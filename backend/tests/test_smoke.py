"""Step 0 smoke tests: contracts validate and the stub pipeline produces a valid prediction row."""
import asyncio
import datetime as dt
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.agent.pipeline import run_pipeline
from backend.agent.router import add_business_days, hold
from backend.agent.tools import load_complaint
from backend.contracts import PREDICTION_COLUMNS, Clues, Complaint, Decision, fmt_myt


def test_refund_rounds_to_sen():
    d = Decision(category="ATM_NOT_DISPENSED", outcome="REFUND", refund_amount_myr="1,383.2",
                 priority="P2", reply_language="EN", route="HUMAN_APPROVAL", rule_id="T")
    assert d.refund_amount_myr == Decimal("1383.20")
    assert d.policy_route == "HUMAN_APPROVAL"


@pytest.mark.parametrize("received", ["2026-09-30 10:15", "30-09-2026 10:15", "30/09/2026 10:15:00"])
def test_live_round_row_parses_malaysian_and_iso_dates(received):
    c = Complaint(complaint_id="LIVE-07", customer_id="CUS-01234", received_at=received,
                  channel="App chat", subject="", text="Hi, I was charged twice...")
    assert c.received_at == dt.datetime(2026, 9, 30, 10, 15)
    assert fmt_myt(c.received_at) == "30-09-2026 10:15:00"


@pytest.mark.parametrize("text, route", [
    ("I waited two hours at the branch.", "HUMAN_APPROVAL"),
    ("A police officer told me to move my money to a safe account.", "FRAUD_TEAM"),
])
def test_unknown_customer_is_held_not_dropped(text, route):
    c = Complaint(complaint_id="LIVE-99", customer_id="CUS-99999", received_at="30-09-2026 10:15:00",
                  channel="App chat", text=text)
    run = asyncio.run(run_pipeline(c))
    assert run.error is None
    assert (run.decision.hold_reason, run.decision.route) == ("customer_not_found", route)


def test_clues_reject_unknown_fields_and_bad_formats():
    Clues(category="FEE_DISPUTE", language="MS", fee_type="Debit card annual fee", fee_month="2026-08",
          date_exact="15-09-2026", card_last4="1882")
    with pytest.raises(ValidationError):
        Clues(category="FEE_DISPUTE", language="EN", merchant_name="GoRide")
    with pytest.raises(ValidationError):
        Clues(category="FEE_DISPUTE", language="EN", fee_month="August")


def test_hold_only_pushes_toward_humans():
    auto = Decision(category="ATM_NOT_DISPENSED", outcome="REFUND", refund_amount_myr="50", priority="P2",
                    reply_language="EN", route="AUTO_RESOLVE", rule_id="T")
    fraud = auto.model_copy(update={"outcome": "INVESTIGATE", "route": "FRAUD_TEAM", "policy_route": "FRAUD_TEAM"})
    held = hold(auto, "ambiguous_match")
    assert (held.route, held.policy_route) == ("HUMAN_APPROVAL", "AUTO_RESOLVE")
    assert hold(fraud, "ambiguous_match").route == "FRAUD_TEAM"


def test_business_days_skip_weekend():
    friday = dt.datetime(2026, 9, 25, 9, 0)
    assert add_business_days(friday, 1) == dt.datetime(2026, 9, 28, 9, 0)


@pytest.mark.parametrize("complaint_id", ["CMP-00001", "CMP-00002", "CMP-00244"])
def test_stub_pipeline_produces_prediction_row(complaint_id):
    run = asyncio.run(run_pipeline(load_complaint(complaint_id)))
    assert run.error is None and run.self_check.passed
    assert run.decision.ack_due_at > load_complaint(complaint_id).received_at
    row = run.prediction_row()
    assert list(row) == PREDICTION_COLUMNS
    assert row["refund_amount_myr"] == "0.00"
