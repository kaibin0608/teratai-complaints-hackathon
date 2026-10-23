"""Second-issue check: does a complaint raise another, different problem? Owner: Dev B.

The LLM lists every issue it sees with the customer's own words (prompt issues-v1); code keeps only the ones that
are a different category, aren't a natural overlap, and whose quote really is in the complaint. The pipeline holds a
case for an officer when one survives (hold_reason second_issue). The check never changes a scored field, and any
failure means "no second issue", so the case behaves exactly as before.
"""
from __future__ import annotations

import re
from typing import Any

from backend.contracts import Complaint, LLMUsage, OtherIssue
from backend.llm.client import get_client
from backend.llm.prompts import ISSUES_WIRE_SCHEMA, build_issues_messages
from backend.llm.registry import issues_enabled, step_config, step_reasoning

MIN_QUOTE = 8  # characters; stops one-word quotes like "fee"
MAX_TOKENS = 1000  # the answer is short, but DeepSeek can spend 500-950 hidden tokens first (300 ran out 0.8% of the time)
NATURAL_OVERLAP = {  # mentioned as part of the main story, and these cases go to the fraud team anyway
    "SCAM_TRANSFER": {"FAILED_TRANSFER", "UNAUTHORISED_CARD"},
    "UNAUTHORISED_CARD": {"SCAM_TRANSFER"},
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _issues(data: Any) -> list[OtherIssue]:
    if not isinstance(data, dict) or not isinstance(data.get("issues"), list):
        raise TypeError("expected {\"issues\": [...]}")
    return [OtherIssue.model_validate(item) for item in data["issues"]]


async def detect_issues(complaint: Complaint) -> tuple[list[OtherIssue], LLMUsage | None]:
    """Every issue the LLM sees (main one included). Raises on provider or output errors; the pipeline treats that
    as no second issue. No call (and ([], None)) when the step is off or uses a fake provider."""
    if not issues_enabled():
        return [], None
    spec, json_mode = step_config("issues")
    if spec.provider == "fake":
        return [], None
    return await get_client().structured(
        spec, build_issues_messages(complaint), schema=ISSUES_WIRE_SCHEMA, schema_name="complaint_issues",
        convert=_issues, json_mode=json_mode, temperature=0.0, max_tokens=MAX_TOKENS,
        reasoning_effort=step_reasoning("issues"),
    )


def other_issues(issues: list[OtherIssue], category: str, complaint: Complaint) -> list[OtherIssue]:
    """The issues that make this a second-issue case: a different category, not a natural overlap, and a quote
    (at least MIN_QUOTE characters) that appears word for word in the subject or body. One per category."""
    text = _norm(f"{complaint.subject} {complaint.text}")
    skip = NATURAL_OVERLAP.get(category, set()) | {category}
    kept: dict[str, OtherIssue] = {}
    for issue in issues:
        quote = _norm(issue.quote)
        if issue.category in skip or issue.category in kept or len(quote) < MIN_QUOTE or quote not in text:
            continue
        kept[issue.category] = issue
    return list(kept.values())
