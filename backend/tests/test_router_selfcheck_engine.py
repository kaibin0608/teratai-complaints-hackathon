"""Tests for router, self_check, and engine wiring. Owner: Dev A."""
import csv
import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from backend.agent.engine import match_and_decide
from backend.agent.router import (
    compute_language,
    compute_priority,
    compute_route,
    compute_vulnerable,
    finalize_decision,
)
from backend.agent.self_check import check_reply
from backend.agent.tools import load_complaint
from backend.contracts import (
    Calculation,
    CheckResult,
    Clues,
    Complaint,
    Decision,
    EngineResult,
    Evidence,
    MatchResult,
    to_money,
)

DATA = Path(__file__).resolve().parent.parent.parent / "data"
LABELS = list(csv.DictReader(open(DATA / "labels_train.csv", encoding="utf-8")))


# === ROUTER ===

class TestComputeRoute:
    def test_investigate_goes_fraud_team(self):
        assert compute_route("INVESTIGATE", Decimal("0")) == "FRAUD_TEAM"

    def test_decline_goes_human_approval(self):
        assert compute_route("DECLINE", Decimal("0")) == "HUMAN_APPROVAL"

    def test_info_only_auto_resolve(self):
        assert compute_route("INFO_ONLY", Decimal("0")) == "AUTO_RESOLVE"

    def test_refund_500_auto_resolve(self):
        assert compute_route("REFUND", Decimal("500.00")) == "AUTO_RESOLVE"

    def test_refund_500_01_human_approval(self):
        assert compute_route("REFUND", Decimal("500.01")) == "HUMAN_APPROVAL"

    def test_refund_under_500_auto(self):
        assert compute_route("REFUND", Decimal("100.00")) == "AUTO_RESOLVE"


class TestComputePriority:
    def test_vulnerable_bumps_p2_to_p1(self):
        complaint = load_complaint("CMP-00244")
        from unittest.mock import patch
        with patch("backend.agent.router.get_customer", return_value={"date_of_birth": "1950-01-01"}):
            assert compute_priority("P2", complaint) == "P1"

    def test_young_stays_p2(self):
        complaint = load_complaint("CMP-00244")
        from unittest.mock import patch
        with patch("backend.agent.router.get_customer", return_value={"date_of_birth": "1990-01-01"}):
            assert compute_priority("P2", complaint) == "P2"

    def test_p1_stays_p1(self):
        complaint = load_complaint("CMP-00244")
        from unittest.mock import patch
        with patch("backend.agent.router.get_customer", return_value={"date_of_birth": "1950-01-01"}):
            assert compute_priority("P1", complaint) == "P1"


class TestComputeLanguage:
    def test_mixed_uses_preferred(self):
        complaint = load_complaint("CMP-00244")
        clues = Clues(category="ATM_NOT_DISPENSED", language="MS", is_mixed_language=True)
        from unittest.mock import patch
        with patch("backend.agent.router.get_customer", return_value={"preferred_language": "EN"}):
            assert compute_language(clues, complaint) == "EN"

    def test_not_mixed_uses_clue_language(self):
        complaint = load_complaint("CMP-00244")
        clues = Clues(category="ATM_NOT_DISPENSED", language="MS", is_mixed_language=False)
        from unittest.mock import patch
        with patch("backend.agent.router.get_customer", return_value={"preferred_language": "EN"}):
            assert compute_language(clues, complaint) == "MS"


# === SELF-CHECK ===

