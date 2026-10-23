"""DUPLICATE_CHARGE handler. Owner: Dev A.

Match: Card POS or e-Commerce debit by amount, merchant, date, card.
Policy: If a valid duplicate pair exists (same amount, merchant, within 10 min,
        neither reversed) → REFUND the later charge. No valid pair → DECLINE.
"""
from __future__ import annotations

import datetime as dt

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

DUPLICATE_WINDOW_SECONDS = 600  # 10 minutes


@register
class DuplicateChargeHandler(CategoryHandler):
    category = "DUPLICATE_CHARGE"
    base_priority = "P2"
    channel_family = "card"

    @property
    def reply_guidance(self) -> str:
        return (
            "Duplicate charge complaint. If refunding, state the amount and that the "
            "duplicate charge has been refunded. If declining because no duplicate was "
            "found, explain we reviewed the transactions and each charge is distinct."
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

            cp_score = self.score_counterparty(
                t.get("merchant_or_counterparty", "") or t.get("description", ""),
                clues.counterparty_name,
            )
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
        if result.status == "ambiguous":
            result = self._resolve_tied_pair(result, candidates, txns)
        result.category = self.category

        if result.txn_id:
            matched_txn = next((t for t in txns if t["txn_id"] == result.txn_id), None)
            evidence.matched_txn = matched_txn
            if matched_txn:
                evidence.allowed_txn_ids = [result.txn_id]
                evidence.allowed_amounts = [to_money(matched_txn["amount"])]
                pair = self._find_pair(matched_txn, txns)
                if pair:
                    evidence.related_txns = [pair]
                    evidence.allowed_txn_ids.append(pair["txn_id"])

        return result, evidence

    def decide(self, match: MatchResult, evidence: Evidence, complaint: Complaint, clues: Clues) -> Decision:
        base = dict(category=self.category, matched_txn_id=match.txn_id, priority=self.base_priority, reply_language="EN", route="AUTO_RESOLVE")

        if match.txn_id is None:
            return Decision(**base, outcome="DECLINE", rule_id="DUP.NO_MATCH",
                            calculation=Calculation(explanation="No matching card transaction found"))

        txn = evidence.matched_txn
        amount = to_money(txn["amount"]) if txn else to_money(0)

        if not evidence.related_txns:
            all_txns = find_transactions(
                complaint.customer_id,
                complaint.received_at,
                channel_family=self.channel_family,
            )
            pair = self._find_pair(txn, all_txns) if txn else None
        else:
            pair = evidence.related_txns[0]

        if pair is None:
            return Decision(
                **base, outcome="DECLINE", rule_id="DUP.NO_PAIR",
                calculation=Calculation(
                    explanation=f"No duplicate pair found for {amount} — each charge is distinct",
                    inputs={"amount": str(amount), "merchant": txn.get("merchant_or_counterparty", "") if txn else ""},
                ),
            )

        pair_reversed = get_reversal(pair["txn_id"])
        matched_reversed = get_reversal(match.txn_id)

        if pair_reversed or matched_reversed:
            return Decision(
                **base, outcome="DECLINE", rule_id="DUP.ALREADY_REVERSED",
                calculation=Calculation(
                    explanation=f"Duplicate pair exists but already reversed",
                    inputs={"amount": str(amount), "matched_txn": match.txn_id, "pair_txn": pair["txn_id"]},
                ),
            )

        return Decision(
            **base, outcome="REFUND", refund_amount_myr=amount,
            rule_id="DUP.VALID_PAIR_REFUND",
            calculation=Calculation(
                explanation=f"Duplicate charge of {amount} — valid pair within 10 min, neither reversed, refund later charge",
                inputs={
                    "amount": str(amount),
                    "matched_txn": match.txn_id,
                    "pair_txn": pair["txn_id"],
                    "time_diff_seconds": str(abs(int((txn["time"] - pair["time"]).total_seconds()))) if txn else "?",
                },
            ),
        )

    def _resolve_tied_pair(self, result: MatchResult, candidates: list[Candidate], txns: list[dict]) -> MatchResult:
        """Two top candidates with the same score that are each other's duplicate pair are the duplicate itself:
        take the later charge (the one policy refunds) and call it confident. Any other tie stays ambiguous."""
        if len(candidates) < 2 or candidates[0].score != candidates[1].score:
            return result
        if len(candidates) > 2 and candidates[2].score > candidates[0].score - 0.15:
            return result
        by_id = {t["txn_id"]: t for t in txns}
        first, second = by_id.get(candidates[0].txn_id), by_id.get(candidates[1].txn_id)
        if not first or not second or self._find_pair(first, [second]) is None:
            return result
        later = max(first, second, key=lambda t: t["time"])
        ordered = sorted(candidates[:2], key=lambda c: c.txn_id != later["txn_id"]) + candidates[2:]
        return MatchResult(status="confident", txn_id=later["txn_id"], candidates=ordered, category=self.category)

    @staticmethod
    def _find_pair(txn: dict, all_txns: list[dict]) -> dict | None:
        """Find the duplicate pair for a given card transaction.

        Pair criteria: same amount, same merchant, card channel, within 10 min, different txn_id.
        Returns the pair transaction or None.
        """
        if txn is None:
            return None
        txn_id = txn["txn_id"]
        amt = txn["amount"]
        txn_time = txn["time"]
        merchant = txn.get("merchant_or_counterparty", "")

        best_pair = None
        best_diff = float("inf")

        for t in all_txns:
            if t["txn_id"] == txn_id:
                continue
            if t["channel"] not in ("Card POS", "Card e-Commerce"):
                continue
            if abs(t["amount"] - amt) > 0.01:
                continue
            if merchant and t.get("merchant_or_counterparty", "") != merchant:
                continue
            time_diff = abs((t["time"] - txn_time).total_seconds())
            if time_diff > DUPLICATE_WINDOW_SECONDS:
                continue
            if time_diff < best_diff:
                best_diff = time_diff
                best_pair = t

        return best_pair
