"""Resolve date phrases from complaint text to (start_date, end_date) ranges. Owner: Dev A.

Anchored to received_at. FEE_DISPUTE uses calendar months per complaint_policy.csv.
"""
from __future__ import annotations

import calendar
import datetime as dt
import re

MALAY_DAYS: dict[str, int] = {
    "isnin": 0, "selasa": 1, "rabu": 2, "khamis": 3,
    "jumaat": 4, "sabtu": 5, "ahad": 6,
}
ENGLISH_DAYS: dict[str, int] = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
ALL_DAYS = {**MALAY_DAYS, **ENGLISH_DAYS}

MALAY_MONTHS: dict[str, int] = {
    "januari": 1, "februari": 2, "mac": 3, "april": 4,
    "mei": 5, "jun": 6, "julai": 7, "ogos": 8,
    "september": 9, "oktober": 10, "november": 11, "disember": 12,
}
ENGLISH_MONTHS: dict[str, int] = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
ALL_MONTHS = {**MALAY_MONTHS, **ENGLISH_MONTHS}

YESTERDAY = {"yesterday", "ytd", "semalam", "smlm", "semlm"}
KELMARIN = {"kelmarin", "kemarin"}  # usually the day before yesterday, sometimes yesterday: cover both
# "last week": in the data the transaction is 5-12 days before received_at; 2-14 covers that and the calendar reading
LAST_WEEK = {"last week", "last wk", "minggu lepas", "minggu lalu", "minggu lps", "mgg lepas", "mgg lps"}
LAST_WEEK_DAYS = (2, 14)
LAST_MONTH = {"last month", "bulan lepas", "bulan lalu"}
TODAY = {"today", "hari ini", "tadi"}
THIS_WEEK = {"this week", "minggu ini"}

_N_DAYS_AGO = re.compile(r"(\d+)\s*(?:days?|hari)\s*(?:ago|lepas|lalu)")


def _most_recent_weekday(before: dt.date, weekday: int) -> dt.date:
    """Most recent occurrence of weekday (0=Mon) strictly before `before`."""
    days_back = (before.weekday() - weekday) % 7
    if days_back == 0:
        days_back = 7
    return before - dt.timedelta(days=days_back)


def _calendar_month(year: int, month: int) -> tuple[dt.date, dt.date]:
    _, last_day = calendar.monthrange(year, month)
    return dt.date(year, month, 1), dt.date(year, month, last_day)


def _prev_calendar_month(ref: dt.date) -> tuple[dt.date, dt.date]:
    if ref.month == 1:
        return _calendar_month(ref.year - 1, 12)
    return _calendar_month(ref.year, ref.month - 1)


def resolve_date(
    date_phrase: str | None,
    date_exact: dt.date | None,
    received_at: dt.datetime,
    match_window_days: int = 45,
) -> tuple[dt.date, dt.date]:
    """Return (start_date, end_date) inclusive range for transaction search.

    Falls back to the full match window if the phrase is unparseable.
    """
    received_date = received_at.date()
    window_start = received_date - dt.timedelta(days=match_window_days)
    full_window = (window_start, received_date)

    if date_exact is not None:
        return (date_exact, date_exact)

    if not date_phrase:
        return full_window

    phrase = date_phrase.strip().lower()

    if phrase in TODAY:
        return (received_date, received_date)

    if phrase in YESTERDAY:
        day = received_date - dt.timedelta(days=1)
        return (day, day)

    if phrase in KELMARIN:
        return (received_date - dt.timedelta(days=2), received_date - dt.timedelta(days=1))

    if phrase in THIS_WEEK:
        start = received_date - dt.timedelta(days=received_date.weekday())
        return (start, received_date)

    if phrase in LAST_WEEK:
        nearest, furthest = LAST_WEEK_DAYS
        return (received_date - dt.timedelta(days=furthest), received_date - dt.timedelta(days=nearest))

    if phrase in LAST_MONTH:
        return _prev_calendar_month(received_date)

    # "N days ago" / "N hari lepas"
    m = _N_DAYS_AGO.match(phrase)
    if m:
        day = received_date - dt.timedelta(days=int(m.group(1)))
        return (day, day)

    # "last <day>" / "hari <day> lepas" — find the weekday name anywhere in phrase
    for day_name, weekday in ALL_DAYS.items():
        if day_name in phrase:
            target = _most_recent_weekday(received_date, weekday)
            return (target, target)

    # Named month: "July", "bulan Julai", "September", etc.
    for month_name, month_num in sorted(ALL_MONTHS.items(), key=lambda x: -len(x[0])):
        if month_name in phrase:
            for year in (received_date.year, received_date.year - 1):
                start, end = _calendar_month(year, month_num)
                if end >= window_start and start <= received_date:
                    return (start, end)
            return _calendar_month(received_date.year, month_num)

    return full_window


def resolve_fee_month(
    fee_month: str | None,
    date_phrase: str | None,
    received_at: dt.datetime,
    match_window_days: int = 45,
) -> tuple[dt.date, dt.date]:
    """Resolve the month for FEE_DISPUTE matching.

    fee_month is "YYYY-MM" from LLM extraction (structured).
    Falls back to date_phrase resolution if fee_month is absent.
    """
    if fee_month:
        year, month = int(fee_month[:4]), int(fee_month[5:7])
        return _calendar_month(year, month)
    return resolve_date(date_phrase, None, received_at, match_window_days)
