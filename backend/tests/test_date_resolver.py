"""Tests for agent/date_resolver.py. Owner: Dev A.

received_at = 2026-09-30 10:15 (Wednesday) is the live-round date.
"""
import datetime as dt

import pytest

from backend.agent.date_resolver import resolve_date, resolve_fee_month

RECEIVED = dt.datetime(2026, 9, 30, 10, 15)  # Wednesday
RECEIVED_DATE = RECEIVED.date()


class TestExactDate:
    def test_date_exact_overrides_phrase(self):
        exact = dt.date(2026, 9, 15)
        start, end = resolve_date("last week", exact, RECEIVED)
        assert start == end == exact

    def test_date_exact_alone(self):
        exact = dt.date(2026, 9, 20)
        start, end = resolve_date(None, exact, RECEIVED)
        assert start == end == exact


class TestYesterday:
    @pytest.mark.parametrize("phrase", ["yesterday", "semalam", "ytd", "smlm"])
    def test_yesterday_variants(self, phrase):
        start, end = resolve_date(phrase, None, RECEIVED)
        assert start == end == dt.date(2026, 9, 29)

    @pytest.mark.parametrize("phrase", ["kelmarin", "kemarin"])
    def test_kelmarin_covers_yesterday_and_the_day_before(self, phrase):
        # usually "the day before yesterday", sometimes "yesterday": the window holds both
        assert resolve_date(phrase, None, RECEIVED) == (dt.date(2026, 9, 28), dt.date(2026, 9, 29))


class TestToday:
    @pytest.mark.parametrize("phrase", ["today", "hari ini", "tadi"])
    def test_today_variants(self, phrase):
        start, end = resolve_date(phrase, None, RECEIVED)
        assert start == end == RECEIVED_DATE


class TestLastWeek:
    @pytest.mark.parametrize("phrase", ["last week", "minggu lepas", "minggu lalu", "mgg lps", "last wk"])
    def test_last_week_is_2_to_14_days_back(self, phrase):
        # labels_train.csv: "last week" transactions are 5-12 days before received_at (66 complaints);
        # the old 1-7 day window missed 45 of them
        start, end = resolve_date(phrase, None, RECEIVED)
        assert (start, end) == (dt.date(2026, 9, 16), dt.date(2026, 9, 28))


class TestThisWeek:
    @pytest.mark.parametrize("phrase", ["this week", "minggu ini"])
    def test_this_week_starts_monday(self, phrase):
        start, end = resolve_date(phrase, None, RECEIVED)
        assert start == dt.date(2026, 9, 28)  # Monday
        assert end == RECEIVED_DATE


class TestLastDay:
    def test_last_tuesday_from_wednesday(self):
        # Sep 30 is Wed; last Tuesday = Sep 29
        start, end = resolve_date("last Tuesday", None, RECEIVED)
        assert start == end == dt.date(2026, 9, 29)

    def test_hari_selasa_lepas(self):
        start, end = resolve_date("hari Selasa lepas", None, RECEIVED)
        assert start == end == dt.date(2026, 9, 29)

    def test_last_saturday_from_wednesday(self):
        # Sep 30 is Wed; last Saturday = Sep 26
        start, end = resolve_date("last Saturday", None, RECEIVED)
        assert start == end == dt.date(2026, 9, 26)

    def test_hari_sabtu_lepas(self):
        start, end = resolve_date("hari Sabtu lepas", None, RECEIVED)
        assert start == end == dt.date(2026, 9, 26)

    def test_last_wednesday_is_previous_not_today(self):
        # Sep 30 is Wed; last Wednesday = Sep 23 (not today)
        start, end = resolve_date("last Wednesday", None, RECEIVED)
        assert start == end == dt.date(2026, 9, 23)

    def test_last_friday(self):
        # Sep 30 is Wed; last Friday = Sep 25
        start, end = resolve_date("last Friday", None, RECEIVED)
        assert start == end == dt.date(2026, 9, 25)

    def test_hari_jumaat_lepas(self):
        start, end = resolve_date("hari Jumaat lepas", None, RECEIVED)
        assert start == end == dt.date(2026, 9, 25)


