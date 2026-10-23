"""The UI's /api routes over HTTP (offline: keyword extractor, code-written replies)."""
import time

import pytest
from fastapi.testclient import TestClient

from backend.agent.tools import load_complaint
from backend.main import create_app


def body(cid):
    c = load_complaint(cid)
    return {"complaint_id": c.complaint_id, "customer_id": c.customer_id, "received_at": f"{c.received_at:%Y-%m-%d %H:%M}",
            "channel": c.channel, "subject": c.subject, "text": c.text}


def wait(client, cid, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if client.get(f"/cases/{cid}").json()["status"] != "processing":
            return
        time.sleep(0.05)
    raise AssertionError(f"{cid} still processing")


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "api.db")) as c:
        for cid in ("CMP-00001", "CMP-00244", "CMP-00005"):
            c.post("/complaints", json=body(cid))
        for cid in ("CMP-00001", "CMP-00244", "CMP-00005"):
            wait(c, cid)
        yield c


def test_queue_list(client):
    r = client.get("/api/cases", params={"queue": "awaiting_approval,with_fraud_team"})
    assert r.status_code == 200
    data = r.json()
    assert [i["complaint_id"] for i in data["items"]] == ["CMP-00005", "CMP-00244"]  # P1 fraud before P2 refund
    assert data["counts"]["auto_resolved"] == 1 and data["items"][1]["waiting_reason"] == "Refund over RM500"


@pytest.mark.parametrize("params", [{"queue": "nonsense"}, {"sort": "random"}, {"limit": 0}, {"limit": 501},
                                    {"offset": -1}])
def test_queue_list_rejects_bad_parameters(client, params):
    assert client.get("/api/cases", params=params).status_code == 422


def test_case_detail_and_404(client):
    d = client.get("/api/cases/CMP-00244").json()
    assert d["decision"]["refund_amount_myr"] == "550.00" and d["match"]["candidates"]
    assert client.get("/api/cases/NO-SUCH-CASE").status_code == 404


def test_approve_through_the_contract_shows_in_the_ui_routes(client):
    r = client.post("/cases/CMP-00244/actions", json={"action": "approve", "actor": "Aina (officer)"})
    assert r.status_code == 200
    d = client.get("/api/cases/CMP-00244").json()
    assert d["case"]["case_state"] == "approved" and d["outbound"][0]["authorised_by"] == "Aina (officer)"
    assert client.get("/api/audit", params={"people_only": "true"}).json()["items"][0]["action"] == "approve"
    assert client.get("/api/metrics").json()["human"]["approved"] == 1


def test_metrics_as_of(client):
    m = client.get("/api/metrics", params={"as_of": "2026-09-30T16:30"}).json()
    assert m["sla"]["as_of"] == "2026-09-30T16:30:00" and m["sla"]["open"] == 2
    assert m["cases"]["total"] == 3
    assert client.get("/api/metrics", params={"as_of": "yesterday"}).status_code == 422


def test_audit_filters(client):
    a = client.get("/api/audit", params={"complaint_id": "CMP-00001"}).json()
    assert [i["action"] for i in a["items"]] == ["agent_run", "ingest"]
    assert client.get("/api/audit", params={"since": "soon"}).status_code == 422
    assert client.get("/api/audit", params={"limit": 1001}).status_code == 422


def test_cors_allows_the_react_dev_server(client):
    r = client.get("/api/cases", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "*"
    pre = client.options("/cases/CMP-00244/actions", headers={
        "Origin": "http://192.168.1.20:5173", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert pre.status_code == 200 and pre.headers["access-control-allow-origin"] == "*"


def test_ui_reads_change_nothing(client):
    store = client.app.state.service.store
    before = store.conn.total_changes
    for path in ("/api/cases", "/api/cases/CMP-00244", "/api/metrics", "/api/audit"):
        assert client.get(path).status_code == 200
    assert store.conn.total_changes == before


def test_contract_view_unchanged(client):
    assert set(client.get("/cases/CMP-00244").json()) == {
        "complaint_id", "category", "matched_txn_id", "outcome", "refund_amount_myr", "priority", "reply_language",
        "route", "reply_text", "status", "self_check", "case_state", "sent", "human_action", "hold_reason"}
