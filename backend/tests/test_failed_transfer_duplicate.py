"""Tests for FAILED_TRANSFER and DUPLICATE_CHARGE handlers. Owner: Dev A."""
import asyncio
import csv
from decimal import Decimal
from pathlib import Path

import pytest

import backend.agent.categories  # registers handlers
from backend.agent.categories.registry import get_handler
from backend.agent.tools import get_customer, get_reversal, load_complaint
from backend.contracts import Calculation, Clues, Decision, Evidence, MatchResult, to_money

DATA = Path(__file__).resolve().parent.parent.parent / "data"
LABELS = list(csv.DictReader(open(DATA / "labels_train.csv", encoding="utf-8")))
FAILED_LABELS = [l for l in LABELS if l["category"] == "FAILED_TRANSFER"]
DUP_LABELS = [l for l in LABELS if l["category"] == "DUPLICATE_CHARGE"]

failed_handler = get_handler("FAILED_TRANSFER")
dup_handler = get_handler("DUPLICATE_CHARGE")


# === FAILED_TRANSFER ===

class TestFailedTransferPolicy:
    @pytest.mark.parametrize("label", FAILED_LABELS, ids=lambda l: l["complaint_id"])
    def test_outcome_and_refund(self, label):
        complaint = load_complaint(label["complaint_id"])
        gold_txn_id = label["matched_txn_id"]
        expected_outcome = label["outcome"]
        expected_refund = to_money(label["refund_amount_myr"])

        from backend.agent.tools import get_db
        txn = get_db().txns.get(gold_txn_id)
        reversal = get_reversal(gold_txn_id)
        match = MatchResult(status="confident", txn_id=gold_txn_id, category="FAILED_TRANSFER")
        evidence = Evidence(customer=get_customer(complaint.customer_id), matched_txn=txn, reversal=reversal)

        decision = failed_handler.decide(match, evidence, complaint, Clues(category="FAILED_TRANSFER", language="EN"))
        assert decision.outcome == expected_outcome, (
            f"{label['complaint_id']}: expected {expected_outcome}, got {decision.outcome}. "
            f"status={txn.get('status') if txn else '?'}, reversal={'Y' if reversal else 'N'}"
        )
        assert decision.refund_amount_myr == expected_refund


class TestFailedTransferMatching:
    SAMPLE = [l["complaint_id"] for l in FAILED_LABELS[:20]]
    LABEL_MAP = {l["complaint_id"]: l for l in FAILED_LABELS}

    @pytest.mark.parametrize("complaint_id", SAMPLE)
    def test_match_finds_gold_txn(self, complaint_id):
        label = self.LABEL_MAP[complaint_id]
        complaint = load_complaint(complaint_id)
        from backend.agent.stubs import fake_extract
        clues, _ = asyncio.run(fake_extract(complaint))
        clues = clues.model_copy(update={"category": "FAILED_TRANSFER"})
        match_result, evidence = failed_handler.match(complaint, clues)
        candidate_ids = [c.txn_id for c in match_result.candidates]
        assert label["matched_txn_id"] in candidate_ids, (
            f"{complaint_id}: gold txn {label['matched_txn_id']} not in candidates"
        )


