"""Batch runner: stores every run, resumes, reruns, retries failures, and its summary adds up (offline)."""
import asyncio

import pytest

from backend.batch.runner import run_batch, select_ids, summarize
from backend.db.store import CaseStore


@pytest.fixture
def store():
    return CaseStore(":memory:")


def batch(store, ids, **kwargs):
    return asyncio.run(run_batch(ids, store, log=lambda _: None, **kwargs))


def test_select_ids():
    assert len(select_ids("test")) == 750 and select_ids("test")[0] == "CMP-00004"
    assert len(select_ids("train")) == 1750
    assert len(select_ids("pilot")) == 50 and len(select_ids("holdout", limit=5)) == 5


def test_pilot_run_stores_every_case(store):
    ids = select_ids("pilot")
    result = batch(store, ids)
    assert len(result.runs) == 50 and not result.failed and result.skipped == 0
    cases = store.cases_for(ids)
    assert len(cases) == 50 and {c["status"] for c in cases.values()} == {"done"}
    assert all(ms > 0 for _, ms in result.runs)


def test_second_run_skips_done_cases(store):
    ids = select_ids("pilot", limit=10)
    batch(store, ids)
    again = batch(store, ids)
    assert again.skipped == 10 and not again.runs


def test_rerun_makes_new_runs(store):
    ids = select_ids("pilot", limit=5)
    batch(store, ids)
    first = {cid: c["autonomous_run_id"] for cid, c in store.cases_for(ids).items()}
    batch(store, ids, rerun=True)
    second = {cid: c["autonomous_run_id"] for cid, c in store.cases_for(ids).items()}
    assert all(first[i] != second[i] for i in ids)
    assert store.conn.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0] == 10


def test_failed_engine_marks_error_then_retries(store):
    def broken(complaint, clues):
        raise RuntimeError("bug")

    ids = select_ids("pilot", limit=3)
    result = batch(store, ids, pipeline_kwargs={"engine": broken})
    assert len(result.failed) == 3 and {c["status"] for c in store.cases_for(ids).values()} == {"error"}
    retry = batch(store, ids)  # no --rerun needed for failed cases
    assert retry.skipped == 0 and not retry.failed
    assert {c["status"] for c in store.cases_for(ids).values()} == {"done"}


def test_summary_counts_add_up(store):
    result = batch(store, select_ids("pilot"))
    text = summarize(result)
    assert text.startswith("Selected 50: 50 processed, 0 skipped")
    routes = text.split("Routes:")[1].splitlines()[0]
    assert sum(int(part.split()[-1]) for part in routes.split(",")) == 50
    assert "RM0.0000 total" in text and "p95" in text
