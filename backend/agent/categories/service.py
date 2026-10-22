"""SERVICE_QUALITY handler. Owner: Dev A.

No transaction matching. Always INFO_ONLY — acknowledge and route.
"""
from __future__ import annotations

from backend.agent.tools import get_accounts, get_customer
from backend.contracts import (
    Calculation,
    Clues,
    Complaint,
    Decision,
    Evidence,
    MatchResult,
)

from .base import CategoryHandler
from .registry import register


@register
class ServiceQualityHandler(CategoryHandler):
    category = "SERVICE_QUALITY"
    base_priority = "P3"
    channel_family = None

    @property
    def reply_guidance(self) -> str:
        return (
            "Service quality complaint. Acknowledge the customer's experience, "
            "apologise for the inconvenience, and explain their feedback has been "
            "recorded. Do NOT promise refunds or compensation."
        )

    def match(self, complaint: Complaint, clues: Clues) -> tuple[MatchResult, Evidence]:
        customer = get_customer(complaint.customer_id)
        accounts = get_accounts(complaint.customer_id)
        evidence = Evidence(customer=customer, accounts=accounts)
        return MatchResult(status="none", category=self.category), evidence

    def decide(self, match: MatchResult, evidence: Evidence, complaint: Complaint, clues: Clues) -> Decision:
        return Decision(
            category=self.category,
            matched_txn_id=None,
            outcome="INFO_ONLY",
            priority=self.base_priority,
            reply_language="EN",
            route="AUTO_RESOLVE",
            rule_id="SVC.INFO_ONLY",
            calculation=Calculation(explanation="Service quality — no transaction, informational response only"),
        )
