"""The bonus platform over HTTP (offline): roles, the three demo flows, send back, agent vs human, new metrics."""
import time

import pytest
from fastapi.testclient import TestClient

from backend.agent.tools import load_complaint
from backend.main import create_app

# Offline decisions: approval refunds 00244 RM550 (within the RM2,000 limit), 00023 RM2,788.60 (over it),
# 00001 RM46.54 auto-resolved; fraud 00003 (RM1,404.18) and 00005 (RM8,085.08).
OK_REFUND, BIG_REFUND, AUTO, FRAUD_LOW, FRAUD_HIGH = "CMP-00244", "CMP-00023", "CMP-00001", "CMP-00003", "CMP-00005"
ALL = (OK_REFUND, BIG_REFUND, AUTO, FRAUD_LOW, FRAUD_HIGH)


def body(cid):
    c = load_complaint(cid)
    return {"complaint_id": c.complaint_id, "customer_id": c.customer_id, "received_at": f"{c.received_at:%Y-%m-%d %H:%M}",
            "channel": c.channel, "subject": c.subject, "text": c.text}


def settle(client, cid, timeout=20):
    """Wait until the case is neither processing nor being re-run."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        case = client.get(f"/api/cases/{cid}").json()["case"]
        if case["queue"] != "processing" and case["workflow"] != "reprocessing":
            return
        time.sleep(0.05)
    raise AssertionError(f"{cid} did not settle")


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "api.db")) as c:
        for cid in ALL:
            c.post("/complaints", json=body(cid))
        for cid in ALL:
            settle(c, cid)
        yield c


@pytest.fixture
def as_(client):
    tokens = {}

    def headers(username):
        if username not in tokens:
            tokens[username] = client.post("/api/auth/login",
                                           json={"username": username, "password": "teratai123"}).json()["token"]
        return {"Authorization": f"Bearer {tokens[username]}"}
    return headers


def ids(response):
    return sorted(i["complaint_id"] for i in response.json()["items"])


# --- roles ---

def test_each_role_sees_only_its_team(client, as_):
    officer = client.get("/api/cases", headers=as_("officer1")).json()
    assert sorted(i["complaint_id"] for i in officer["items"]) == [BIG_REFUND, OK_REFUND]
    assert officer["total"] == 2 and sum(officer["counts"].values()) == 2
    assert ids(client.get("/api/cases", headers=as_("fraud1"))) == [FRAUD_LOW, FRAUD_HIGH]
    assert len(ids(client.get("/api/cases", headers=as_("manager1")))) == 5
    assert client.get(f"/api/cases/{FRAUD_LOW}", headers=as_("officer1")).status_code == 404
    assert client.get(f"/api/cases/{AUTO}", headers=as_("fraud1")).status_code == 404
    assert client.get(f"/api/cases/{FRAUD_LOW}", headers=as_("fraud1")).status_code == 200


@pytest.mark.parametrize("path", ["/api/metrics", "/api/audit", "/api/users"])
def test_manager_only_reads(client, as_, path):
    assert client.get(path, headers=as_("officer1")).status_code == 403
    assert client.get(path, headers=as_("fraud1")).status_code == 403
    assert client.get(path, headers=as_("manager1")).status_code == 200


def test_actions_need_a_token(client):
    r = client.post(f"/api/cases/{OK_REFUND}/approve", json={})
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


def test_officer_cannot_act_on_fraud(client, as_):
    r = client.post(f"/api/cases/{FRAUD_LOW}/acknowledge", json={}, headers=as_("officer1"))
    assert r.status_code == 403


# --- demo flow 1: within the limit ---

def test_flow_within_limit_officer_approves(client, as_):
    r = client.post(f"/api/cases/{OK_REFUND}/approve", json={"reason": "ATM journal confirms"},
                    headers=as_("officer1"))
    assert r.status_code == 200
    d = r.json()
    assert d["case"]["case_state"] == "approved" and d["case"]["sent"]
    assert d["outbound"][0]["authorised_by"] == "officer1"
    assert d["final"]["by"] == "officer1" and d["differs"] == {"decision": False, "refund": False, "reply": False}
    assert client.post(f"/api/cases/{OK_REFUND}/approve", json={}, headers=as_("officer1")).status_code == 409


def test_edit_with_invented_amount_then_fix(client, as_):
    officer = as_("officer1")
    r = client.post(f"/api/cases/{OK_REFUND}/edit-reply", headers=officer,
                    json={"reply_text": "We will refund RM999.00 for TXN-0000001.", "reason": "shorter"})
    assert r.status_code == 200 and r.json()["draft_reply"]["self_check"] == "flagged"
    refused = client.post(f"/api/cases/{OK_REFUND}/approve", json={}, headers=officer)
    assert refused.status_code == 422 and any("RM999.00" in p for p in refused.json()["detail"]["problems"])
    good = r.json()["reply"]["text"] + "\n\nThank you for your patience."
    client.post(f"/api/cases/{OK_REFUND}/edit-reply", headers=officer, json={"reply_text": good, "reason": "warmer"})
    d = client.post(f"/api/cases/{OK_REFUND}/approve", json={}, headers=officer).json()
    assert d["outbound"][0]["reply_text"] == good and d["differs"]["reply"] is True
    assert ids(client.get("/api/cases", params={"overridden": "true"})) == [OK_REFUND]


# --- demo flow 2: over the limit → manager ---

def test_flow_over_limit_escalates_and_manager_approves(client, as_):
    r = client.post(f"/api/cases/{BIG_REFUND}/approve", json={}, headers=as_("officer1"))
    assert r.status_code == 403
    assert r.json()["detail"] == {"error": "escalate to a manager", "why": "refund RM2,788.60 is over your limit RM2,000.00",
                                  "limit": "2000.00", "amount": "2788.60"}
    esc = client.post(f"/api/cases/{BIG_REFUND}/escalate", json={"reason": "over my limit"}, headers=as_("officer1"))
    assert esc.json()["case"]["workflow"] == "escalated" and esc.json()["case"]["sent"] is False
    assert ids(client.get("/api/cases", params={"workflow": "escalated"}, headers=as_("manager1"))) == [BIG_REFUND]
    assert client.post(f"/cases/{BIG_REFUND}/actions", json={"action": "approve", "actor": "judge"}).status_code == 409
    assert client.get(f"/cases/{BIG_REFUND}").json()["sent"] is False

    d = client.post(f"/api/cases/{BIG_REFUND}/second-tier-approve", json={"reason": "verified with branch"},
                    headers=as_("manager1")).json()
    assert d["case"]["case_state"] == "approved" and d["case"]["workflow"] == "closed"
    assert [m["authorised_by"] for m in d["outbound"]] == ["manager1"]
    trail = [(e["actor"], e["action"]) for e in d["events"] if e["actor"] != "agent"]
    assert trail == [("officer1", "escalate"), ("manager1", "second_tier_approve")]
    assert client.get(f"/cases/{BIG_REFUND}").json()["case_state"] == "approved"  # the contract view agrees


def test_second_tier_reject_shows_the_gap(client, as_):
    client.post(f"/api/cases/{BIG_REFUND}/escalate", json={"reason": "unsure"}, headers=as_("officer1"))
    d = client.post(f"/api/cases/{BIG_REFUND}/second-tier-reject", json={"reason": "transfer completed"},
                    headers=as_("manager1")).json()
    assert d["final"]["outcome"] == "REJECTED" and d["final"]["sent"] is False
    assert d["differs"]["decision"] is True and d["differs"]["refund"] is True


# --- demo flow 3: fraud ---

def test_flow_fraud_acknowledge_investigate_outcome(client, as_):
    analyst = as_("fraud1")
    d = client.post(f"/api/cases/{FRAUD_LOW}/acknowledge", json={}, headers=analyst).json()
    assert d["case"]["workflow"] == "investigating" and [m["kind"] for m in d["outbound"]] == ["holding_reply"]
    client.post(f"/api/cases/{FRAUD_LOW}/investigate", json={"note": "called the customer"}, headers=analyst)
    d = client.post(f"/api/cases/{FRAUD_LOW}/record-outcome", headers=analyst,
                    json={"outcome": "confirmed_fraud", "reason": "card cloned"}).json()
    assert d["case"]["workflow"] == "closed" and d["fraud_outcome"]["outcome"] == "confirmed_fraud"
    assert d["final"]["outcome"] == "confirmed_fraud" and len(d["outbound"]) == 1  # only the holding reply


def test_high_value_fraud_needs_the_manager(client, as_):
    analyst = as_("fraud1")
    client.post(f"/api/cases/{FRAUD_HIGH}/acknowledge", json={}, headers=analyst)
    r = client.post(f"/api/cases/{FRAUD_HIGH}/record-outcome", headers=analyst,
                    json={"outcome": "confirmed_fraud", "reason": "mule account"})
    assert r.status_code == 403 and "RM8,085.08" in r.json()["detail"]["why"]
    client.post(f"/api/cases/{FRAUD_HIGH}/escalate", json={"reason": "high value", "outcome": "confirmed_fraud"},
                headers=analyst)
    d = client.post(f"/api/cases/{FRAUD_HIGH}/second-tier-approve", json={"reason": "agreed"},
                    headers=as_("manager1")).json()
    assert d["fraud_outcome"]["by"] == "manager1" and d["case"]["workflow"] == "closed"


# --- send back, reassign, filters ---

def test_send_back_reruns_with_the_note(client, as_):
    before = client.get(f"/cases/{OK_REFUND}").json()
    r = client.post(f"/api/cases/{OK_REFUND}/send-back", json={"note": "customer confirms about RM1,500 on 17-07"},
                    headers=as_("officer1"))
    assert r.status_code == 202
    settle(client, OK_REFUND)
    d = client.get(f"/api/cases/{OK_REFUND}").json()
    assert [run["run_kind"] for run in d["runs"]] == ["autonomous", "reprocess"]
    assert d["case"]["current_run_id"] == d["runs"][1]["run_id"] != d["case"]["autonomous_run_id"]
    assert d["case"]["workflow"] is None and d["case"]["queue"] == "awaiting_approval"
    assert [e["action"] for e in d["events"]][-2:] == ["send_back", "agent_run"]
    assert client.get(f"/cases/{OK_REFUND}").json() == before  # contract view: the autonomous decision


def test_reassign_and_assigned_to_me(client, as_):
    r = client.post(f"/api/cases/{OK_REFUND}/reassign", json={"username": "officer2", "reason": "leave"},
                    headers=as_("manager1"))
    assert r.json()["case"]["assigned_to"] == "officer2"
    assert ids(client.get("/api/cases", params={"assigned_to": "me"}, headers=as_("officer2"))) == [OK_REFUND]
    assert client.get("/api/cases", params={"assigned_to": "me"}, headers=as_("officer1")).json()["total"] == 0
    assert client.post(f"/api/cases/{OK_REFUND}/approve", json={}, headers=as_("officer1")).status_code == 403
    assert client.get("/api/cases", params={"assigned_to": "me"}).status_code == 422  # no login, no "me"


def test_sensitive_filter_and_workflow_counts(client, as_):
    client.post(f"/api/cases/{OK_REFUND}/flag-sensitive", json={"reason": "bereaved"}, headers=as_("officer1"))
    client.post(f"/api/cases/{BIG_REFUND}/escalate", json={"reason": "limit"}, headers=as_("officer1"))
    listed = client.get("/api/cases", params={"sensitive": "true"}).json()
    assert [i["complaint_id"] for i in listed["items"]] == [OK_REFUND]
    assert listed["items"][0]["sensitive_reason"] == "bereaved"
    assert listed["workflow_counts"]["escalated"] == 1
    big = client.get(f"/api/cases/{BIG_REFUND}").json()["case"]
    assert big["waiting_reason"] == "Escalated to the manager" and big["escalation"]["by"] == "officer1"


# --- new metrics ---

def test_metrics_refunds_compliance_and_trend(client, as_):
    client.post(f"/api/cases/{OK_REFUND}/approve", json={}, headers=as_("officer1"))
    m = client.get("/api/metrics").json()
    assert m["refunds_myr"] == {"auto_paid": "46.54", "approved_paid": "550.00", "awaiting": "2788.60",
                                "rejected": "0.00"}
    assert m["sla"]["compliance"] == 1.0 and m["sla"]["closed"] == 2
    assert m["turnaround_minutes"]["p50"] is not None and m["turnaround_minutes"]["p50"] < 5
    days = m["trends"]["received_by_day"]
    assert sum(d["total"] for d in days) == 5 and [d["date"] for d in days] == sorted(d["date"] for d in days)
    assert sum(m["cases"]["by_channel"].values()) == 5 and sum(m["cases"]["by_language"].values()) == 5
    assert m["human"]["approved"] == 1
