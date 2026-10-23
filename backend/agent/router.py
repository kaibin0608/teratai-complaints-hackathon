"""Route, priority, reply language, hold overrides and SLA. Owner: Dev A."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from backend.agent.language_mix import check_mixed
from backend.agent.tools import get_auto_refund_limit, get_customer, get_db
from backend.contracts import Clues, Complaint, Decision, HoldReason, Priority
from starter.data import age_on

BUMP = {"P3": "P2", "P2": "P1", "P1": "P1"}


def hold(decision: Decision, reason: HoldReason) -> Decision:
    """Holds only push toward humans: INVESTIGATE stays FRAUD_TEAM, everything else goes to HUMAN_APPROVAL."""
    route = "FRAUD_TEAM" if decision.outcome == "INVESTIGATE" else "HUMAN_APPROVAL"
    return decision.model_copy(update={"hold_reason": decision.hold_reason or reason, "route": route})


def compute_priority(base_priority: str, complaint: Complaint) -> str:
    customer = get_customer(complaint.customer_id)
    if customer is None:
        return base_priority
    age = age_on(customer["date_of_birth"], complaint.received_at.date())
    if age >= 65:
        return BUMP.get(base_priority, base_priority)
    return base_priority


def compute_vulnerable(complaint: Complaint) -> bool:
    customer = get_customer(complaint.customer_id)
    if customer is None:
        return False
    return age_on(customer["date_of_birth"], complaint.received_at.date()) >= 65


def compute_language(clues: Clues, complaint: Complaint) -> str:
    customer = get_customer(complaint.customer_id)
    mixed = check_mixed(clues.is_mixed_language, complaint.text)
    if customer and (mixed or complaint.is_staff_note):
        return customer.get("preferred_language", clues.language)
    return clues.language


def compute_route(outcome: str, refund_amount: Decimal) -> str:
    if outcome == "INVESTIGATE":
        return "FRAUD_TEAM"
    if outcome == "DECLINE":
        return "HUMAN_APPROVAL"
    if outcome == "INFO_ONLY":
        return "AUTO_RESOLVE"
    if outcome == "REFUND" and refund_amount > get_auto_refund_limit():
        return "HUMAN_APPROVAL"
    return "AUTO_RESOLVE"


def finalize_decision(decision: Decision, complaint: Complaint, clues: Clues) -> Decision:
    """Apply priority bump, language, route, vulnerability, SLA to a raw handler decision."""
    priority = compute_priority(decision.priority, complaint)
    language = compute_language(clues, complaint)
    vulnerable = compute_vulnerable(complaint)
    route = compute_route(decision.outcome, decision.refund_amount_myr)
    policy_route = route

    ack_due, resolve_due = sla_due(complaint.received_at, priority)

    updated = decision.model_copy(update={
        "priority": priority,
        "reply_language": language,
        "route": route,
        "policy_route": policy_route,
        "vulnerable": vulnerable,
        "ack_due_at": ack_due,
        "resolve_due_at": resolve_due,
    })

    if updated.hold_reason:
        updated = hold(updated, updated.hold_reason)

    customer = get_customer(complaint.customer_id)
    if customer is None:  # the root cause of any no_match, so it replaces that reason
        updated = hold(updated.model_copy(update={"hold_reason": None}), "customer_not_found")

    return updated


def add_business_days(start: dt.datetime, days: int) -> dt.datetime:
    """Mon-Fri only; no public holidays (open question in PLAN.md)."""
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
