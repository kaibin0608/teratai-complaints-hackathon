"""FEE_DISPUTE handler. Owner: Dev A.

Match: Fee charge by description/date on customer's accounts.
Policy: refund = charged - amount_due. Waivers: Basic Savings monthly = RM0,
        debit annual waived if customer 60+ on charge date, credit annual
        waived if charge date < first anniversary of account open_date.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from backend.agent.date_resolver import resolve_date, resolve_fee_month
from backend.agent.tools import (
    find_transactions,
    get_account,
    get_accounts,
    get_customer,
    get_fee_schedule_for_product,
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


def _parse_date(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%Y-%m-%d").date()


def _age_on(dob: str, ref: dt.date) -> int:
    d = _parse_date(dob)
    return (ref - d).days // 365


@register
class FeeDisputeHandler(CategoryHandler):
    category = "FEE_DISPUTE"
    base_priority = "P3"
    channel_family = "fee"

    @property
    def reply_guidance(self) -> str:
        return (
            "Fee dispute complaint. If refunding (overcharge or waived fee), state "
            "the refund amount and why. If declining, explain the fee is correct per "
            "the schedule and no waiver applies."
        )

    def match(self, complaint: Complaint, clues: Clues) -> tuple[MatchResult, Evidence]:
        customer = get_customer(complaint.customer_id)
        accounts = get_accounts(complaint.customer_id)
        evidence = Evidence(customer=customer, accounts=accounts)

        if customer is None:
            return MatchResult(status="none", category=self.category), evidence

        date_range = resolve_fee_month(
            getattr(clues, "fee_month", None),
            clues.date_phrase,
            complaint.received_at,
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
                score += amt_score * 0.35
                reasons.append(f"amount ({amt_score:.2f})")

            fee_desc = t.get("description", "").lower()
            if clues.fee_type:
                ft = clues.fee_type.lower()
                words = [tok for tok in ft.split() if len(tok) > 3]
                if ft in fee_desc or (words and all(tok in fee_desc for tok in words)):
                    score += 0.35
                    reasons.append("fee type match")

            date_score = self.score_date(t["time"], date_range)
            if date_score > 0:
                score += date_score * 0.2
                reasons.append("date in range")

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
                acct = get_account(matched_txn["account_id"])
                if acct:
                    fee_rows = get_fee_schedule_for_product(acct["product"])
                    evidence.fee_schedule_row = self._match_fee_row(matched_txn, fee_rows)

        return result, evidence

    def decide(self, match: MatchResult, evidence: Evidence, complaint: Complaint, clues: Clues) -> Decision:
        base = dict(category=self.category, matched_txn_id=match.txn_id, priority=self.base_priority, reply_language="EN", route="AUTO_RESOLVE")

        if match.txn_id is None:
            return Decision(**base, outcome="DECLINE", rule_id="FEE.NO_MATCH",
                            calculation=Calculation(explanation="No matching fee transaction found"))

        txn = evidence.matched_txn
        if txn is None:
            return Decision(**base, outcome="DECLINE", rule_id="FEE.NO_MATCH",
                            calculation=Calculation(explanation="No matching fee transaction found"))

        charged = to_money(txn["amount"])
        desc = txn.get("description", "")
        acct = get_account(txn["account_id"])

        if acct is None:
            return Decision(**base, outcome="DECLINE", rule_id="FEE.NO_ACCOUNT",
                            calculation=Calculation(explanation="Fee account not found"))

        product = acct["product"]
        fee_rows = get_fee_schedule_for_product(product)
        fee_row = evidence.fee_schedule_row or self._match_fee_row(txn, fee_rows)

        if fee_row is None:
            return Decision(**base, outcome="DECLINE", rule_id="FEE.NO_SCHEDULE",
                            calculation=Calculation(explanation=f"No fee schedule for {product} / {desc}"))

        amount_due = to_money(fee_row["amount_myr"])
        waiver = fee_row.get("waiver_rule", "")
        waiver_applied = ""
        charge_date = txn["time"].date() if hasattr(txn["time"], "date") else _parse_date(txn["txn_time"][:10])

        customer = evidence.customer
        if "not chargeable" in waiver.lower() and "basic savings" in waiver.lower():
            amount_due = to_money(0)
            waiver_applied = "Basic Savings not chargeable"
        elif "aged 60" in waiver and customer:
            age = _age_on(customer["date_of_birth"], charge_date)
            if age >= 60:
                amount_due = to_money(0)
                waiver_applied = f"customer aged {age} on charge date (60+ waiver)"
        elif "first anniversary" in waiver:
            open_date = _parse_date(acct["open_date"])
            first_anniv = open_date.replace(year=open_date.year + 1)
            if charge_date < first_anniv:
                amount_due = to_money(0)
                waiver_applied = f"charge date {charge_date} before first anniversary {first_anniv}"

        refund = max(charged - amount_due, to_money(0))
        inputs = {
            "charged": str(charged),
            "amount_due": str(amount_due),
            "product": product,
            "fee_code": fee_row.get("fee_code", ""),
        }
        if waiver_applied:
            inputs["waiver"] = waiver_applied

        if refund > 0:
            evidence.allowed_amounts.append(refund)
            evidence.allowed_amounts.append(amount_due)
            return Decision(
                **base, outcome="REFUND", refund_amount_myr=refund,
                rule_id="FEE.OVERCHARGE_REFUND",
                calculation=Calculation(
                    explanation=f"Charged {charged}, due {amount_due} → refund {refund}",
                    inputs=inputs,
                ),
            )

        return Decision(
            **base, outcome="DECLINE", rule_id="FEE.CORRECT_CHARGE",
            calculation=Calculation(
                explanation=f"Charged {charged}, due {amount_due} — fee is correct, no refund",
                inputs=inputs,
            ),
        )

    @staticmethod
    def _match_fee_row(txn: dict, fee_rows: list[dict]) -> dict | None:
        desc = txn.get("description", "").lower()
        for r in fee_rows:
            if r["fee_name"].lower() in desc:
                return r
        return None
