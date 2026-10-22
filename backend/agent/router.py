"""Route, priority, reply language, hold overrides and SLA. Owner: Dev A.

Step 0 provides the hold override and SLA due times, which the pipeline and stubs need.
"""
from __future__ import annotations

import datetime as dt

from backend.agent.tools import get_db
from backend.contracts import Decision, HoldReason, Priority


def hold(decision: Decision, reason: HoldReason) -> Decision:
    """Holds only push toward humans: INVESTIGATE stays FRAUD_TEAM, everything else goes to HUMAN_APPROVAL."""
    route = "FRAUD_TEAM" if decision.outcome == "INVESTIGATE" else "HUMAN_APPROVAL"
    return decision.model_copy(update={"hold_reason": decision.hold_reason or reason, "route": route})


def add_business_days(start: dt.datetime, days: int) -> dt.datetime:
    """Mon–Fri only; no public holidays (open question in PLAN.md)."""
    current = start
    while days > 0:
        current += dt.timedelta(days=1)
        if current.weekday() < 5:
            days -= 1
    return current


def sla_due(received_at: dt.datetime, priority: Priority) -> tuple[dt.datetime, dt.datetime]:
    """(acknowledge by, resolve by) from sla_policy.csv, in MYT."""
    row = get_db().sla[priority]
    ack = received_at + dt.timedelta(hours=int(row["acknowledge_within_hours"]))
    return ack, add_business_days(received_at, int(row["resolve_within_business_days"]))
