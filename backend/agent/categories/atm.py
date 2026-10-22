"""ATM_NOT_DISPENSED handler. Owner: Dev A.

Match: ATM Withdrawal by amount and date (optionally location).
Policy: dispensed < requested from atm_journal → REFUND the shortfall. Else DECLINE.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from backend.agent.date_resolver import resolve_date
from backend.agent.tools import (
    find_transactions,
    get_accounts,
    get_atm_journal,
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
class ATMHandler(CategoryHandler):
    category = "ATM_NOT_DISPENSED"
    base_priority = "P2"
    channel_family = "atm"

    @property
    def reply_guidance(self) -> str:
        return (
            "ATM complaint. If refunding, state the shortfall clearly: "
            "'requested RMX, ATM dispensed RMY, refunding the difference of RMZ'. "
            "If declining, explain that the ATM journal confirms the full amount was dispensed."
        )

    def match(self, complaint: Complaint, clues: Clues) -> tuple[MatchResult, Evidence]:
        customer = get_customer(complaint.customer_id)
        accounts = get_accounts(complaint.customer_id)
        evidence = Evidence(customer=customer, accounts=accounts)

        if customer is None:
            return (
                MatchResult(status="none", category=self.category),
                evidence,
            )

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
                score += amt_score * 0.5
                reasons.append(f"amount match ({amt_score:.2f})")

            date_score = self.score_date(t["time"], date_range)
            if date_score > 0:
                score += date_score * 0.3
                reasons.append("date in range")

            if clues.atm_location:
                loc_score = self.score_counterparty(t.get("description", ""), clues.atm_location)
                if loc_score > 0:
                    score += loc_score * 0.2
                    reasons.append(f"location match ({loc_score:.2f})")
            elif clues.counterparty_name:
                loc_score = self.score_counterparty(t.get("description", ""), clues.counterparty_name)
                if loc_score > 0:
                    score += loc_score * 0.2
                    reasons.append(f"location match ({loc_score:.2f})")
            else:
                score += 0.1
                reasons.append("no location filter")

            if score > 0:
                candidates.append(Candidate(txn_id=t["txn_id"], score=min(score, 1.0), reasons=reasons))

        result = self.pick_best(candidates)
        result.category = self.category

        if result.txn_id:
            matched_txn = next((t for t in txns if t["txn_id"] == result.txn_id), None)
            journal = get_atm_journal(result.txn_id) if matched_txn else None
            evidence.matched_txn = matched_txn
            evidence.atm_journal = journal
            if matched_txn:
                evidence.allowed_txn_ids = [result.txn_id]
                amounts = [to_money(matched_txn["amount"])]
                if journal:
                    req = to_money(journal["requested_myr"])
                    disp = to_money(journal["dispensed_myr"])
                    amounts.extend([req, disp])
                    shortfall = req - disp
                    if shortfall > 0:
                        amounts.append(shortfall)
                evidence.allowed_amounts = amounts

        return result, evidence

    def decide(self, match: MatchResult, evidence: Evidence, complaint: Complaint, clues: Clues) -> Decision:
        base = dict(category=self.category, matched_txn_id=match.txn_id, priority=self.base_priority, reply_language="EN", route="AUTO_RESOLVE")

        if match.txn_id is None:
            return Decision(**base, outcome="DECLINE", rule_id="ATM.NO_MATCH",
                            calculation=Calculation(explanation="No matching ATM withdrawal found"))

        journal = evidence.atm_journal
        if journal is None:
            return Decision(**base, outcome="DECLINE", rule_id="ATM.NO_JOURNAL",
                            calculation=Calculation(explanation="No ATM journal entry for this withdrawal"))

        requested = to_money(journal["requested_myr"])
        dispensed = to_money(journal["dispensed_myr"])
        shortfall = requested - dispensed

        if shortfall > 0:
            return Decision(
                **base,
                outcome="REFUND",
                refund_amount_myr=shortfall,
                rule_id="ATM.SHORTFALL_REFUND",
                calculation=Calculation(
                    explanation=f"{requested} requested − {dispensed} dispensed = {shortfall} refund",
                    inputs={"requested": str(requested), "dispensed": str(dispensed), "shortfall": str(shortfall)},
                ),
            )

        return Decision(
            **base,
            outcome="DECLINE",
            rule_id="ATM.FULLY_DISPENSED",
            calculation=Calculation(
                explanation=f"ATM dispensed full amount ({dispensed})",
                inputs={"requested": str(requested), "dispensed": str(dispensed)},
            ),
        )
