"""Orchestrates one complaint: extract → match_and_decide → draft → self-check → hold. Owner: Dev B.

Every step is injected, so stubs and real implementations swap without touching this file.
Extract and draft are async (LLM calls); engine and check are plain functions.

An LLM failure never costs the complaint its prediction row: extraction falls back to keyword clues, drafting to
the template holding reply, and the case is held with llm_error for a human. Only an engine bug leaves a run
without a decision.
"""
from __future__ import annotations

import functools
import uuid

from backend.agent.engine import match_and_decide
from backend.agent.parser import extract as llm_extract
from backend.agent.reply_generator import code_draft, draft as llm_draft
from backend.agent.reply_rules import combined_check
from backend.agent.router import hold
from backend.agent.stubs import fake_extract
from backend.contracts import (
    AgentRun, Checker, Complaint, Decision, Drafter, Engine, EngineResult, Extractor, LLMUsage, RunKind,
)
from backend.llm.prompts import CLUES_SCHEMA_VERSION, DRAFT_PROMPT_VERSION, EXTRACT_PROMPT_VERSION

MAX_REDRAFTS = 1


def hold_llm_error(decision: Decision) -> Decision:
    """llm_error replaces whatever the engine said (keyword clues usually give no_match, which would hide it)."""
    return hold(decision.model_copy(update={"hold_reason": None}), "llm_error")


def note_error(run: AgentRun, message: str) -> None:
    run.error = f"{run.error}; {message}" if run.error else message


async def draft_or_template(
    draft: Drafter, result: EngineResult, feedback: list[str] | None, run: AgentRun,
) -> tuple[str, LLMUsage, bool]:
    """(reply, usage, llm_failed). A drafter failure falls back to the code-written reply (facts only)."""
    try:
        reply, usage = await draft(result, feedback)
        return reply, usage, False
    except Exception as exc:
        note_error(run, f"draft failed, used code-written reply: {exc}")
        reply, usage = await code_draft(result)
        return reply, usage, True


async def run_pipeline(
    complaint: Complaint,
    *,
    extract: Extractor = llm_extract,
    engine: Engine = match_and_decide,
    draft: Drafter | None = None,  # None: the LLM reply writer for this complaint (LLM_DRAFT)
    check: Checker = combined_check,
    run_kind: RunKind = "autonomous",
) -> AgentRun:
    run = AgentRun(run_id=uuid.uuid4().hex, complaint_id=complaint.complaint_id, run_kind=run_kind,
                   prompt_version=EXTRACT_PROMPT_VERSION, schema_version=CLUES_SCHEMA_VERSION)
    llm_failed = False
    try:
        run.clues, run.extract_usage = await extract(complaint)
    except Exception as exc:  # provider down or invalid output after the retry: keyword clues, held for a human
        note_error(run, f"extract failed, used keyword fallback: {exc}")
        run.clues, run.extract_usage = await fake_extract(complaint)
        llm_failed = True
    if run.extract_usage.provider == "fake":
        run.prompt_version = run.schema_version = "keywords"

    try:
        result = engine(complaint, run.clues)
    except Exception as exc:  # engine bug; business cases come back as holds, not exceptions
        note_error(run, f"engine failed: {exc}")
        return run
    run.match, run.decision, run.evidence = result.match, result.decision, result.evidence
    if draft is None:
        draft = functools.partial(llm_draft, complaint=complaint)

    reply, usage, failed = await draft_or_template(draft, result, None, run)
    llm_failed |= failed
    run.draft_usage.append(usage)
    run.self_check = check(reply, result)
    while not run.self_check.passed and run.redraft_count < MAX_REDRAFTS:
        run.redraft_count += 1
        reply, usage, failed = await draft_or_template(draft, result, run.self_check.problems, run)
        llm_failed |= failed
        run.draft_usage.append(usage)
        run.self_check = check(reply, result)

    run.reply_text = reply
    run.prompt_version += "+" + ("code-template" if usage.provider == "fake" else DRAFT_PROMPT_VERSION)
    if not run.self_check.passed:
        run.decision = hold(run.decision, "self_check_failed")
    if llm_failed:
        run.decision = hold_llm_error(run.decision)
    return run
