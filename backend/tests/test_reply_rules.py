"""Reply rules: empty, length, refund stated, no premature refund claim, language; combined with the evidence check."""
import asyncio
from decimal import Decimal

import pytest

from backend.agent.pipeline import run_pipeline
from backend.agent.reply_rules import check, combined_check
from backend.agent.tools import load_complaint


def result_for(cid, **decision_changes):
    run = asyncio.run(run_pipeline(load_complaint(cid)))
    from backend.contracts import EngineResult
    decision = run.decision.model_copy(update=decision_changes)
    return EngineResult(match=run.match, decision=decision, evidence=run.evidence)


AUTO_REFUND = result_for("CMP-00001")    # REFUND RM46.54, AUTO_RESOLVE, EN
PENDING = result_for("CMP-00244")        # REFUND RM550.00, HUMAN_APPROVAL, EN
EN_OK = "Dear customer, we have refunded RM46.54 to your account for the failed transfer. Thank you for your patience."


def problems(text, result):
    return check(text, result).problems


def test_good_auto_refund_passes():
    assert problems(EN_OK, AUTO_REFUND) == []


@pytest.mark.parametrize("amount", ["RM46.54", "RM 46.54", "RM46.54,"])
def test_refund_amount_formats(amount):
    assert problems(f"Dear customer, we have refunded {amount} to your account and thank you.", AUTO_REFUND) == []


def test_large_amount_with_comma():
    text = "Dear customer, a refund of RM1,383.20 will be credited to your account after review. Thank you."
    assert problems(text, result_for("CMP-00244", refund_amount_myr=Decimal("1383.20"))) == []


def test_missing_refund_amount():
    assert any("does not state the refund amount RM46.54" in p
               for p in problems("Dear customer, we have refunded the money to your account.", AUTO_REFUND))


@pytest.mark.parametrize("claim", ["has been refunded", "telah dikreditkan"])
def test_premature_claim_on_pending_refund(claim):
    text = f"Dear customer, RM550.00 {claim} to your account and we thank you for your patience."
    assert any(claim in p for p in problems(text, PENDING))


def test_will_be_credited_is_fine_when_pending():
    text = "Dear customer, a refund of RM550.00 will be credited to your account once our review is complete."
    assert problems(text, PENDING) == []


def test_wrong_language():
    ms = result_for("CMP-00001", reply_language="MS")
    assert "the reply is not in MS" in problems(EN_OK, ms)
    malay = "Yang dihormati pelanggan, kami telah membayar balik RM46.54 ke dalam akaun anda. Terima kasih."
    assert problems(malay, ms) == []


def test_empty_and_too_long():
    assert problems("   ", AUTO_REFUND) == ["the reply is empty"]
    assert any("characters" in p for p in problems(EN_OK + " the" * 400, AUTO_REFUND))


def test_combined_lists_evidence_and_rule_problems():
    text = "Dear customer, we have refunded the money and added RM600.00 for you. Thank you."
    result = combined_check(text, AUTO_REFUND)
    assert not result.passed
    assert any("RM600" in p for p in result.problems)                     # Dev A's evidence check
    assert any("does not state the refund amount" in p for p in result.problems)  # our rule
