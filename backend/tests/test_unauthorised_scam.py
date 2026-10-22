"""Tests for UNAUTHORISED_CARD and SCAM_TRANSFER handlers. Owner: Dev A."""
import asyncio
import csv
from decimal import Decimal
from pathlib import Path

import pytest

import backend.agent.categories  # registers handlers
from backend.agent.categories.registry import get_handler
from backend.agent.tools import get_customer, load_complaint
from backend.contracts import Calculation, Clues, Decision, Evidence, MatchResult, to_money

DATA = Path(__file__).resolve().parent.parent.parent / "data"
LABELS = list(csv.DictReader(open(DATA / "labels_train.csv", encoding="utf-8")))
UNAUTH_LABELS = [l for l in LABELS if l["category"] == "UNAUTHORISED_CARD"]
SCAM_LABELS = [l for l in LABELS if l["category"] == "SCAM_TRANSFER"]

unauth_handler = get_handler("UNAUTHORISED_CARD")
scam_handler = get_handler("SCAM_TRANSFER")


# === UNAUTHORISED_CARD ===

class TestUnauthorisedPolicy:
    @pytest.mark.parametrize("label", UNAUTH_LABELS, ids=lambda l: l["complaint_id"])
    def test_outcome_and_refund(self, label):
        complaint = load_complaint(label["complaint_id"])
        gold_txn_id = label["matched_txn_id"]
        expected_outcome = label["outcome"]
        expected_refund = to_money(label["refund_amount_myr"])

        from backend.agent.tools import get_db
        txn = get_db().txns.get(gold_txn_id)
        match = MatchResult(status="confident", txn_id=gold_txn_id, category="UNAUTHORISED_CARD")
        evidence = Evidence(customer=get_customer(complaint.customer_id), matched_txn=txn)

        decision = unauth_handler.decide(match, evidence, complaint, Clues(category="UNAUTHORISED_CARD", language="EN"))
        assert decision.outcome == expected_outcome, (
            f"{label['complaint_id']}: expected {expected_outcome}, got {decision.outcome}. "
            f"auth={txn.get('auth_method') if txn else '?'}"
        )
        assert decision.refund_amount_myr == expected_refund


class TestUnauthorisedMatching:
    SAMPLE = [l["complaint_id"] for l in UNAUTH_LABELS[:20]]
    LABEL_MAP = {l["complaint_id"]: l for l in UNAUTH_LABELS}

    @pytest.mark.parametrize("complaint_id", SAMPLE)
    def test_match_finds_gold_txn(self, complaint_id):
        label = self.LABEL_MAP[complaint_id]
        complaint = load_complaint(complaint_id)
        from backend.agent.stubs import fake_extract
        clues, _ = asyncio.run(fake_extract(complaint))
        clues = clues.model_copy(update={"category": "UNAUTHORISED_CARD"})
        match_result, evidence = unauth_handler.match(complaint, clues)
        candidate_ids = [c.txn_id for c in match_result.candidates]
        assert label["matched_txn_id"] in candidate_ids, (
            f"{complaint_id}: gold txn {label['matched_txn_id']} not in candidates"
        )


class TestUnauthorisedBoundaries:
    def _decide(self, auth_method, amount="500.00"):
        match = MatchResult(status="confident", txn_id="TXN-FAKE", category="UNAUTHORISED_CARD")
        txn = {"txn_id": "TXN-FAKE", "amount": float(amount), "auth_method": auth_method}
        evidence = Evidence(matched_txn=txn)
        complaint = load_complaint("CMP-00244")
        return unauth_handler.decide(match, evidence, complaint, Clues(category="UNAUTHORISED_CARD", language="EN"))

    def test_none_auth_is_refund(self):
        d = self._decide("None")
        assert d.outcome == "REFUND"
        assert d.refund_amount_myr == Decimal("500.00")

    def test_3ds_otp_is_investigate(self):
        d = self._decide("3DS-OTP")
        assert d.outcome == "INVESTIGATE"
        assert d.refund_amount_myr == Decimal("0.00")

    def test_chip_pin_is_investigate(self):
        d = self._decide("Chip+PIN")
        assert d.outcome == "INVESTIGATE"
        assert d.refund_amount_myr == Decimal("0.00")

    def test_unknown_auth_is_investigate_with_hold(self):
        d = self._decide("Contactless")
        assert d.outcome == "INVESTIGATE"
        assert d.hold_reason == "unknown_auth_method"

    def test_empty_auth_treated_as_none(self):
        d = self._decide("")
        assert d.outcome == "REFUND"

    def test_no_match_is_decline(self):
        match = MatchResult(status="none", txn_id=None, category="UNAUTHORISED_CARD")
        evidence = Evidence()
        complaint = load_complaint("CMP-00244")
        d = unauth_handler.decide(match, evidence, complaint, Clues(category="UNAUTHORISED_CARD", language="EN"))
        assert d.outcome == "DECLINE"


# === SCAM_TRANSFER ===

class TestScamPolicy:
    @pytest.mark.parametrize("label", SCAM_LABELS, ids=lambda l: l["complaint_id"])
    def test_always_investigate(self, label):
        complaint = load_complaint(label["complaint_id"])
        gold_txn_id = label["matched_txn_id"]

        from backend.agent.tools import get_db
        txn = get_db().txns.get(gold_txn_id)
        match = MatchResult(status="confident", txn_id=gold_txn_id, category="SCAM_TRANSFER")
        evidence = Evidence(customer=get_customer(complaint.customer_id), matched_txn=txn)

        decision = scam_handler.decide(match, evidence, complaint, Clues(category="SCAM_TRANSFER", language="EN"))
        assert decision.outcome == "INVESTIGATE", f"{label['complaint_id']}: expected INVESTIGATE"
        assert decision.refund_amount_myr == Decimal("0.00")


class TestScamMatching:
    SAMPLE = [l["complaint_id"] for l in SCAM_LABELS[:20]]
    LABEL_MAP = {l["complaint_id"]: l for l in SCAM_LABELS}

    @pytest.mark.parametrize("complaint_id", SAMPLE)
    def test_match_finds_gold_txn(self, complaint_id):
        label = self.LABEL_MAP[complaint_id]
        complaint = load_complaint(complaint_id)
        from backend.agent.stubs import fake_extract
        clues, _ = asyncio.run(fake_extract(complaint))
        clues = clues.model_copy(update={"category": "SCAM_TRANSFER"})
        match_result, evidence = scam_handler.match(complaint, clues)
        candidate_ids = [c.txn_id for c in match_result.candidates]
        assert label["matched_txn_id"] in candidate_ids, (
            f"{complaint_id}: gold txn {label['matched_txn_id']} not in candidates"
        )


class TestScamBoundaries:
    def test_always_investigate_even_with_match(self):
        match = MatchResult(status="confident", txn_id="TXN-FAKE", category="SCAM_TRANSFER")
        txn = {"txn_id": "TXN-FAKE", "amount": 10000.0}
        evidence = Evidence(matched_txn=txn)
        complaint = load_complaint("CMP-00244")
        d = scam_handler.decide(match, evidence, complaint, Clues(category="SCAM_TRANSFER", language="EN"))
        assert d.outcome == "INVESTIGATE"
        assert d.refund_amount_myr == Decimal("0.00")

    def test_investigate_even_without_match(self):
        match = MatchResult(status="none", txn_id=None, category="SCAM_TRANSFER")
        evidence = Evidence()
        complaint = load_complaint("CMP-00244")
        d = scam_handler.decide(match, evidence, complaint, Clues(category="SCAM_TRANSFER", language="EN"))
        assert d.outcome == "INVESTIGATE"
