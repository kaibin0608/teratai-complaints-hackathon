"""Tests for FEE_DISPUTE and SERVICE_QUALITY handlers. Owner: Dev A."""
import asyncio
import csv
import datetime as _dt
from decimal import Decimal
from pathlib import Path

import pytest

import backend.agent.categories  # registers handlers
from backend.agent.categories.registry import get_handler
from backend.agent.tools import get_account, get_customer, get_reversal, load_complaint
from backend.contracts import Calculation, Clues, Decision, Evidence, MatchResult, to_money

DATA = Path(__file__).resolve().parent.parent.parent / "data"
LABELS = list(csv.DictReader(open(DATA / "labels_train.csv", encoding="utf-8")))
FEE_LABELS = [l for l in LABELS if l["category"] == "FEE_DISPUTE"]
SVC_LABELS = [l for l in LABELS if l["category"] == "SERVICE_QUALITY"]

fee_handler = get_handler("FEE_DISPUTE")
svc_handler = get_handler("SERVICE_QUALITY")


# === FEE_DISPUTE ===

class TestFeeDisputePolicy:
    @pytest.mark.parametrize("label", FEE_LABELS, ids=lambda l: l["complaint_id"])
    def test_outcome_and_refund(self, label):
        complaint = load_complaint(label["complaint_id"])
        gold_txn_id = label["matched_txn_id"]
        expected_outcome = label["outcome"]
        expected_refund = to_money(label["refund_amount_myr"])

        from backend.agent.tools import get_db
        txn = get_db().txns.get(gold_txn_id)
        match = MatchResult(status="confident", txn_id=gold_txn_id, category="FEE_DISPUTE")
        evidence = Evidence(
            customer=get_customer(complaint.customer_id),
            matched_txn=txn,
        )

        decision = fee_handler.decide(match, evidence, complaint, Clues(category="FEE_DISPUTE", language="EN"))
        assert decision.outcome == expected_outcome, (
            f"{label['complaint_id']}: expected {expected_outcome}, got {decision.outcome}. "
            f"desc={txn.get('description') if txn else '?'}"
        )
        assert decision.refund_amount_myr == expected_refund, (
            f"{label['complaint_id']}: expected refund {expected_refund}, got {decision.refund_amount_myr}"
        )


class TestFeeDisputeMatching:
    SAMPLE = [l["complaint_id"] for l in FEE_LABELS[:20]]
    LABEL_MAP = {l["complaint_id"]: l for l in FEE_LABELS}

    @pytest.mark.parametrize("complaint_id", SAMPLE)
    def test_match_finds_gold_txn(self, complaint_id):
        label = self.LABEL_MAP[complaint_id]
        complaint = load_complaint(complaint_id)
        from backend.agent.stubs import fake_extract
        clues, _ = asyncio.run(fake_extract(complaint))
        clues = clues.model_copy(update={"category": "FEE_DISPUTE"})
        match_result, evidence = fee_handler.match(complaint, clues)
        candidate_ids = [c.txn_id for c in match_result.candidates]
        assert label["matched_txn_id"] in candidate_ids, (
            f"{complaint_id}: gold txn {label['matched_txn_id']} not in candidates"
        )


