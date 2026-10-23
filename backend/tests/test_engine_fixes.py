"""Regression tests for engine fixes: tied duplicate pairs, counterparty field, unknown customer, fee-type words,
keyword-fallback words. Each test fails if its fix is undone."""
import asyncio

import pytest

from backend.agent.categories.atm import ATMHandler
from backend.agent.categories.duplicate import DuplicateChargeHandler
from backend.agent.categories.failed_transfer import FailedTransferHandler
from backend.agent.categories.scam import ScamTransferHandler
from backend.agent.categories.unauthorised import UnauthorisedCardHandler
from backend.agent.engine import match_and_decide
from backend.agent.stubs import fake_extract
from backend.agent.tools import get_db, load_complaint
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
    txn = get_db().txns[LABELS[cid]["matched_txn_id"]]
    return {"amount_mentioned": txn["amount_myr"], "counterparty_name": txn["merchant_or_counterparty"]}


@pytest.mark.parametrize("handler, category, reason", [
    (FailedTransferHandler, "FAILED_TRANSFER", "recipient (1.00)"),
    (ScamTransferHandler, "SCAM_TRANSFER", "recipient (1.00)"),
    (UnauthorisedCardHandler, "UNAUTHORISED_CARD", "merchant (1.00)"),  # card description is empty
    (ATMHandler, "ATM_NOT_DISPENSED", "location match (1.00)"),  # description is the terminal ID ("ATM-SUB-05")
])
def test_recipient_name_is_scored_against_the_counterparty_field(handler, category, reason):
    cid = next(c for c, r in LABELS.items() if r["category"] == category)
    txn = get_db().txns[LABELS[cid]["matched_txn_id"]]
    clues = Clues(category=category, language="EN", counterparty_name=txn["merchant_or_counterparty"])
    match, _ = handler().match(load_complaint(cid), clues)
    best = next(c for c in match.candidates if c.txn_id == txn["txn_id"])
    assert reason in best.reasons  # was scored against the memo field ("Makan", "Transfer") and never hit


def test_debit_card_fee_does_not_match_credit_card_fee():
    # CMP-00010: "debit card annual fee"; "card" and "annual" alone used to match the credit card annual fee too
    result = match_and_decide(load_complaint("CMP-00010"), Clues(category="FEE_DISPUTE", language="EN",
                                                                 fee_type="Debit card annual fee"))
    assert (result.match.status, result.match.txn_id) == ("confident", "TXN-0104872")
    credit = next(c for c in result.match.candidates if c.txn_id == "TXN-0119443")  # Credit card annual fee
    assert "fee type match" not in credit.reasons


@pytest.mark.parametrize("text, category", [
    ("Mesin tak keluar duit tetapi akaun saya ditolak RM300.", "ATM_NOT_DISPENSED"),
    ("The machine did not give me the cash but my account was debited.", "ATM_NOT_DISPENSED"),
    ("I withdrew RM200 and nothing came out.", "ATM_NOT_DISPENSED"),
    ("Saya melabur RM5,000 dalam satu skim pelaburan dan admin hilang.", "SCAM_TRANSFER"),
    ("I was deceived by someone online and want to recover the money.", "SCAM_TRANSFER"),
])
def test_keyword_fallback_catches_atm_and_scam_wording(text, category):
    # the LLM-failure fallback; without these words such complaints fell to SERVICE_QUALITY (20 critical errors)
    complaint = Complaint(complaint_id="LIVE-1", customer_id="CUS-00001", received_at="2026-09-30 10:15",
                          channel="App chat", text=text)
    clues, _ = asyncio.run(fake_extract(complaint))
    assert clues.category == category


def test_unknown_customer_reason_wins_over_no_match():
    complaint = Complaint(complaint_id="LIVE-1", customer_id="CUS-99999", received_at="2026-09-30 10:15",
                          channel="App chat", text="A police officer told me to move my money to a safe account.")
    decision = match_and_decide(complaint, Clues(category="SCAM_TRANSFER", language="EN")).decision
    assert (decision.hold_reason, decision.route) == ("customer_not_found", "FRAUD_TEAM")
