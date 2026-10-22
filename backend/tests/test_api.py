"""The organisers' contract over HTTP (offline: keyword extractor, code-written replies)."""
import time

import pytest
from fastapi.testclient import TestClient

from backend.agent.tools import load_complaint
from backend.db.store import CaseStore
from backend.main import create_app

FIELDS = ("complaint_id", "customer_id", "received_at", "channel", "subject", "text")


def body(cid, **changes):
    c = load_complaint(cid)
    return {"complaint_id": c.complaint_id, "customer_id": c.customer_id, "received_at": f"{c.received_at:%Y-%m-%d %H:%M}",
            "channel": c.channel, "subject": c.subject, "text": c.text, **changes}


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "api.db")) as c:
        yield c


def wait(client, cid, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        case = client.get(f"/cases/{cid}").json()
        if case["status"] != "processing":
            return case
        time.sleep(0.05)
    raise AssertionError(f"{cid} still processing")


def test_health_and_unknown_case(client):
    assert client.get("/health").json() == {"ok": True}
    assert client.get("/cases/NO-SUCH-CASE-123").status_code == 404


def test_new_complaint_is_processed_in_background(client):
    r = client.post("/complaints", json=body("CMP-00244"))
    assert r.status_code == 202 and r.json() == {"complaint_id": "CMP-00244", "status": "processing"}
    case = wait(client, "CMP-00244")
    assert {k: case[k] for k in ("status", "outcome", "refund_amount_myr", "route", "case_state", "sent",
                                 "human_action", "self_check")} == {
        "status": "done", "outcome": "REFUND", "refund_amount_myr": "550.00", "route": "HUMAN_APPROVAL",
        "case_state": "awaiting_approval", "sent": False, "human_action": None, "self_check": "passed"}


@pytest.mark.parametrize("change", [{"text": ""}, {"text": "   "}, {"customer_id": ""}, {"received_at": "yesterday"}])
def test_bad_input_is_422(client, change):
    assert client.post("/complaints", json=body("CMP-00244", **change)).status_code == 422
    assert client.get("/cases/CMP-00244").status_code == 404


def test_missing_text_field_is_422(client):
    bad = {k: v for k, v in body("CMP-00244").items() if k != "text"}
    assert client.post("/complaints", json=bad).status_code == 422


def test_repost_returns_existing_case_unchanged(client):
    client.post("/complaints", json=body("CMP-00001"))
    before = wait(client, "CMP-00001")
    again = client.post("/complaints", json=body("CMP-00001"))
    assert again.status_code == 200 and again.json()["status"] == "done"
    assert client.get("/cases/CMP-00001").json() == before


def test_same_id_different_content_is_409(client):
    client.post("/complaints", json=body("CMP-00001"))
    assert client.post("/complaints", json=body("CMP-00001", text="something else")).status_code == 409


def test_unknown_customer_is_held(client):
    r = client.post("/complaints", json=body("CMP-00002", complaint_id="LIVE-99", customer_id="CUS-99999"))
    assert r.status_code == 202
    case = wait(client, "LIVE-99")
    assert case["status"] == "done" and case["hold_reason"] == "customer_not_found"


def test_twenty_at_once(client):
    ids = [f"CMP-{n:05d}" for n in range(1, 21)]
    assert {client.post("/complaints", json=body(i)).status_code for i in ids} == {202}
    assert {wait(client, i)["status"] for i in ids} == {"done"}


def test_pipeline_crash_becomes_error(tmp_path):
    async def crash(complaint):
        raise RuntimeError("boom")

    with TestClient(create_app(tmp_path / "api.db", pipeline=crash)) as c:
        c.post("/complaints", json=body("CMP-00001"))
        case = wait(c, "CMP-00001")
    assert case["status"] == "error" and "boom" in case["error"]


def test_restart_requeues_processing_cases(tmp_path):
    path = tmp_path / "api.db"
    CaseStore(path).register(load_complaint("CMP-00244"))  # as if the server died mid-run
    with TestClient(create_app(path)) as c:
        assert wait(c, "CMP-00244")["status"] == "done"


def test_human_loop_like_api_check(client):
    client.post("/complaints", json=body("CMP-00244"))
    target = wait(client, "CMP-00244")
    url = "/cases/CMP-00244/actions"
    bad = {"action": "edit_approve", "actor": "api_check probe", "reason": "probe",
           "reply_text": target["reply_text"] + " We have also credited RM987.65 to your account."}
    refused = client.post(url, json=bad)
    held = client.get("/cases/CMP-00244").json()
    assert refused.status_code == 422 and (held["case_state"], held["sent"]) == ("awaiting_approval", False)

    ok = client.post(url, json={"action": "approve", "actor": "api_check probe", "reason": "probe"})
    done = ok.json()
    assert ok.status_code == 200 and (done["case_state"], done["sent"]) == ("approved", True)
    assert done["human_action"]["actor"] == "api_check probe"
    assert all(done[k] == target[k] for k in ("category", "matched_txn_id", "outcome", "refund_amount_myr",
                                               "priority", "reply_language", "route", "reply_text"))
    assert client.post(url, json={"action": "approve", "actor": "x", "reason": "again"}).status_code == 409


def test_reject_and_validation_codes(client):
    client.post("/complaints", json=body("CMP-00244"))
    wait(client, "CMP-00244")
    url = "/cases/CMP-00244/actions"
    assert client.post(url, json={"action": "approve"}).status_code == 422             # no actor
    assert client.post(url, json={"action": "escalate", "actor": "A"}).status_code == 422
    assert client.post(url, json={"action": "reject", "actor": "A"}).status_code == 422  # no reason
    assert client.post("/cases/NOPE/actions", json={"action": "approve", "actor": "A"}).status_code == 404
    r = client.post(url, json={"action": "reject", "actor": "A", "reason": "wrong transaction"})
    assert r.status_code == 200 and (r.json()["case_state"], r.json()["sent"]) == ("rejected", False)


def test_auto_resolved_and_fraud_cases(client):
    for cid in ("CMP-00002", "CMP-00005"):
        client.post("/complaints", json=body(cid))
    auto, fraud = wait(client, "CMP-00002"), wait(client, "CMP-00005")
    assert (auto["case_state"], auto["sent"]) == ("auto_resolved", True)
    assert (fraud["case_state"], fraud["sent"]) == ("with_fraud_team", False)
    assert client.post("/cases/CMP-00005/actions", json={"action": "approve", "actor": "A"}).status_code == 409

    ack = client.post("/cases/CMP-00005/acknowledge", json={"actor": "Hafiz (fraud analyst)"})
    assert ack.status_code == 200 and (ack.json()["case_state"], ack.json()["sent"]) == ("with_fraud_team", True)
    assert client.post("/cases/CMP-00005/acknowledge", json={"actor": "Hafiz"}).status_code == 409
    assert client.post("/cases/CMP-00002/acknowledge", json={"actor": "Hafiz"}).status_code == 409
