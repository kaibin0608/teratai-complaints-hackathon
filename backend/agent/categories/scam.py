"""SCAM_TRANSFER handler. Owner: Dev A.

Match: DuitNow/IBG transfer debit by recipient, amount, date.
Policy: Always INVESTIGATE — fraud team for recall attempt, no refund now.
"""
from __future__ import annotations

from backend.agent.date_resolver import resolve_date
from backend.agent.tools import (
    find_transactions,
    get_accounts,
    get_customer,
    get_match_window_days,
)
from backend.contracts import (
    Calculation,
    Candidate,
    Clues,
    Complaint,
    Decision,
    Evidence,
    MatchResult,
    to_money,
)

from .base import CategoryHandler
from .registry import register


@register
class ScamTransferHandler(CategoryHandler):
    category = "SCAM_TRANSFER"
    base_priority = "P1"
    channel_family = "transfer"

    @property
    def reply_guidance(self) -> str:
        return (
            "Scam complaint. This is a holding reply only — do NOT promise a refund. "
            "Acknowledge the report, say the fraud team will investigate and attempt a recall, "
            "and provide a timeline for next contact. Be empathetic but factual."
        )

    def match(self, complaint: Complaint, clues: Clues) -> tuple[MatchResult, Evidence]:
        customer = get_customer(complaint.customer_id)
        accounts = get_accounts(complaint.customer_id)
        evidence = Evidence(customer=customer, accounts=accounts)

        if customer is None:
            return MatchResult(status="none", category=self.category), evidence

        date_range = resolve_date(
            clues.date_phrase, clues.date_exact, complaint.received_at, get_match_window_days(),
        )

        txns = find_transactions(
            complaint.customer_id,
            complaint.received_at,
            channel_family=self.channel_family,
            date_range=date_range,
        )

        if not txns and clues.date_phrase:
            txns = find_transactions(
                complaint.customer_id,
                complaint.received_at,
                channel_family=self.channel_family,
            )

        candidates: list[Candidate] = []
        for t in txns:
            score = 0.0
            reasons: list[str] = []

            amt_score = self.score_amount(t["amount"], clues.amount_mentioned, clues.amount_approximate)
            if amt_score > 0:
                score += amt_score * 0.4
                reasons.append(f"amount ({amt_score:.2f})")

            cp_score = self.score_counterparty(t.get("merchant_or_counterparty", "") or t.get("description", ""), clues.counterparty_name)
            if cp_score > 0:
                score += cp_score * 0.3
                reasons.append(f"recipient ({cp_score:.2f})")

            date_score = self.score_date(t["time"], date_range)
            if date_score > 0:
                score += date_score * 0.2
                reasons.append("date in range")

            if clues.counterparty_bank:
                bank = t.get("counterparty_bank", "").lower()
                if clues.counterparty_bank.lower() in bank:
                    score += 0.1
                    reasons.append("bank match")

            if score > 0:
                candidates.append(Candidate(txn_id=t["txn_id"], score=min(score, 1.0), reasons=reasons))

        result = self.pick_best(candidates)
        result.category = self.category

        if result.txn_id:
            matched_txn = next((t for t in txns if t["txn_id"] == result.txn_id), None)
            evidence.matched_txn = matched_txn
            if matched_txn:
                evidence.allowed_txn_ids = [result.txn_id]
                evidence.allowed_amounts = [to_money(matched_txn["amount"])]

        return result, evidence

    def decide(self, match: MatchResult, evidence: Evidence, complaint: Complaint, clues: Clues) -> Decision:
        base = dict(category=self.category, matched_txn_id=match.txn_id, priority=self.base_priority, reply_language="EN", route="AUTO_RESOLVE")

        if match.txn_id is None:
            return Decision(**base, outcome="INVESTIGATE", rule_id="SCAM.NO_MATCH_INVESTIGATE",
                            calculation=Calculation(explanation="Scam reported, no matching transfer found — investigate anyway"))

        txn = evidence.matched_txn
        amount = to_money(txn["amount"]) if txn else to_money(0)

        return Decision(
            **base,
            outcome="INVESTIGATE",
            rule_id="SCAM.ALWAYS_INVESTIGATE",
            calculation=Calculation(
                explanation=f"Scam transfer of {amount} — fraud team for recall attempt, no refund now",
                inputs={"amount": str(amount)},
            ),
        )
