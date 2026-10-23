"""Tests for the code check on is_mixed_language. Owner: Dev A.

The complaint cases are real training complaints the LLM flag got wrong, with the flag the LLM gave
and the labelled reply language.
"""
import pytest

from backend.agent.language_mix import check_mixed, word_counts
from backend.agent.router import compute_language
from backend.agent.tools import load_complaint
from backend.contracts import Clues


class TestWordCounts:
    def test_formal_malay_has_no_english(self):
        en, ms = word_counts("Tuan/Puan, saya tidak faham kenapa ada caj perkhidmatan bulanan bagi bulan Jun.")
        assert en == 0 and ms > 0

    def test_loanwords_written_as_malay_are_not_english(self):
        text = "Saya sertai kerja sambilan dalam kumpulan aplikasi mesej untuk 'like' video, dan app log keluar"
        assert word_counts("aplikasi telefon asyik log keluar sendiri, kad debit, kumpulan chat") == (0, 1)
        assert word_counts(text)[0] == 1  # only "app"

    def test_greetings_and_sign_offs_ignored(self):
        assert word_counts("Hello, saya tak dapat duit. Thank you.") == (0, 3)
        assert word_counts("Assalamualaikum, terima kasih") == (0, 0)

    def test_names_places_and_acronyms_ignored(self):
        assert word_counts("ATM kat Taiping Mall rosak, Kedai Buku Ilmu caj saya") == (0, 4)

    def test_casual_mix_counts_both(self):
        en, ms = word_counts("Kenapa ada monthly service charge RM10 bulan Julai? Mohon bantu, urgent.")
        assert en == 4 and ms >= 4


class TestCheckMixed:
    def test_no_english_overrides_llm_mixed(self):
        assert check_mixed(True, "saya tidak dapat membayar bil dalam akaun saya") is False

    def test_english_and_malay_overrides_llm_not_mixed(self):
        assert check_mixed(False, "Withdraw RM 1,500.00 kat Kuantan Branch pada 8 Ogos, duit tak keluar full.") is True

    def test_plain_english_stays_not_mixed(self):
        assert check_mixed(False, "Hi, my card was charged twice at Kedai Buku. Please refund.") is False

    def test_llm_mixed_kept_when_english_present(self):
        assert check_mixed(True, "app asyik logout sendiri 3 hari dah") is True


@pytest.mark.parametrize("complaint_id, llm_language, llm_mixed, expected", [
    # formal Malay the LLM flagged as mixed -> Malay, not the customer's preferred English
    ("CMP-00064", "MS", True, "MS"),
    ("CMP-00131", "MS", True, "MS"),
    ("CMP-00227", "MS", True, "MS"),
    ("CMP-00319", "MS", True, "MS"),
    ("CMP-02125", "MS", True, "MS"),
    ("CMP-02451", "MS", True, "MS"),
    # casual Malay with English words the LLM called not mixed -> preferred language
    ("CMP-00220", "MS", False, "EN"),
    ("CMP-00524", "MS", False, "EN"),
    ("CMP-00657", "MS", False, "EN"),
    ("CMP-00986", "MS", False, "EN"),
    ("CMP-01048", "MS", False, "EN"),
    ("CMP-02085", "MS", False, "EN"),
    ("CMP-02156", "EN", False, "MS"),
    # mixed the LLM got right stays mixed ("app ... logout")
    ("CMP-00043", "MS", True, "EN"),
])
def test_training_misses_now_match_labels(complaint_id, llm_language, llm_mixed, expected):
    complaint = load_complaint(complaint_id)
    clues = Clues(category="SERVICE_QUALITY", language=llm_language, is_mixed_language=llm_mixed)
    assert compute_language(clues, complaint) == expected
