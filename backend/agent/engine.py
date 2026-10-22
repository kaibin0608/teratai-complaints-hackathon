"""Decision engine: match_and_decide. Owner: Dev A.

Wires category handlers + router into the Engine protocol.
"""
from __future__ import annotations

import backend.agent.categories  # noqa: F401 — triggers registration

from backend.agent.categories.registry import get_fallback_categories, get_handler
from backend.agent.router import finalize_decision, hold
from backend.contracts import (
    Clues,
    Complaint,
    EngineResult,
)


def match_and_decide(complaint: Complaint, clues: Clues) -> EngineResult:
    handler = get_handler(clues.category)
    match_result, evidence = handler.match(complaint, clues)

    if match_result.status == "none" and clues.category != "SERVICE_QUALITY":
        for fallback_cat in get_fallback_categories(clues.category):
            fb_handler = get_handler(fallback_cat)
            fb_match, fb_evidence = fb_handler.match(complaint, clues)
            if fb_match.status != "none":
                match_result = fb_match
                evidence = fb_evidence
                match_result.category = fallback_cat
                break

    decision = handler.decide(match_result, evidence, complaint, clues)

    if match_result.status == "ambiguous":
        decision = hold(decision, "ambiguous_match")
    elif match_result.status == "none" and clues.category != "SERVICE_QUALITY":
        decision = hold(decision, "no_match")

    decision = finalize_decision(decision, complaint, clues)

    return EngineResult(match=match_result, decision=decision, evidence=evidence)