class TestFailedTransferBoundaries:
    def _decide(self, status, has_reversal=False, amount="500.00"):
        match = MatchResult(status="confident", txn_id="TXN-FAKE", category="FAILED_TRANSFER")
        txn = {"txn_id": "TXN-FAKE", "amount": float(amount), "status": status}
        reversal = {"txn_id": "TXN-REV", "amount": float(amount), "txn_time": "2026-08-01 12:00:00"} if has_reversal else None
        evidence = Evidence(matched_txn=txn, reversal=reversal)
        complaint = load_complaint("CMP-00244")
        return failed_handler.decide(match, evidence, complaint, Clues(category="FAILED_TRANSFER", language="EN"))

    def test_failed_no_reversal_is_refund(self):
        d = self._decide("Failed", has_reversal=False)
        assert d.outcome == "REFUND"
        assert d.refund_amount_myr == Decimal("500.00")
        assert d.rule_id == "FAILED.FAILED_NO_REVERSAL"

    def test_failed_with_reversal_is_decline(self):
        d = self._decide("Failed", has_reversal=True)
        assert d.outcome == "DECLINE"
        assert d.rule_id == "FAILED.ALREADY_REVERSED"

    def test_completed_is_decline(self):
        d = self._decide("Completed")
        assert d.outcome == "DECLINE"
        assert d.rule_id == "FAILED.COMPLETED"

    def test_unknown_status_is_decline(self):
        d = self._decide("Pending")
        assert d.outcome == "DECLINE"
        assert d.rule_id == "FAILED.UNKNOWN_STATUS"

    def test_no_match_is_decline(self):
        match = MatchResult(status="none", txn_id=None, category="FAILED_TRANSFER")
        evidence = Evidence()
        complaint = load_complaint("CMP-00244")
        d = failed_handler.decide(match, evidence, complaint, Clues(category="FAILED_TRANSFER", language="EN"))
        assert d.outcome == "DECLINE"
        assert d.rule_id == "FAILED.NO_MATCH"


# === DUPLICATE_CHARGE ===

class TestDuplicateChargePolicy:
    @pytest.mark.parametrize("label", DUP_LABELS, ids=lambda l: l["complaint_id"])
    def test_outcome_and_refund(self, label):
        complaint = load_complaint(label["complaint_id"])
        gold_txn_id = label["matched_txn_id"]
        expected_outcome = label["outcome"]
        expected_refund = to_money(label["refund_amount_myr"])

        from backend.agent.tools import get_db
        txn = get_db().txns.get(gold_txn_id)
        match = MatchResult(status="confident", txn_id=gold_txn_id, category="DUPLICATE_CHARGE")
        evidence = Evidence(customer=get_customer(complaint.customer_id), matched_txn=txn)

        decision = dup_handler.decide(match, evidence, complaint, Clues(category="DUPLICATE_CHARGE", language="EN"))
        assert decision.outcome == expected_outcome, (
            f"{label['complaint_id']}: expected {expected_outcome}, got {decision.outcome}. "
            f"txn_amt={txn.get('amount') if txn else '?'}"
        )
        assert decision.refund_amount_myr == expected_refund


class TestDuplicateChargeMatching:
    SAMPLE = [l["complaint_id"] for l in DUP_LABELS[:20]]
    LABEL_MAP = {l["complaint_id"]: l for l in DUP_LABELS}

    @pytest.mark.parametrize("complaint_id", SAMPLE)
    def test_match_finds_gold_txn(self, complaint_id):
        label = self.LABEL_MAP[complaint_id]
        complaint = load_complaint(complaint_id)
        from backend.agent.stubs import fake_extract
        clues, _ = asyncio.run(fake_extract(complaint))
        clues = clues.model_copy(update={"category": "DUPLICATE_CHARGE"})
        match_result, evidence = dup_handler.match(complaint, clues)
        candidate_ids = [c.txn_id for c in match_result.candidates]
        assert label["matched_txn_id"] in candidate_ids, (
            f"{complaint_id}: gold txn {label['matched_txn_id']} not in candidates"
        )


