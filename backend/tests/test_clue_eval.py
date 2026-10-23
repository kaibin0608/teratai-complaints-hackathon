"""The clue evaluator scores a perfect extraction as all correct and catches the misses that hurt matching."""
import asyncio

import pytest

from backend.agent.stubs import fake_extract
from backend.agent.tools import get_db, load_complaint
from backend.contracts import Clues
from backend.eval.clue_eval import engine_check, same_name, score_complaint
from starter.data import read

LABELS = {r["complaint_id"]: r for r in read("labels_train.csv")}


def verdicts(complaint_id, clues):
    results = score_complaint(load_complaint(complaint_id), LABELS[complaint_id], clues, get_db())
    return {r.field: r.verdict for r in results}


@pytest.mark.parametrize("got, gold, ok", [
    ("Haziq", "Haziq bin Yusof", True),
    ("gamevault", "GameVault", True),
    ("Kedai Ilmu", "Kedai Buku Ilmu Batu Pahat", True),
    ("Subang Jaya Market", "Batu Pahat Market", False),
    ("Iskandar bin Omar", "Iskandar bin Ahmad", False),
])
def test_same_name(got, gold, ok):
    assert same_name(got, gold) is ok


def test_perfect_transfer_clues_are_all_correct():
    # "DuitNow transfer of RM46.54 to Shalini a/p Nair yesterday"
    clues = Clues(category="FAILED_TRANSFER", language="EN", amount_mentioned="46.54",
                  counterparty_name="Shalini a/p Nair", date_phrase="yesterday")
    assert verdicts("CMP-00001", clues) == {
        "category": "correct", "reply_language": "correct", "amount_mentioned": "correct",
        "amount_approximate": "correct", "counterparty_name": "correct", "date_window": "correct",
    }


def test_perfect_fee_clues_on_call_centre_note():
    # "Disputes a monthly service charge of RM 2.00 for June"; staff note, so reply in preferred_language (MS)
    clues = Clues(category="FEE_DISPUTE", language="EN", amount_mentioned="2.00",
                  fee_type="Monthly service charge", fee_month="2026-06")
    assert set(verdicts("CMP-00008", clues).values()) == {"correct"}


def test_approximate_amount_without_flag():
    # "about RM1,400" for a RM1,404.18 charge: Dev A's score_amount still accepts it (within 1%), but the flag is missed
    clues = Clues(category="UNAUTHORISED_CARD", language="EN", amount_mentioned="1400", date_exact="2026-09-15")
    v = verdicts("CMP-00003", clues)
    assert (v["amount_mentioned"], v["amount_approximate"], v["date_exact"]) == ("correct", "wrong", "correct")


def test_amount_outside_matcher_tolerance_is_wrong():
    clues = Clues(category="UNAUTHORISED_CARD", language="EN", amount_mentioned="1200", amount_approximate=True)
    assert verdicts("CMP-00003", clues)["amount_mentioned"] == "wrong"  # 14.5% off: beyond the ±10% approx band


def test_wrong_date_exact_overrides_correct_phrase():
    # The resolver uses date_exact as a one-day window, so a day-off date loses the transaction
    clues = Clues(category="UNAUTHORISED_CARD", language="EN", amount_mentioned="1400", amount_approximate=True,
                  date_phrase="15 September 2026", date_exact="2026-09-14")
    assert verdicts("CMP-00003", clues)["date_window"] == "wrong"


def test_relative_month_fee_is_not_missed_without_fee_month():
    # Same complaint, but "last month" instead of "June": fee_month is not expected, date_window still checks it
    complaint = load_complaint("CMP-00008").model_copy(
        update={"text": "Customer called. Disputes a monthly service charge of RM 2.00 last month."})
    clues = Clues(category="FEE_DISPUTE", language="EN", amount_mentioned="2.00",
                  fee_type="Monthly service charge", date_phrase="last month")
    v = {r.field: r.verdict for r in score_complaint(complaint, LABELS["CMP-00008"], clues, get_db())}
    assert "fee_month" not in v and v["date_window"] == "correct"


def test_failed_extraction_counts_expected_fields_as_missed():
    v = verdicts("CMP-00001", None)
    assert v["category"] == v["amount_mentioned"] == v["counterparty_name"] == v["date_window"] == "missed"


def test_engine_check_scores_the_exported_transaction():
    complaint = load_complaint("CMP-00001")
    clues, _ = asyncio.run(fake_extract(complaint))
    row = engine_check(complaint, LABELS["CMP-00001"], clues)
    assert row.top1 and row.in_candidates and row.outcome_ok and row.refund_ok and row.status == "confident"
    failed = engine_check(complaint, LABELS["CMP-00001"], None)
    assert failed.status == "extract_error" and not failed.top1
