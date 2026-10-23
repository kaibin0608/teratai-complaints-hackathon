"""LLM step: decision + facts → customer reply in decision.reply_language. Owner: Dev B.

Code decides what the reply says (reply_facts); the LLM only words it. The provider and model come from LLM_DRAFT;
"fake:<anything>" returns the code-written reply, so tests and --no-draft need no network.
"""
from __future__ import annotations

import backend.agent.categories  # noqa: F401  (registers the handlers)
from backend.agent.categories.registry import get_handler
from backend.agent.reply_templates import render
from backend.contracts import Complaint, EngineResult, LLMUsage
from backend.llm.client import get_client
from backend.llm.prompts import build_draft_messages
from backend.llm.registry import step_config, step_reasoning


async def code_draft(result: EngineResult, feedback: list[str] | None = None) -> tuple[str, LLMUsage]:
    """The Drafter used for outages, fake:* config and --no-draft."""
    return render(result), LLMUsage(provider="fake", model="code-template")


async def draft(result: EngineResult, feedback: list[str] | None = None, *, complaint: Complaint) -> tuple[str, LLMUsage]:
    spec, _ = step_config("draft")
    if spec.provider == "fake":
        return await code_draft(result, feedback)
    guidance = get_handler(result.decision.category).reply_guidance
    messages = build_draft_messages(result, complaint, feedback, guidance)
    return await get_client().text(spec, messages, temperature=0.3, max_tokens=700,
                                   reasoning_effort=step_reasoning("draft"))
