"""Orchestrates one complaint: extract → match_and_decide → draft → self-check → hold. Owner: Dev B.

Every step is injected, so stubs and real implementations swap without touching this file.
Extract and draft are async (LLM calls); engine and check are plain functions.
"""
from __future__ import annotations

import uuid

from backend.agent.router import hold
from backend.agent.stubs import fake_extract, stub_check, stub_draft, stub_engine
from backend.contracts import AgentRun, Checker, Complaint, Drafter, Engine, Extractor, RunKind

MAX_REDRAFTS = 1


async def run_pipeline(
    complaint: Complaint,
    *,
    extract: Extractor = fake_extract,
    engine: Engine = stub_engine,
    draft: Drafter = stub_draft,
    check: Checker = stub_check,
    run_kind: RunKind = "autonomous",
) -> AgentRun:
    run = AgentRun(run_id=uuid.uuid4().hex, complaint_id=complaint.complaint_id, run_kind=run_kind)
    try:
        run.clues, run.extract_usage = await extract(complaint)
    except Exception as exc:  # provider failure or malformed output: visible failed run, never a guess
        run.error = f"extract failed: {exc}"
        return run

    try:
        result = engine(complaint, run.clues)
    except Exception as exc:  # engine bug; business cases come back as holds, not exceptions
        run.error = f"engine failed: {exc}"
        return run
    run.match, run.decision, run.evidence = result.match, result.decision, result.evidence

    reply, usage = await draft(result)
    run.draft_usage.append(usage)
    run.self_check = check(reply, result)
    while not run.self_check.passed and run.redraft_count < MAX_REDRAFTS:
        run.redraft_count += 1
        reply, usage = await draft(result, run.self_check.problems)
        run.draft_usage.append(usage)
        run.self_check = check(reply, result)

    run.reply_text = reply
    if not run.self_check.passed:
        run.decision = hold(run.decision, "self_check_failed")
    return run
