"""FAILED_TRANSFER handler. Owner: Dev A.

Match: DuitNow/IBG transfer debit by recipient, amount, date — regardless of status.
Policy: Failed + no reversal → REFUND. Reversal exists → DECLINE. Completed → DECLINE.
"""
from __future__ import annotations

from backend.agent.date_resolver import resolve_date
from backend.agent.tools import (
    find_transactions,
    get_accounts,
    get_customer,
    get_match_window_days,
    get_reversal,
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
class FailedTransferHandler(CategoryHandler):
    category = "FAILED_TRANSFER"
    base_priority = "P2"
    channel_family = "transfer"

    @property
    def reply_guidance(self) -> str:
        return (
            "Failed transfer complaint. If refunding, state the amount and that the failed "
            "transfer has been refunded. If declining because a reversal exists, tell the "
            "customer when the reversal was processed. If declining because the transfer "
            "completed, explain the money reached the recipient."
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

            cp_score = self.score_counterparty(t.get("description", ""), clues.counterparty_name)
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
            reversal = get_reversal(result.txn_id)
            evidence.matched_txn = matched_txn
            evidence.reversal = reversal
            if matched_txn:
                evidence.allowed_txn_ids = [result.txn_id]
                evidence.allowed_amounts = [to_money(matched_txn["amount"])]
                if reversal:
                    evidence.allowed_txn_ids.append(reversal["txn_id"])
                    evidence.allowed_amounts.append(to_money(reversal["amount"]))

        return result, evidence

    def decide(self, match: MatchResult, evidence: Evidence, complaint: Complaint, clues: Clues) -> Decision:
        base = dict(category=self.category, matched_txn_id=match.txn_id, priority=self.base_priority, reply_language="EN", route="AUTO_RESOLVE")

        if match.txn_id is None:
            return Decision(**base, outcome="DECLINE", rule_id="FAILED.NO_MATCH",
                            calculation=Calculation(explanation="No matching transfer found"))

        txn = evidence.matched_txn
        status = txn.get("status", "") if txn else ""
        amount = to_money(txn["amount"]) if txn else to_money(0)
        reversal = evidence.reversal

        if status == "Completed":
            return Decision(
                **base, outcome="DECLINE", rule_id="FAILED.COMPLETED",
                calculation=Calculation(
                    explanation=f"Transfer {amount} completed — money reached the recipient",
                    inputs={"status": status, "amount": str(amount)},
                ),
            )

        if reversal:
            rev_time = reversal.get("txn_time", "")
            return Decision(
                **base, outcome="DECLINE", rule_id="FAILED.ALREADY_REVERSED",
                calculation=Calculation(
                    explanation=f"Transfer {amount} already reversed on {rev_time}",
                    inputs={"status": status, "amount": str(amount), "reversal_txn": reversal["txn_id"], "reversal_time": rev_time},
                ),
            )

        if status == "Failed":
            return Decision(
                **base, outcome="REFUND", refund_amount_myr=amount,
                rule_id="FAILED.FAILED_NO_REVERSAL",
                calculation=Calculation(
                    explanation=f"Transfer {amount} failed, no reversal → refund",
                    inputs={"status": status, "amount": str(amount)},
                ),
            )

        return Decision(
            **base, outcome="DECLINE", rule_id="FAILED.UNKNOWN_STATUS",
            calculation=Calculation(
                explanation=f"Transfer status={status!r}, cannot confirm failure → decline",
                inputs={"status": status, "amount": str(amount)},
            ),
        )
