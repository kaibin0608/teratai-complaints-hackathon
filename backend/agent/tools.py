"""Lookup tools over the hackathon CSVs. Owner: Dev A.

All data access goes through these functions. Handlers never touch get_db() directly.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from functools import lru_cache
from typing import Any

from backend.contracts import Complaint, to_money
from starter import data as starter_data


@lru_cache(maxsize=1)
def get_db():
    """Load all CSVs once per process (see starter/data.py for the structure)."""
    return starter_data.load()


def load_complaint(complaint_id: str) -> Complaint:
    return Complaint(**get_db().complaints[complaint_id])


CHANNEL_FAMILIES: dict[str, list[str]] = {
    "card": ["Card POS", "Card e-Commerce"],
    "transfer": ["DuitNow Transfer", "IBG Transfer"],
    "atm": ["ATM Withdrawal"],
    "fee": ["Fee"],
}

CATEGORY_CHANNEL_FAMILY: dict[str, str] = {
    "DUPLICATE_CHARGE": "card",
    "FAILED_TRANSFER": "transfer",
    "ATM_NOT_DISPENSED": "atm",
    "UNAUTHORISED_CARD": "card",
    "SCAM_TRANSFER": "transfer",
    "FEE_DISPUTE": "fee",
}


def get_customer(customer_id: str) -> dict[str, Any] | None:
    return get_db().customers.get(customer_id)


def get_accounts(customer_id: str) -> list[dict[str, Any]]:
    return get_db().accounts_by_customer.get(customer_id, [])


def get_account(account_id: str) -> dict[str, Any] | None:
    return get_db().accounts.get(account_id)


def get_match_window_days() -> int:
    return int(get_db().params.get("MATCH_WINDOW_DAYS", "45"))


def get_auto_refund_limit() -> Decimal:
    return to_money(get_db().params["AUTO_REFUND_LIMIT_MYR"])


def find_transactions(
    customer_id: str,
    received_at: dt.datetime,
    *,
    channel_family: str | None = None,
    date_range: tuple[dt.date, dt.date] | None = None,
    card_last4: str | None = None,
    counterparty: str | None = None,
    exclude_reversals: bool = True,
) -> list[dict[str, Any]]:
    """Broad filter over a customer's transactions within the 45-day match window.

    Returns candidates sorted by time descending (most recent first).
    Amount matching is NOT done here — handlers score candidates by amount separately
    so we never accidentally filter out the correct transaction.
    """
    db = get_db()
    window_days = get_match_window_days()
    window_start = received_at - dt.timedelta(days=window_days)

    allowed_channels = CHANNEL_FAMILIES.get(channel_family, []) if channel_family else None

    results = []
    for t in db.txns_by_customer.get(customer_id, []):
        if t["time"] < window_start or t["time"] > received_at:
            continue
        if exclude_reversals and t["channel"] == "Reversal":
            continue
        if allowed_channels and t["channel"] not in allowed_channels:
            continue
        if date_range:
            txn_date = t["time"].date()
            if txn_date < date_range[0] or txn_date > date_range[1]:
                continue
        if card_last4 and t.get("card_last4", "") != card_last4:
            continue
        if counterparty:
            desc = t.get("description", "").lower()
            if counterparty.lower() not in desc:
                continue
        results.append(t)

    results.sort(key=lambda x: x["time"], reverse=True)
    return results


def get_txn(txn_id: str) -> dict[str, Any] | None:
    return get_db().txns.get(txn_id)


def get_reversal(txn_id: str) -> dict[str, Any] | None:
    return get_db().reversal_of.get(txn_id)


def get_atm_journal(txn_id: str) -> dict[str, Any] | None:
    return get_db().atm_journal.get(txn_id)


def get_fee_schedule_for_product(product: str) -> list[dict[str, Any]]:
    return [r for r in get_db().fee_schedule if product in r.get("product", "")]


def get_policy(category: str) -> dict[str, Any]:
    return get_db().policy[category]


def get_sla(priority: str) -> dict[str, Any]:
    return get_db().sla[priority]