class TestDuplicateChargeBoundaries:
    def test_valid_pair_is_refund(self):
        """Two card charges, same amount/merchant, 5 min apart, neither reversed."""
        from backend.agent.categories.duplicate import DuplicateChargeHandler
        import datetime as _dt
        txn = {"txn_id": "TXN-A", "amount": 100.0, "channel": "Card POS",
               "merchant_or_counterparty": "Shop X", "time": _dt.datetime(2026, 8, 1, 12, 5, 0)}
        pair = {"txn_id": "TXN-B", "amount": 100.0, "channel": "Card POS",
                "merchant_or_counterparty": "Shop X", "time": _dt.datetime(2026, 8, 1, 12, 0, 0)}

        match = MatchResult(status="confident", txn_id="TXN-A", category="DUPLICATE_CHARGE")
        evidence = Evidence(matched_txn=txn, related_txns=[pair])
        complaint = load_complaint("CMP-00244")
        d = dup_handler.decide(match, evidence, complaint, Clues(category="DUPLICATE_CHARGE", language="EN"))
        assert d.outcome == "REFUND"
        assert d.refund_amount_myr == Decimal("100.00")
        assert d.rule_id == "DUP.VALID_PAIR_REFUND"

    def test_no_pair_is_decline(self):
        import datetime as _dt
        txn = {"txn_id": "TXN-A", "amount": 100.0, "channel": "Card POS",
               "merchant_or_counterparty": "Shop X", "time": _dt.datetime(2026, 8, 1, 12, 0, 0)}
        match = MatchResult(status="confident", txn_id="TXN-A", category="DUPLICATE_CHARGE")
        evidence = Evidence(matched_txn=txn, related_txns=[])
        complaint = load_complaint("CMP-00244")
        d = dup_handler.decide(match, evidence, complaint, Clues(category="DUPLICATE_CHARGE", language="EN"))
        assert d.outcome == "DECLINE"
        assert d.rule_id == "DUP.NO_PAIR"

    def test_no_match_is_decline(self):
        match = MatchResult(status="none", txn_id=None, category="DUPLICATE_CHARGE")
        evidence = Evidence()
        complaint = load_complaint("CMP-00244")
        d = dup_handler.decide(match, evidence, complaint, Clues(category="DUPLICATE_CHARGE", language="EN"))
        assert d.outcome == "DECLINE"
        assert d.rule_id == "DUP.NO_MATCH"

    def test_pair_over_10_min_not_found(self):
        """Pair more than 10 min apart should not count."""
        from backend.agent.categories.duplicate import DuplicateChargeHandler
        import datetime as _dt
        txn = {"txn_id": "TXN-A", "amount": 100.0, "channel": "Card POS",
               "merchant_or_counterparty": "Shop X", "time": _dt.datetime(2026, 8, 1, 12, 0, 0)}
        other = {"txn_id": "TXN-B", "amount": 100.0, "channel": "Card POS",
                 "merchant_or_counterparty": "Shop X", "time": _dt.datetime(2026, 8, 1, 12, 11, 0)}
        pair = DuplicateChargeHandler._find_pair(txn, [txn, other])
        assert pair is None

    def test_pair_exactly_10_min_is_found(self):
        """Pair exactly 600 seconds apart should count."""
        from backend.agent.categories.duplicate import DuplicateChargeHandler
        import datetime as _dt
        txn = {"txn_id": "TXN-A", "amount": 100.0, "channel": "Card POS",
               "merchant_or_counterparty": "Shop X", "time": _dt.datetime(2026, 8, 1, 12, 0, 0)}
        other = {"txn_id": "TXN-B", "amount": 100.0, "channel": "Card POS",
                 "merchant_or_counterparty": "Shop X", "time": _dt.datetime(2026, 8, 1, 12, 10, 0)}
        pair = DuplicateChargeHandler._find_pair(txn, [txn, other])
        assert pair is not None
        assert pair["txn_id"] == "TXN-B"

    def test_different_merchant_no_pair(self):
        from backend.agent.categories.duplicate import DuplicateChargeHandler
        import datetime as _dt
        txn = {"txn_id": "TXN-A", "amount": 100.0, "channel": "Card POS",
               "merchant_or_counterparty": "Shop X", "time": _dt.datetime(2026, 8, 1, 12, 0, 0)}
        other = {"txn_id": "TXN-B", "amount": 100.0, "channel": "Card POS",
                 "merchant_or_counterparty": "Shop Y", "time": _dt.datetime(2026, 8, 1, 12, 5, 0)}
        pair = DuplicateChargeHandler._find_pair(txn, [txn, other])
        assert pair is None
