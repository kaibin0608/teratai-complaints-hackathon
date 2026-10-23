"""Store: processing cases, the contract view, human actions and fraud acknowledge; the agent's run never changes."""
import asyncio
import sqlite3

import pytest

from backend.agent.pipeline import run_pipeline
from backend.agent.reply_rules import combined_check
from backend.agent.tools import load_complaint
from backend.db.schema import init_db
from backend.db.store import CaseConflict, CaseStore, InvalidAction, NotFound, ReplyRefused, WrongState

PENDING, FRAUD, AUTO = "CMP-00244", "CMP-00005", "CMP-00002"
DECISION = ("category", "matched_txn_id", "outcome", "refund_amount_myr", "priority", "reply_language", "route",
            "reply_text")


@pytest.fixture
def store():
    s = CaseStore(":memory:")
    for cid in (PENDING, FRAUD, AUTO):
        c = load_complaint(cid)
        s.register(c)
        s.save_run(c, asyncio.run(run_pipeline(c)), latency_ms=5)
    return s


def act(store, cid, action, **kw):
    return store.act(cid, action, kw.pop("actor", "Aina (officer)"), check=combined_check, **kw)


def test_migration_adds_human_action_to_old_databases(tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE cases (complaint_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, received_at TEXT NOT NULL,"
                 " channel TEXT NOT NULL, subject TEXT NOT NULL, text TEXT NOT NULL, content_hash TEXT NOT NULL,"
                 " autonomous_run_id TEXT, current_run_id TEXT, status TEXT NOT NULL, case_state TEXT,"
                 " sent INTEGER NOT NULL DEFAULT 0, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    conn.commit()
    init_db(conn)
    assert "human_action" in {r[1] for r in conn.execute("PRAGMA table_info(cases)")}


def test_register_is_idempotent_and_detects_conflicts():
    s = CaseStore(":memory:")
    c = load_complaint(PENDING)
    case, created = s.register(c)
    assert created and case["status"] == "processing" and s.case_view(PENDING) == {"complaint_id": PENDING,
                                                                                   "status": "processing"}
    assert s.register(c) == (case, False) and s.processing_ids() == [PENDING]
    with pytest.raises(CaseConflict):
        s.register(c.model_copy(update={"text": "different"}))
    assert [e["action"] for e in s.events(PENDING)] == ["ingest"]


def test_view_has_every_contract_field(store):
    view = store.case_view(PENDING)
    assert {k: view[k] for k in ("status", "outcome", "refund_amount_myr", "route", "case_state", "sent",
                                  "human_action", "self_check")} == {
        "status": "done", "outcome": "REFUND", "refund_amount_myr": "550.00", "route": "HUMAN_APPROVAL",
        "case_state": "awaiting_approval", "sent": False, "human_action": None, "self_check": "passed"}


def test_approve(store):
    before = store.case_view(PENDING)
    act(store, PENDING, "approve", reason="journal confirms")
    after = store.case_view(PENDING)
    assert (after["case_state"], after["sent"]) == ("approved", True)
    assert after["human_action"]["actor"] == "Aina (officer)" and after["human_action"]["reply_text"] == before["reply_text"]
    assert all(after[k] == before[k] for k in DECISION)
    assert [m["kind"] for m in store.outbound(PENDING)] == ["resolution"]
    with pytest.raises(WrongState):
        act(store, PENDING, "approve")


def test_edit_with_invented_amount_is_refused_and_nothing_sent(store):
    bad = store.case_view(PENDING)["reply_text"] + " We have also credited RM987.65 to your account."
    with pytest.raises(ReplyRefused) as refused:
        act(store, PENDING, "edit_approve", reason="add detail", reply_text=bad)
    assert any("RM987.65" in p for p in refused.value.problems)
    view = store.case_view(PENDING)
    assert (view["case_state"], view["sent"]) == ("awaiting_approval", False) and not store.outbound(PENDING)
    assert store.events(PENDING)[-1]["action"] == "edit_approve_refused"


def test_good_edit_is_sent_but_decision_keeps_agent_reply(store):
    agent_reply = store.case_view(PENDING)["reply_text"]
    edited = "Dear customer, a refund of RM550.00 will be credited to your account once our review is complete. " \
             "We are sorry for the trouble.\n\nYours sincerely,\nTeratai Bank Customer Care"
    act(store, PENDING, "edit_approve", reason="shorter", reply_text=edited)
    view = store.case_view(PENDING)
    assert view["reply_text"] == agent_reply and view["human_action"]["reply_text"] == edited
    assert store.outbound(PENDING)[0]["reply_text"] == edited


def test_reject_sends_nothing(store):
    act(store, PENDING, "reject", reason="journal disagrees")
    view = store.case_view(PENDING)
    assert (view["case_state"], view["sent"], view["human_action"]["reply_text"]) == ("rejected", False, None)
    assert not store.outbound(PENDING)


@pytest.mark.parametrize("kwargs, message", [
    ({"actor": "  "}, "actor"), ({"reason": ""}, "reason"),
])
def test_invalid_actions(store, kwargs, message):
    with pytest.raises(InvalidAction, match=message):
        act(store, PENDING, "reject", **{"reason": "x", **kwargs})
    with pytest.raises(InvalidAction, match="unknown action"):
        act(store, PENDING, "escalate")
    with pytest.raises(InvalidAction, match="reply_text"):
        act(store, PENDING, "edit_approve", reason="x")


def test_actions_only_on_awaiting_approval(store):
    for cid in (FRAUD, AUTO):
        with pytest.raises(WrongState):
            act(store, cid, "approve")
    with pytest.raises(NotFound):
        act(store, "NO-SUCH", "approve")


def test_acknowledge_fraud_case(store):
    before = store.case_view(FRAUD)
    store.acknowledge(FRAUD, "Hafiz (fraud analyst)", "called the customer")
    after = store.case_view(FRAUD)
    assert (after["case_state"], after["sent"], after["human_action"]["action"]) == ("with_fraud_team", True, "acknowledge")
    assert all(after[k] == before[k] for k in DECISION)
    assert [m["kind"] for m in store.outbound(FRAUD)] == ["holding_reply"]
    with pytest.raises(WrongState):
        store.acknowledge(FRAUD, "Hafiz")
    with pytest.raises(WrongState):
        store.acknowledge(PENDING, "Hafiz")
    with pytest.raises(InvalidAction):
        store.acknowledge(FRAUD, "")
