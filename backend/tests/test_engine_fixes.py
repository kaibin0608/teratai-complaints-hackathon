"""Engine fixes found by Dev B's end-to-end runs: tied duplicate pairs, counterparty field, unknown customer."""
import pytest

from backend.agent.categories.duplicate import DuplicateChargeHandler
from backend.agent.categories.failed_transfer import FailedTransferHandler
from backend.agent.categories.scam import ScamTransferHandler
from backend.agent.engine import match_and_decide
from backend.agent.tools import load_complaint
from backend.contracts import Clues, Complaint
from starter.data import read

LABELS = {r["complaint_id"]: r for r in read("labels_train.csv")}
DUP_REFUNDS = [cid for cid, r in LABELS.items() if r["category"] == "DUPLICATE_CHARGE" and r["outcome"] == "REFUND"][:15]


@pytest.mark.parametrize("cid", DUP_REFUNDS)
def test_tied_duplicate_pair_is_confident_and_picks_the_later_charge(cid):
    complaint = load_complaint(cid)
    clues = Clues(category="DUPLICATE_CHARGE", language="EN", **_amount_clues(cid))
    match, _ = DuplicateChargeHandler().match(complaint, clues)
    assert match.status == "confident" and match.txn_id == LABELS[cid]["matched_txn_id"]


def _amount_clues(cid):
    from backend.agent.tools import get_db
    txn = get_db().txns[LABELS[cid]["matched_txn_id"]]
    return {"amount_mentioned": txn["amount_myr"], "counterparty_name": txn["merchant_or_counterparty"]}


@pytest.mark.parametrize("handler, category", [(FailedTransferHandler, "FAILED_TRANSFER"), (ScamTransferHandler, "SCAM_TRANSFER")])
def test_recipient_name_is_scored_against_the_counterparty_field(handler, category):
    cid = next(c for c, r in LABELS.items() if r["category"] == category)
    from backend.agent.tools import get_db
    txn = get_db().txns[LABELS[cid]["matched_txn_id"]]
    clues = Clues(category=category, language="EN", counterparty_name=txn["merchant_or_counterparty"])
    match, _ = handler().match(load_complaint(cid), clues)
    best = next(c for c in match.candidates if c.txn_id == txn["txn_id"])
    assert "recipient (1.00)" in best.reasons  # was scored against the memo field ("Makan", "Transfer") and never hit


def test_unknown_customer_reason_wins_over_no_match():
    complaint = Complaint(complaint_id="LIVE-1", customer_id="CUS-99999", received_at="2026-09-30 10:15",
                          channel="App chat", text="A police officer told me to move my money to a safe account.")
    decision = match_and_decide(complaint, Clues(category="SCAM_TRANSFER", language="EN")).decision
    assert (decision.hold_reason, decision.route) == ("customer_not_found", "FRAUD_TEAM")
