"""Tests for ATM_NOT_DISPENSED handler against training labels. Owner: Dev A."""
import csv
from decimal import Decimal
from pathlib import Path

import pytest

import backend.agent.categories  # registers handlers
from backend.agent.categories.atm import ATMHandler
from backend.agent.categories.registry import get_handler
from backend.agent.tools import get_atm_journal, get_customer, load_complaint
from backend.contracts import Clues, to_money

DATA = Path(__file__).resolve().parent.parent.parent / "data"
LABELS = list(csv.DictReader(open(DATA / "labels_train.csv", encoding="utf-8")))
ATM_LABELS = [l for l in LABELS if l["category"] == "ATM_NOT_DISPENSED"]

handler = get_handler("ATM_NOT_DISPENSED")


def test_handler_registered():
    assert isinstance(handler, ATMHandler)


def test_base_priority():
    assert handler.base_priority == "P2"


class TestATMPolicy:
    """Test decide() with gold transaction IDs — isolates policy from matching."""

    @pytest.mark.parametrize("label", ATM_LABELS, ids=lambda l: l["complaint_id"])
    def test_outcome_and_refund(self, label):
        complaint = load_complaint(label["complaint_id"])
        gold_txn_id = label["matched_txn_id"]
        expected_outcome = label["outcome"]
        expected_refund = to_money(label["refund_amount_myr"])

        clues = Clues(category="ATM_NOT_DISPENSED", language="EN")

        # Build match result and evidence as if matching succeeded
        from backend.agent.tools import get_db
        db = get_db()
        txn = db.txns.get(gold_txn_id)
        journal = get_atm_journal(gold_txn_id)
        from backend.contracts import Evidence, MatchResult
        match = MatchResult(status="confident", txn_id=gold_txn_id, category="ATM_NOT_DISPENSED")
        evidence = Evidence(
            customer=get_customer(complaint.customer_id),
            matched_txn=txn,
            atm_journal=journal,
        )

        decision = handler.decide(match, evidence, complaint, clues)
        assert decision.outcome == expected_outcome, (
            f"{label['complaint_id']}: expected {expected_outcome}, got {decision.outcome}. "
            f"journal={journal}"
        )
        assert decision.refund_amount_myr == expected_refund, (
            f"{label['complaint_id']}: expected refund {expected_refund}, got {decision.refund_amount_myr}"
        )


class TestATMMatching:
    """Test match() finds the correct transaction for a sample of ATM complaints."""

    SAMPLE_IDS = [l["complaint_id"] for l in ATM_LABELS[:20]]
    LABEL_MAP = {l["complaint_id"]: l for l in ATM_LABELS}

    @pytest.mark.parametrize("complaint_id", SAMPLE_IDS)
    def test_match_finds_gold_txn(self, complaint_id):
        label = self.LABEL_MAP[complaint_id]
        complaint = load_complaint(complaint_id)
        gold_txn_id = label["matched_txn_id"]

        # Use fake clues (keyword extraction) since we don't have the real LLM
        from backend.agent.stubs import fake_extract
        import asyncio
        clues, _ = asyncio.run(fake_extract(complaint))
        clues = clues.model_copy(update={"category": "ATM_NOT_DISPENSED"})

        match_result, evidence = handler.match(complaint, clues)

        # The gold txn should be in the candidates
        candidate_ids = [c.txn_id for c in match_result.candidates]
        assert gold_txn_id in candidate_ids, (
            f"{complaint_id}: gold txn {gold_txn_id} not in candidates {candidate_ids[:5]}"
        )


class TestATMBoundaries:
    """Edge cases from the guardrail checklist."""

    def test_fully_dispensed_is_decline(self):
        """ATM journal shows full dispensal → DECLINE."""
        from backend.contracts import Evidence, MatchResult
        match = MatchResult(status="confident", txn_id="TXN-0000030", category="ATM_NOT_DISPENSED")
        txn = {"txn_id": "TXN-0000030", "amount": 500.0}
        journal = {"txn_id": "TXN-0000030", "requested_myr": "500.00", "dispensed_myr": "500.00", "journal_status": "OK"}
        evidence = Evidence(matched_txn=txn, atm_journal=journal)
        complaint = load_complaint("CMP-00244")
        clues = Clues(category="ATM_NOT_DISPENSED", language="EN")
        decision = handler.decide(match, evidence, complaint, clues)
        assert decision.outcome == "DECLINE"
        assert decision.refund_amount_myr == Decimal("0.00")

    def test_shortfall_refund_exact_amount(self):
        """requested=1500, dispensed=950 → refund=550."""
        from backend.contracts import Evidence, MatchResult
        match = MatchResult(status="confident", txn_id="TXN-FAKE", category="ATM_NOT_DISPENSED")
        journal = {"txn_id": "TXN-FAKE", "requested_myr": "1500.00", "dispensed_myr": "950.00", "journal_status": "Partial"}
        evidence = Evidence(matched_txn={"txn_id": "TXN-FAKE", "amount": 1500.0}, atm_journal=journal)
        complaint = load_complaint("CMP-00244")
        clues = Clues(category="ATM_NOT_DISPENSED", language="EN")
        decision = handler.decide(match, evidence, complaint, clues)
        assert decision.outcome == "REFUND"
        assert decision.refund_amount_myr == Decimal("550.00")
        assert "550.00" in decision.calculation.explanation

    def test_no_journal_is_decline(self):
        """Missing ATM journal → DECLINE (can't confirm shortfall)."""
        from backend.contracts import Evidence, MatchResult
        match = MatchResult(status="confident", txn_id="TXN-FAKE", category="ATM_NOT_DISPENSED")
        evidence = Evidence(matched_txn={"txn_id": "TXN-FAKE", "amount": 500.0}, atm_journal=None)
        complaint = load_complaint("CMP-00244")
        clues = Clues(category="ATM_NOT_DISPENSED", language="EN")
        decision = handler.decide(match, evidence, complaint, clues)
        assert decision.outcome == "DECLINE"
        assert decision.rule_id == "ATM.NO_JOURNAL"

    def test_no_match_is_decline(self):
        from backend.contracts import Evidence, MatchResult
        match = MatchResult(status="none", txn_id=None, category="ATM_NOT_DISPENSED")
        evidence = Evidence()
        complaint = load_complaint("CMP-00244")
        clues = Clues(category="ATM_NOT_DISPENSED", language="EN")
        decision = handler.decide(match, evidence, complaint, clues)
        assert decision.outcome == "DECLINE"
        assert decision.rule_id == "ATM.NO_MATCH"