class TestLastMonth:
    @pytest.mark.parametrize("phrase", ["last month", "bulan lepas", "bulan lalu"])
    def test_last_month_is_calendar_month(self, phrase):
        start, end = resolve_date(phrase, None, RECEIVED)
        assert start == dt.date(2026, 8, 1)
        assert end == dt.date(2026, 8, 31)

    def test_last_month_january_wraps_to_december(self):
        jan = dt.datetime(2026, 1, 15, 10, 0)
        start, end = resolve_date("last month", None, jan)
        assert start == dt.date(2025, 12, 1)
        assert end == dt.date(2025, 12, 31)


class TestNamedMonth:
    def test_september_from_sep_30(self):
        start, end = resolve_date("September", None, RECEIVED)
        assert start == dt.date(2026, 9, 1)
        assert end == dt.date(2026, 9, 30)

    def test_bulan_julai(self):
        # July 2026 is within 45-day window of Sep 30? Window starts Aug 16.
        # July ends Jul 31, which is before Aug 16. So falls outside window.
        # Should try 2026 first, fail window check, then... still return it
        # because it's the most recent year. Actually wait: Jul 31 < Aug 16.
        # Let me re-check: window_start = Sep 30 - 45 = Aug 16.
        # July 2026: start=Jul 1, end=Jul 31. end (Jul 31) < window_start (Aug 16). Skip.
        # July 2025: far out of window. Skip.
        # Fallback: return July of current year.
        start, end = resolve_date("bulan Julai", None, RECEIVED)
        assert start == dt.date(2026, 7, 1)
        assert end == dt.date(2026, 7, 31)

    def test_august_in_window(self):
        start, end = resolve_date("August", None, RECEIVED)
        assert start == dt.date(2026, 8, 1)
        assert end == dt.date(2026, 8, 31)

    def test_bulan_ogos(self):
        start, end = resolve_date("bulan Ogos", None, RECEIVED)
        assert start == dt.date(2026, 8, 1)
        assert end == dt.date(2026, 8, 31)

    def test_longer_month_name_matches_first(self):
        # "jun" should not match inside "june"
        start, end = resolve_date("June", None, RECEIVED)
        assert start.month == 6


class TestNDaysAgo:
    def test_2_days_ago(self):
        start, end = resolve_date("2 days ago", None, RECEIVED)
        assert start == end == dt.date(2026, 9, 28)

    def test_3_hari_lepas(self):
        start, end = resolve_date("3 hari lepas", None, RECEIVED)
        assert start == end == dt.date(2026, 9, 27)


class TestFallback:
    def test_unparseable_returns_full_window(self):
        start, end = resolve_date("some random text", None, RECEIVED)
        assert start == dt.date(2026, 8, 16)  # Sep 30 - 45
        assert end == RECEIVED_DATE

    def test_none_phrase_returns_full_window(self):
        start, end = resolve_date(None, None, RECEIVED)
        assert start == dt.date(2026, 8, 16)
        assert end == RECEIVED_DATE


class TestResolveFeeMonth:
    def test_structured_fee_month(self):
        start, end = resolve_fee_month("2026-08", None, RECEIVED)
        assert start == dt.date(2026, 8, 1)
        assert end == dt.date(2026, 8, 31)

    def test_fee_month_takes_priority_over_phrase(self):
        start, end = resolve_fee_month("2026-07", "last month", RECEIVED)
        assert start == dt.date(2026, 7, 1)
        assert end == dt.date(2026, 7, 31)

    def test_falls_back_to_phrase(self):
        start, end = resolve_fee_month(None, "bulan Ogos", RECEIVED)
        assert start == dt.date(2026, 8, 1)
        assert end == dt.date(2026, 8, 31)

    def test_falls_back_to_full_window(self):
        start, end = resolve_fee_month(None, None, RECEIVED)
        assert start == dt.date(2026, 8, 16)
        assert end == RECEIVED_DATE