class TestSelfCheck:
    def test_valid_reply_passes(self):
        evidence = Evidence(allowed_txn_ids=["TXN-0001234"], allowed_amounts=[Decimal("500.00")])
        result = EngineResult(
            match=MatchResult(status="confident", txn_id="TXN-0001234", category="ATM_NOT_DISPENSED"),
            decision=Decision(category="ATM_NOT_DISPENSED", outcome="REFUND", refund_amount_myr=Decimal("500.00"),
                              priority="P2", reply_language="EN", route="AUTO_RESOLVE", rule_id="ATM.SHORTFALL_REFUND"),
            evidence=evidence,
        )
        check = check_reply("We have refunded RM500.00 for transaction TXN-0001234.", result)
        assert check.passed

    def test_invented_txn_fails(self):
        evidence = Evidence(allowed_txn_ids=["TXN-0001234"], allowed_amounts=[Decimal("500.00")])
        result = EngineResult(
            match=MatchResult(status="confident", txn_id="TXN-0001234", category="ATM_NOT_DISPENSED"),
            decision=Decision(category="ATM_NOT_DISPENSED", outcome="REFUND", refund_amount_myr=Decimal("500.00"),
                              priority="P2", reply_language="EN", route="AUTO_RESOLVE", rule_id="ATM.SHORTFALL_REFUND"),
            evidence=evidence,
        )
        check = check_reply("We have refunded RM500.00 for transaction TXN-9999999.", result)
        assert not check.passed
        assert any("TXN-9999999" in p for p in check.problems)

    def test_invented_amount_fails(self):
        evidence = Evidence(allowed_txn_ids=["TXN-0001234"], allowed_amounts=[Decimal("500.00")])
        result = EngineResult(
            match=MatchResult(status="confident", txn_id="TXN-0001234", category="ATM_NOT_DISPENSED"),
            decision=Decision(category="ATM_NOT_DISPENSED", outcome="REFUND", refund_amount_myr=Decimal("500.00"),
                              priority="P2", reply_language="EN", route="AUTO_RESOLVE", rule_id="ATM.SHORTFALL_REFUND"),
            evidence=evidence,
        )
        check = check_reply("We have refunded RM999.99 for transaction TXN-0001234.", result)
        assert not check.passed
        assert any("999.99" in p for p in check.problems)

    def test_no_ids_or_amounts_passes(self):
        evidence = Evidence()
        result = EngineResult(
            match=MatchResult(status="none", category="SERVICE_QUALITY"),
            decision=Decision(category="SERVICE_QUALITY", outcome="INFO_ONLY",
                              priority="P3", reply_language="EN", route="AUTO_RESOLVE", rule_id="SVC.INFO_ONLY"),
            evidence=evidence,
        )
        check = check_reply("Thank you for contacting us. We will review your feedback.", result)
        assert check.passed

    def test_comma_separated_amount(self):
        evidence = Evidence(allowed_txn_ids=["TXN-0001234"], allowed_amounts=[Decimal("1383.20")])
        result = EngineResult(
            match=MatchResult(status="confident", txn_id="TXN-0001234", category="ATM_NOT_DISPENSED"),
            decision=Decision(category="ATM_NOT_DISPENSED", outcome="REFUND", refund_amount_myr=Decimal("1383.20"),
                              priority="P2", reply_language="EN", route="AUTO_RESOLVE", rule_id="ATM.SHORTFALL_REFUND"),
            evidence=evidence,
        )
        check = check_reply("Refunded RM1,383.20 for TXN-0001234.", result)
        assert check.passed


# === ENGINE WIRING ===

class TestEngineWiring:
    def test_service_quality_returns_info_only(self):
        complaint = load_complaint("CMP-00002")
        clues = Clues(category="SERVICE_QUALITY", language="EN")
        result = match_and_decide(complaint, clues)
        assert result.decision.outcome == "INFO_ONLY"
        assert result.decision.category == "SERVICE_QUALITY"

    def test_engine_against_sample_labels(self):
        """Run engine on 5 labels per category to verify wiring."""
        from backend.agent.stubs import fake_extract
        import asyncio

        categories = ["ATM_NOT_DISPENSED", "UNAUTHORISED_CARD", "SCAM_TRANSFER",
                       "FAILED_TRANSFER", "DUPLICATE_CHARGE", "FEE_DISPUTE", "SERVICE_QUALITY"]
        for cat in categories:
            cat_labels = [l for l in LABELS if l["category"] == cat][:5]
            for label in cat_labels:
                complaint = load_complaint(label["complaint_id"])
                clues, _ = asyncio.run(fake_extract(complaint))
                clues = clues.model_copy(update={"category": cat})
                result = match_and_decide(complaint, clues)
                assert result.decision is not None, f"{label['complaint_id']} returned no decision"
                assert result.decision.priority in ("P1", "P2", "P3")
                assert result.decision.route in ("AUTO_RESOLVE", "HUMAN_APPROVAL", "FRAUD_TEAM")

    def test_hold_overrides_route(self):
        """Ambiguous match should push to HUMAN_APPROVAL."""
        complaint = load_complaint("CMP-00244")
        clues = Clues(category="ATM_NOT_DISPENSED", language="EN")
        result = match_and_decide(complaint, clues)
        if result.match.status == "ambiguous":
            assert result.decision.route in ("HUMAN_APPROVAL", "FRAUD_TEAM")

    def test_fallback_match_is_decided_by_the_handler_that_found_it(self, monkeypatch):
        """The extractor says FAILED_TRANSFER, the failed-transfer handler finds nothing, the scam handler
        finds the transfer: the scam handler decides, and a person confirms the revised category."""
        from backend.agent.categories.registry import get_handler
        from backend.contracts import MatchResult

        failed = get_handler("FAILED_TRANSFER")
        monkeypatch.setattr(failed, "match", lambda complaint, clues: (
            MatchResult(status="none", category="FAILED_TRANSFER"), Evidence()))
        complaint = load_complaint("CMP-00005")  # scam: RM8,085.08 to Iskandar bin Omar, labelled TXN-0120065
        clues = Clues(category="FAILED_TRANSFER", language="MS", amount_mentioned=Decimal("8085.08"),
                      counterparty_name="Iskandar bin Omar", date_phrase="semalam")
        result = match_and_decide(complaint, clues)
        assert result.match.category == "SCAM_TRANSFER"
        assert result.decision.category == "SCAM_TRANSFER"
        assert result.decision.matched_txn_id == "TXN-0120065"
        assert result.decision.outcome == "INVESTIGATE" and result.decision.refund_amount_myr == 0
        assert result.decision.route == "FRAUD_TEAM"
        assert result.decision.hold_reason == "category_revised"
