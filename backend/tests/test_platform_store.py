"""Store changes for the bonus platform: migration, seeded users, the one gated send, send-back runs."""
import asyncio
import sqlite3

import bcrypt
import pytest

from backend.agent.pipeline import run_pipeline
from backend.agent.reply_rules import combined_check
from backend.agent.tools import load_complaint
from backend.db.schema import ADDED_CASE_COLUMNS, init_db
from backend.db.seed import DEMO_PASSWORD, USERS, seed_users
from backend.db.store import CaseStore, ReplyRefused, WrongState

PENDING, FRAUD = "CMP-00244", "CMP-00005"


def put(store, cid):
    c = load_complaint(cid)
    store.register(c)
    store.save_run(c, asyncio.run(run_pipeline(c)), latency_ms=5)


@pytest.fixture
def store():
    s = CaseStore(":memory:")
    put(s, PENDING)
    put(s, FRAUD)
    return s


def set_workflow(store, cid, value):
    with store.conn:
        store.conn.execute("UPDATE cases SET workflow = ? WHERE complaint_id = ?", (value, cid))


def test_migration_adds_platform_columns_and_users_to_an_existing_database(tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE cases (complaint_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, received_at TEXT NOT NULL,"
                 " channel TEXT NOT NULL, subject TEXT NOT NULL, text TEXT NOT NULL, content_hash TEXT NOT NULL,"
                 " autonomous_run_id TEXT, current_run_id TEXT, status TEXT NOT NULL, case_state TEXT,"
                 " sent INTEGER NOT NULL DEFAULT 0, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,"
                 " human_action TEXT)")
    conn.execute("INSERT INTO cases VALUES ('X', 'C', '2026-09-30 10:00', 'Email', '', 't', 'h', NULL, NULL,"
                 " 'processing', NULL, 0, NULL, 'now', 'now', NULL)")
    conn.commit()
    init_db(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(cases)")}
    assert set(ADDED_CASE_COLUMNS) <= columns
    assert conn.execute("SELECT workflow, assigned_to FROM cases WHERE complaint_id = 'X'").fetchone() == (None, None)
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone() == (0,)


def test_seeding_twice_keeps_one_copy_with_hashed_passwords():
    s = CaseStore(":memory:")
    assert seed_users(s.conn) == 4 and seed_users(s.conn) == 0
    rows = s.conn.execute("SELECT username, password_hash, role, approval_limit_sen FROM users ORDER BY username")
    rows = {r[0]: r for r in rows}
    assert set(rows) == {u[0] for u in USERS}
    assert rows["officer1"][3] == 200_000 and rows["fraud1"][3] == 500_000 and rows["manager1"][3] is None
    assert all(r[1] != DEMO_PASSWORD and bcrypt.checkpw(DEMO_PASSWORD.encode(), r[1].encode()) for r in rows.values())


def test_double_send_is_refused_and_writes_one_outbox_row(store):
    store.act(PENDING, "approve", "Aina", check=combined_check)
    with pytest.raises(WrongState):
        store.act(PENDING, "approve", "Aina", check=combined_check)
    case = store.get_case(PENDING)
    run = store.current_run(case)
    with pytest.raises(WrongState, match="already sent"):  # straight at the gate, as a retry would hit it
        with store.conn:
            store.send(case, run.run_id, "resolution", run.reply_text, 55000, "Aina", "now", checked=run.self_check)
    assert len(store.outbound(PENDING)) == 1


@pytest.mark.parametrize("workflow", ["escalated", "reprocessing", "closed"])
def test_contract_approve_is_refused_on_platform_cases(store, workflow):
    set_workflow(store, PENDING, workflow)
    with pytest.raises(WrongState):
        store.act(PENDING, "approve", "judge", check=combined_check)
    assert store.outbound(PENDING) == [] and not store.get_case(PENDING)["sent"]


def test_gate_refuses_an_escalated_case_unless_second_tier(store):
    set_workflow(store, PENDING, "escalated")
    case, run = store.get_case(PENDING), store.autonomous_run(PENDING)
    with pytest.raises(WrongState, match="escalated"):
        with store.conn:
            store.send(case, run.run_id, "resolution", run.reply_text, 0, "Aina", "now", checked=run.self_check)
    with store.conn:
        store.send(case, run.run_id, "resolution", run.reply_text, 0, "Mei", "now", checked=run.self_check,
                   second_tier=True)
    assert [m["authorised_by"] for m in store.outbound(PENDING)] == ["Mei"]


def test_gate_refuses_a_reply_that_failed_the_self_check(store):
    case, run = store.get_case(PENDING), store.autonomous_run(PENDING)
    flagged = run.self_check.model_copy(update={"passed": False, "problems": ["amount RM9.99 is not in the evidence"]})
    with pytest.raises(ReplyRefused, match="RM9.99"):
        with store.conn:
            store.send(case, run.run_id, "resolution", run.reply_text, 0, "Aina", "now", checked=flagged)
    with pytest.raises(ReplyRefused):
        with store.conn:
            store.send(case, run.run_id, "resolution", run.reply_text, 0, "Aina", "now", checked=None)
    assert store.outbound(PENDING) == []


def test_acknowledge_starts_the_investigation(store):
    store.acknowledge(FRAUD, "Farid")
    case = store.get_case(FRAUD)
    assert case["workflow"] == "investigating" and case["sent"] and case["case_state"] == "with_fraud_team"
    with pytest.raises(WrongState):
        store.acknowledge(FRAUD, "Farid")


def test_reprocess_becomes_current_but_contract_and_export_stay_autonomous(store):
    before = store.case_view(PENDING)
    autonomous = store.get_case(PENDING)["autonomous_run_id"]
    set_workflow(store, PENDING, "reprocessing")
    c = load_complaint(PENDING)
    rerun = asyncio.run(run_pipeline(c.model_copy(update={"text": c.text + "\n\n[Officer note: about RM1,500]"}),
                                     run_kind="reprocess"))
    case = store.save_reprocess(PENDING, rerun, latency_ms=7)
    assert case["current_run_id"] == rerun.run_id and case["autonomous_run_id"] == autonomous
    assert case["workflow"] is None and case["case_state"] == "awaiting_approval"
    assert store.case_view(PENDING) == before
    assert store.autonomous_run(PENDING).run_id == autonomous
    assert store.events(PENDING)[-1]["action"] == "agent_run"


def test_reprocess_never_auto_resolves():
    s = CaseStore(":memory:")
    put(s, "CMP-00244")
    set_workflow(s, "CMP-00244", "reprocessing")
    auto = asyncio.run(run_pipeline(load_complaint("CMP-00001")))  # an AUTO_RESOLVE decision
    rerun = auto.model_copy(update={"complaint_id": "CMP-00244", "run_kind": "reprocess"})
    case = s.save_reprocess("CMP-00244", rerun, latency_ms=7)
    assert case["case_state"] == "awaiting_approval" and not case["sent"] and s.outbound("CMP-00244") == []


def test_failed_reprocess_keeps_the_current_run(store):
    current = store.get_case(PENDING)["current_run_id"]
    set_workflow(store, PENDING, "reprocessing")
    failed = asyncio.run(run_pipeline(load_complaint(PENDING))).model_copy(
        update={"decision": None, "error": "engine crashed", "run_kind": "reprocess"})
    case = store.save_reprocess(PENDING, failed, latency_ms=7)
    assert case["current_run_id"] == current and case["workflow"] is None
    assert store.events(PENDING)[-1]["action"] == "send_back_failed"


def test_restart_cleans_up_an_interrupted_send_back(store):
    set_workflow(store, PENDING, "reprocessing")
    assert store.reset_reprocessing() == [PENDING]
    assert store.get_case(PENDING)["workflow"] is None
    assert store.events(PENDING)[-1]["detail"] == '{"error": "server restarted during the re-run"}'
