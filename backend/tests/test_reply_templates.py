"""Code-written replies: right wording per purpose, both languages, and they pass the combined self-check."""
import asyncio

import pytest

from backend.agent.pipeline import run_pipeline
from backend.agent.reply_facts import build_facts, money
from backend.agent.reply_rules import combined_check
from backend.agent.reply_templates import render
from backend.agent.tools import load_complaint
from backend.batch.runner import select_ids
from backend.contracts import Complaint, EngineResult


def result_for(complaint):
    run = asyncio.run(run_pipeline(complaint))
    return EngineResult(match=run.match, decision=run.decision, evidence=run.evidence)


def reply_for(cid):
    result = result_for(load_complaint(cid))
    return render(result), result


def test_money_format():
    from decimal import Decimal
    assert money(Decimal("1383.2")) == "RM1,383.20" and money(Decimal("46.54")) == "RM46.54"


def test_auto_refund_says_refunded_with_amount_and_reference():
    text, result = reply_for("CMP-00001")
    assert "We have refunded RM46.54" in text and "TXN-0145614 on 22-09-2026 (RM46.54)" in text
    assert "update you by" not in text  # auto-resolved: no date promised
    assert combined_check(text, result).passed


def test_pending_refund_will_be_credited_with_next_update():
    text, result = reply_for("CMP-00244")
    assert "RM550.00 will be credited" in text and "has been refunded" not in text
    assert f"We will update you by {build_facts(result).next_update}" in text
    assert combined_check(text, result).passed


def test_decline_gives_reason():
    text, result = reply_for("CMP-00008")  # fee correct; reply language MS (call-centre note)
    assert result.decision.outcome == "DECLINE" and "tidak dapat membuat bayaran balik" in text
    assert combined_check(text, result).passed


def test_scam_holding_reply_with_advice():
    text, result = reply_for("CMP-00005")
    facts = build_facts(result)
    assert "pasukan penipuan" in text or "fraud team" in text
    assert all(line in text for line in facts.advice) and facts.next_update in text
    assert "bayaran balik sebanyak" not in text and combined_check(text, result).passed


def test_service_reply_has_no_transaction():
    text, result = reply_for("CMP-00002")
    assert "TXN-" not in text and combined_check(text, result).passed


def test_greeting_uses_name_or_generic():
    text, result = reply_for("CMP-00001")
    assert text.startswith(f"Dear {result.evidence.customer['full_name']},")
    unknown = Complaint(complaint_id="LIVE-1", customer_id="CUS-99999", received_at="2026-09-30 10:15",
                        channel="App chat", text="I waited two hours at the branch.")
    unknown_result = result_for(unknown)
    assert render(unknown_result).startswith("Dear Customer,")
    assert combined_check(render(unknown_result), unknown_result).passed


@pytest.mark.parametrize("cid", select_ids("pilot"))
def test_every_pilot_decision_passes(cid):
    text, result = reply_for(cid)
    check = combined_check(text, result)
    assert check.passed, check.problems