class TestFeeDisputeBoundaries:
    def test_basic_savings_monthly_refund(self):
        """Basic Savings monthly charge should be fully refunded (amount_due=0)."""
        txn = {
            "txn_id": "TXN-FAKE", "amount": 10.0, "amount_myr": "10.00",
            "description": "Monthly service charge Jun 2026",
            "account_id": "ACC-FAKE", "txn_time": "2026-06-15 10:00:00",
            "time": _dt.datetime(2026, 6, 15, 10, 0, 0),
        }
        match = MatchResult(status="confident", txn_id="TXN-FAKE", category="FEE_DISPUTE")

        from unittest.mock import patch
        fake_acct = {"account_id": "ACC-FAKE", "product": "Basic Savings", "open_date": "2020-01-01"}
        with patch("backend.agent.categories.fee.get_account", return_value=fake_acct):
            evidence = Evidence(matched_txn=txn, customer={"date_of_birth": "1990-01-01"})
            d = fee_handler.decide(match, evidence, load_complaint("CMP-00244"),
                                   Clues(category="FEE_DISPUTE", language="EN"))
        assert d.outcome == "REFUND"
        assert d.refund_amount_myr == Decimal("10.00")

    def test_debit_annual_waived_over_60(self):
        """Debit card annual fee waived for customer 60+ on charge date."""
        txn = {
            "txn_id": "TXN-FAKE", "amount": 12.0, "amount_myr": "12.00",
            "description": "Debit card annual fee",
            "account_id": "ACC-FAKE", "txn_time": "2026-07-01 10:00:00",
            "time": _dt.datetime(2026, 7, 1, 10, 0, 0),
        }
        match = MatchResult(status="confident", txn_id="TXN-FAKE", category="FEE_DISPUTE")

        from unittest.mock import patch
        fake_acct = {"account_id": "ACC-FAKE", "product": "Savings Plus", "open_date": "2010-01-01"}
        with patch("backend.agent.categories.fee.get_account", return_value=fake_acct):
            evidence = Evidence(matched_txn=txn, customer={"date_of_birth": "1960-01-01"})
            d = fee_handler.decide(match, evidence, load_complaint("CMP-00244"),
                                   Clues(category="FEE_DISPUTE", language="EN"))
        assert d.outcome == "REFUND"
        assert d.refund_amount_myr == Decimal("12.00")

    def test_debit_annual_not_waived_under_60(self):
        """Debit card annual fee NOT waived for customer under 60."""
        txn = {
            "txn_id": "TXN-FAKE", "amount": 12.0, "amount_myr": "12.00",
            "description": "Debit card annual fee",
            "account_id": "ACC-FAKE", "txn_time": "2026-07-01 10:00:00",
            "time": _dt.datetime(2026, 7, 1, 10, 0, 0),
        }
        match = MatchResult(status="confident", txn_id="TXN-FAKE", category="FEE_DISPUTE")

        from unittest.mock import patch
        fake_acct = {"account_id": "ACC-FAKE", "product": "Savings Plus", "open_date": "2010-01-01"}
        with patch("backend.agent.categories.fee.get_account", return_value=fake_acct):
            evidence = Evidence(matched_txn=txn, customer={"date_of_birth": "1980-01-01"})
            d = fee_handler.decide(match, evidence, load_complaint("CMP-00244"),
                                   Clues(category="FEE_DISPUTE", language="EN"))
        assert d.outcome == "DECLINE"
        assert d.refund_amount_myr == Decimal("0.00")

    def test_credit_annual_waived_first_year(self):
        """Credit card annual fee waived if charge date < first anniversary."""
        txn = {
            "txn_id": "TXN-FAKE", "amount": 150.0, "amount_myr": "150.00",
            "description": "Credit card annual fee",
            "account_id": "ACC-FAKE", "txn_time": "2026-06-01 10:00:00",
            "time": _dt.datetime(2026, 6, 1, 10, 0, 0),
        }
        match = MatchResult(status="confident", txn_id="TXN-FAKE", category="FEE_DISPUTE")

        from unittest.mock import patch
        fake_acct = {"account_id": "ACC-FAKE", "product": "Credit Card Classic", "open_date": "2026-01-01"}
        with patch("backend.agent.categories.fee.get_account", return_value=fake_acct):
            evidence = Evidence(matched_txn=txn, customer={"date_of_birth": "1990-01-01"})
            d = fee_handler.decide(match, evidence, load_complaint("CMP-00244"),
                                   Clues(category="FEE_DISPUTE", language="EN"))
        assert d.outcome == "REFUND"
        assert d.refund_amount_myr == Decimal("150.00")

    def test_credit_annual_not_waived_after_first_year(self):
        """Credit card annual fee NOT waived after first anniversary."""
        txn = {
            "txn_id": "TXN-FAKE", "amount": 150.0, "amount_myr": "150.00",
            "description": "Credit card annual fee",
            "account_id": "ACC-FAKE", "txn_time": "2026-06-01 10:00:00",
            "time": _dt.datetime(2026, 6, 1, 10, 0, 0),
        }
        match = MatchResult(status="confident", txn_id="TXN-FAKE", category="FEE_DISPUTE")

        from unittest.mock import patch
        fake_acct = {"account_id": "ACC-FAKE", "product": "Credit Card Classic", "open_date": "2020-01-01"}
        with patch("backend.agent.categories.fee.get_account", return_value=fake_acct):
            evidence = Evidence(matched_txn=txn, customer={"date_of_birth": "1990-01-01"})
            d = fee_handler.decide(match, evidence, load_complaint("CMP-00244"),
                                   Clues(category="FEE_DISPUTE", language="EN"))
        assert d.outcome == "DECLINE"
        assert d.refund_amount_myr == Decimal("0.00")

    def test_no_match(self):
        match = MatchResult(status="none", txn_id=None, category="FEE_DISPUTE")
        evidence = Evidence()
        d = fee_handler.decide(match, evidence, load_complaint("CMP-00244"),
                               Clues(category="FEE_DISPUTE", language="EN"))
        assert d.outcome == "DECLINE"
        assert d.rule_id == "FEE.NO_MATCH"


# === SERVICE_QUALITY ===

class TestServiceQualityPolicy:
    @pytest.mark.parametrize("label", SVC_LABELS, ids=lambda l: l["complaint_id"])
    def test_always_info_only(self, label):
        complaint = load_complaint(label["complaint_id"])
        match = MatchResult(status="none", txn_id=None, category="SERVICE_QUALITY")
        evidence = Evidence(customer=get_customer(complaint.customer_id))

        decision = svc_handler.decide(match, evidence, complaint, Clues(category="SERVICE_QUALITY", language="EN"))
        assert decision.outcome == "INFO_ONLY", f"{label['complaint_id']}: expected INFO_ONLY"
        assert decision.refund_amount_myr == Decimal("0.00")
        assert decision.matched_txn_id is None


class TestServiceQualityMatching:
    SAMPLE = [l["complaint_id"] for l in SVC_LABELS[:10]]

    @pytest.mark.parametrize("complaint_id", SAMPLE)
    def test_match_returns_none(self, complaint_id):
        complaint = load_complaint(complaint_id)
        from backend.agent.stubs import fake_extract
        clues, _ = asyncio.run(fake_extract(complaint))
        clues = clues.model_copy(update={"category": "SERVICE_QUALITY"})
        match_result, evidence = svc_handler.match(complaint, clues)
        assert match_result.status == "none"
        assert match_result.txn_id is None


class TestServiceQualityBoundaries:
    def test_info_only_no_refund(self):
        match = MatchResult(status="none", txn_id=None, category="SERVICE_QUALITY")
        evidence = Evidence()
        complaint = load_complaint("CMP-00244")
        d = svc_handler.decide(match, evidence, complaint, Clues(category="SERVICE_QUALITY", language="EN"))
        assert d.outcome == "INFO_ONLY"
        assert d.refund_amount_myr == Decimal("0.00")
        assert d.rule_id == "SVC.INFO_ONLY"
