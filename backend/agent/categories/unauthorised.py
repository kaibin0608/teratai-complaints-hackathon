"""UNAUTHORISED_CARD handler. Owner: Dev A.

Match: Card POS or e-Commerce debit by amount, merchant, date, card.
Policy: auth_method=None → REFUND. 3DS-OTP or Chip+PIN → INVESTIGATE.
        Unknown auth method → INVESTIGATE with hold_reason.
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

KNOWN_AUTH = {"None", "3DS-OTP", "Chip+PIN"}


@register
class UnauthorisedCardHandler(CategoryHandler):
    category = "UNAUTHORISED_CARD"
    base_priority = "P1"
    channel_family = "card"

    @property
    def reply_guidance(self) -> str:
        return (
            "Unauthorised card complaint. If refunding (no strong auth), reassure the customer "
            "the charge has been refunded. If investigating (OTP or chip+PIN was used), explain "
            "the transaction was authenticated and the fraud team will investigate further. "
            "Do NOT reveal the auth method details to the customer."
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
            card_last4=clues.card_last4,
        )

        if not txns and (clues.date_phrase or clues.card_last4):
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
                reasons.append(f"merchant ({cp_score:.2f})")

            date_score = self.score_date(t["time"], date_range)
            if date_score > 0:
                score += date_score * 0.2
                reasons.append("date in range")

            if clues.card_last4 and t.get("card_last4") == clues.card_last4:
                score += 0.1
                reasons.append("card match")

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
            return Decision(**base, outcome="DECLINE", rule_id="UNAUTH.NO_MATCH",
                            calculation=Calculation(explanation="No matching card transaction found"))

        txn = evidence.matched_txn
        auth = txn.get("auth_method", "") if txn else ""
        amount = to_money(txn["amount"]) if txn else to_money(0)

        if auth == "None" or auth == "":
            return Decision(
                **base,
                outcome="REFUND",
                refund_amount_myr=amount,
                rule_id="UNAUTH.NO_AUTH_REFUND",
                calculation=Calculation(
                    explanation=f"auth_method={auth}, no strong authentication → refund {amount}",
                    inputs={"auth_method": auth, "amount": str(amount)},
                ),
            )

        if auth in ("3DS-OTP", "Chip+PIN"):
            return Decision(
                **base,
                outcome="INVESTIGATE",
                rule_id="UNAUTH.STRONG_AUTH_INVESTIGATE",
                calculation=Calculation(
                    explanation=f"auth_method={auth}, strong authentication → fraud team investigates",
                    inputs={"auth_method": auth, "amount": str(amount)},
                ),
            )

        # Unknown auth method — never seen in training data, safe default
        return Decision(
            **base,
            outcome="INVESTIGATE",
            hold_reason="unknown_auth_method",
            rule_id="UNAUTH.UNKNOWN_AUTH",
            calculation=Calculation(
                explanation=f"auth_method={auth!r} is unknown → investigate, held for review",
                inputs={"auth_method": auth, "amount": str(amount)},
            ),
        )
