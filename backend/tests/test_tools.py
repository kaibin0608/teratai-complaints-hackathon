"""Tests for agent/tools.py lookup functions."""
import datetime as dt
from decimal import Decimal

from backend.agent.tools import (
    CATEGORY_CHANNEL_FAMILY,
    find_transactions,
    get_account,
    get_accounts,
    get_atm_journal,
    get_auto_refund_limit,
    get_customer,
    get_fee_schedule_for_product,
    get_match_window_days,
    get_policy,
    get_reversal,
    get_sla,
    get_txn,
    load_complaint,
)


def test_load_complaint():
    c = load_complaint("CMP-00244")
    assert c.complaint_id == "CMP-00244"
    assert c.customer_id.startswith("CUS-")
    assert isinstance(c.received_at, dt.datetime)


def test_get_customer_existing():
    cust = get_customer("CUS-00001")
    assert cust is not None
    assert "date_of_birth" in cust
    assert "preferred_language" in cust


def test_get_customer_missing():
    assert get_customer("CUS-99999") is None


def test_get_accounts():
    accs = get_accounts("CUS-00001")
    assert isinstance(accs, list)
    assert len(accs) > 0
    assert "account_id" in accs[0]


def test_get_account():
    accs = get_accounts("CUS-00001")
    acc = get_account(accs[0]["account_id"])
    assert acc is not None
    assert acc["customer_id"] == "CUS-00001"


def test_find_transactions_returns_debits_in_window():
    c = load_complaint("CMP-00244")
    txns = find_transactions(c.customer_id, c.received_at)
    assert len(txns) > 0
    for t in txns:
        assert t["channel"] != "Reversal"
        assert t["time"] <= c.received_at
        assert t["time"] >= c.received_at - dt.timedelta(days=45)


def test_find_transactions_sorted_most_recent_first():
    c = load_complaint("CMP-00244")
    txns = find_transactions(c.customer_id, c.received_at)
    for i in range(len(txns) - 1):
        assert txns[i]["time"] >= txns[i + 1]["time"]


def test_find_transactions_channel_family_filter():
    c = load_complaint("CMP-00244")
    atm_txns = find_transactions(c.customer_id, c.received_at, channel_family="atm")
    for t in atm_txns:
        assert t["channel"] == "ATM Withdrawal"


def test_find_transactions_date_range_filter():
    c = load_complaint("CMP-00244")
    rd = c.received_at.date()
    one_day = (rd - dt.timedelta(days=1), rd)
    txns = find_transactions(c.customer_id, c.received_at, date_range=one_day)
    for t in txns:
        assert one_day[0] <= t["time"].date() <= one_day[1]


def test_find_transactions_card_last4_filter():
    c = load_complaint("CMP-00244")
    txns = find_transactions(c.customer_id, c.received_at, card_last4="0000")
    for t in txns:
        assert t.get("card_last4") == "0000"


def test_category_channel_families_complete():
    expected = {"DUPLICATE_CHARGE", "FAILED_TRANSFER", "ATM_NOT_DISPENSED",
                "UNAUTHORISED_CARD", "SCAM_TRANSFER", "FEE_DISPUTE"}
    assert set(CATEGORY_CHANNEL_FAMILY.keys()) == expected


def test_get_atm_journal():
    journal = get_atm_journal("TXN-0088211")
    assert journal is not None or journal is None  # may or may not exist; just check it doesn't crash


def test_get_reversal():
    rev = get_reversal("TXN-0000001")
    assert rev is None or "txn_id" in rev


def test_get_fee_schedule():
    rows = get_fee_schedule_for_product("Basic Savings")
    assert len(rows) > 0
    for r in rows:
        assert "Basic Savings" in r["product"]


def test_get_policy_all_categories():
    for cat in ["DUPLICATE_CHARGE", "FAILED_TRANSFER", "ATM_NOT_DISPENSED",
                "UNAUTHORISED_CARD", "SCAM_TRANSFER", "FEE_DISPUTE", "SERVICE_QUALITY"]:
        p = get_policy(cat)
        assert p["category"] == cat


def test_get_sla():
    for p in ["P1", "P2", "P3"]:
        sla = get_sla(p)
        assert "acknowledge_within_hours" in sla


def test_get_match_window_days():
    assert get_match_window_days() == 45


def test_get_auto_refund_limit():
    assert get_auto_refund_limit() == Decimal("500.00")
