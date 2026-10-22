"""Step 0 smoke tests: contracts validate and the stub pipeline produces a valid prediction row."""
from decimal import Decimal

import pytest

from backend.agent.pipeline import run_pipeline
from backend.agent.router import hold
from backend.agent.tools import load_complaint
from backend.contracts import PREDICTION_COLUMNS, Complaint, Decision


def test_refund_rounds_to_sen():
    d = Decision(category="ATM_NOT_DISPENSED", outcome="REFUND", refund_amount_myr="1,383.2",
                 priority="P2", reply_language="EN", route="HUMAN_APPROVAL", rule_id="T")
    assert d.refund_amount_myr == Decimal("1383.20")


def test_live_round_row_parses():
    c = Complaint(complaint_id="LIVE-07", customer_id="CUS-01234", received_at="2026-09-30 10:15",
                  channel="App chat", subject="", text="Hi, I was charged twice...")
    assert c.received_at.day == 30 and not c.is_staff_note


def test_hold_only_pushes_toward_humans():
    auto = Decision(category="ATM_NOT_DISPENSED", outcome="REFUND", refund_amount_myr="50", priority="P2",
                    reply_language="EN", route="AUTO_RESOLVE", rule_id="T")
    fraud = auto.model_copy(update={"outcome": "INVESTIGATE", "route": "FRAUD_TEAM"})
    assert hold(auto, "ambiguous_match").route == "HUMAN_APPROVAL"
    assert hold(fraud, "ambiguous_match").route == "FRAUD_TEAM"


@pytest.mark.parametrize("complaint_id", ["CMP-00001", "CMP-00002", "CMP-00244"])
def test_stub_pipeline_produces_prediction_row(complaint_id):
    run = run_pipeline(load_complaint(complaint_id))
    assert run.error is None and run.self_check.passed
    row = run.prediction_row()
    assert list(row) == PREDICTION_COLUMNS
    assert row["refund_amount_myr"] == "0.00"
