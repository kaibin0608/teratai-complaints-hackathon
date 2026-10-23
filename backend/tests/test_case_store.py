"""CaseStore: immutable runs, case state from the route, one outbox message, rerun rules."""
import asyncio
import sqlite3

import pytest

from backend.agent.pipeline import run_pipeline
from backend.agent.tools import load_complaint
from backend.db.store import CaseConflict, CaseStore, HumanActedError


@pytest.fixture
def store():
    return CaseStore(":memory:")


def run_for(cid, **kwargs):
    return asyncio.run(run_pipeline(load_complaint(cid), **kwargs))


def save(store, cid, rerun=False, **kwargs):
    return store.save_run(load_complaint(cid), run_for(cid, **kwargs), latency_ms=12, rerun=rerun)


def test_run_round_trips_and_refund_in_sen(store):
    run = run_for("CMP-00244")
    store.save_run(load_complaint("CMP-00244"), run, latency_ms=12)
    loaded = store.run(run.run_id)  # raw evidence rows come back JSON-typed (datetimes as strings)
    assert loaded.model_dump_json() == run.model_dump_json() and loaded.decision == run.decision
    row = store.conn.execute("SELECT refund_sen, route, self_check FROM agent_runs").fetchone()
    assert tuple(row) == (55000, "HUMAN_APPROVAL", "passed")


@pytest.mark.parametrize("sql", ["UPDATE agent_runs SET outcome = 'DECLINE'", "DELETE FROM agent_runs",
                                 "UPDATE case_events SET actor = 'x'", "DELETE FROM case_events"])
def test_runs_and_events_are_append_only(store, sql):
    save(store, "CMP-00244")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        store.conn.execute(sql)


@pytest.mark.parametrize("cid, state, sent, outbox", [
    ("CMP-00244", "awaiting_approval", 0, 0),   # refund RM550 > RM500
    ("CMP-00002", "auto_resolved", 1, 1),       # service complaint, INFO_ONLY
    ("CMP-00005", "with_fraud_team", 0, 0),     # scam: waits for an analyst
])
def test_case_state_follows_route(store, cid, state, sent, outbox):
    case = save(store, cid)
    assert (case["status"], case["case_state"], case["sent"]) == ("done", state, sent)
    assert len(store.outbound(cid)) == outbox


def test_auto_resolved_goes_to_outbox_once_even_after_rerun(store):
    save(store, "CMP-00002")
    case = save(store, "CMP-00002", rerun=True)
    assert case["sent"] == 1 and len(store.outbound("CMP-00002")) == 1


def test_failed_run_marks_case_error_and_can_be_retried(store):
    def broken(complaint, clues):
        raise RuntimeError("bug")

    case = save(store, "CMP-00001", engine=broken)
    assert case["status"] == "error" and "engine failed" in case["error"]
    case = save(store, "CMP-00001")  # retry without rerun is allowed for a failed case
    assert case["status"] == "done" and case["error"] is None


def test_done_case_needs_rerun_flag(store):
    save(store, "CMP-00001")
    with pytest.raises(ValueError, match="rerun"):
        save(store, "CMP-00001")


def test_content_conflict(store):
    save(store, "CMP-00001")
    changed = load_complaint("CMP-00001").model_copy(update={"text": "something else"})
    with pytest.raises(CaseConflict):
        store.save_run(changed, run_for("CMP-00001"), latency_ms=1, rerun=True)


def test_rerun_repoints_and_keeps_old_run(store):
    first = save(store, "CMP-00001")["autonomous_run_id"]
    second = save(store, "CMP-00001", rerun=True)["autonomous_run_id"]
    assert first != second and store.run(first) is not None
    assert store.autonomous_run("CMP-00001").run_id == second
    events = store.events("CMP-00001")
    assert [e["action"] for e in events] == ["ingest", "agent_run", "agent_run"]
    assert first in events[-1]["detail"] and events[-1]["run_id"] == second


def test_rerun_refused_after_a_human_acts(store):
    save(store, "CMP-00244")
    with store.conn:
        store._event("CMP-00244", "approve", None, {"reason": "ok"}, actor="Aina (complaints officer)")
    with pytest.raises(HumanActedError):
        save(store, "CMP-00244", rerun=True)
