"""Route, priority, reply language, hold overrides and SLA. Owner: Dev A.

Step 0 provides only the hold override, which the pipeline needs.
"""
from __future__ import annotations

from backend.contracts import Decision, HoldReason


def hold(decision: Decision, reason: HoldReason) -> Decision:
    """Holds only push toward humans: INVESTIGATE stays FRAUD_TEAM, everything else goes to HUMAN_APPROVAL."""
    route = "FRAUD_TEAM" if decision.outcome == "INVESTIGATE" else "HUMAN_APPROVAL"
    return decision.model_copy(update={"hold_reason": decision.hold_reason or reason, "route": route})
