"""Keyword baseline: no LLM, no transaction lookup. It guesses the category from keywords, takes the most common
outcome for that category from the training labels, never refunds, and detects Malay by common words.
This is the score to beat. Writes submissions/baseline/predictions.csv for every complaint.

Usage: python starter/baseline.py
"""
import csv
from collections import Counter, defaultdict
from pathlib import Path

from data import load, read

ROOT = Path(__file__).resolve().parent.parent
KEYWORDS = [  # checked in order
    ("SCAM_TRANSFER", ["scam", "tipu", "police", "polis", "safe account", "akaun selamat", "parcel", "bungkusan", "invest", "part-time", "part time", "kerja sambilan", "emergency", "kecemasan"]),
    ("ATM_NOT_DISPENSED", ["atm"]),
    ("DUPLICATE_CHARGE", ["twice", "two times", "dua kali", "2 kali", "double"]),
    ("UNAUTHORISED_CARD", ["did not make", "not authorise", "didn't make", "bukan saya", "tidak membuat", "tak buat", "disputes a card"]),
    ("FEE_DISPUTE", ["fee", "charge", "caj", "yuran"]),
    ("FAILED_TRANSFER", ["transfer", "pindah", "duitnow", "ibg"]),
]
MALAY = {"saya", "dan", "tetapi", "tidak", "kepada", "pada", "akaun", "wang", "dengan", "untuk", "sila", "mohon", "kenapa", "telah", "sebanyak", "lepas", "semalam"}
PRIORITY = {"SCAM_TRANSFER": "P1", "UNAUTHORISED_CARD": "P1", "DUPLICATE_CHARGE": "P2", "FAILED_TRANSFER": "P2", "ATM_NOT_DISPENSED": "P2",
            "FEE_DISPUTE": "P3", "SERVICE_QUALITY": "P3"}


def classify(text):
    low = text.lower()
    for cat, words in KEYWORDS:
        if any(w in low for w in words):
            return cat
    return "SERVICE_QUALITY"


def main():
    db = load()
    common = defaultdict(Counter)
    for r in read("labels_train.csv"):
        common[r["category"]][r["outcome"]] += 1
    out = ROOT / "submissions" / "baseline"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "predictions.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["complaint_id", "category", "matched_txn_id", "outcome", "refund_amount_myr", "priority", "reply_language", "route", "reply_text"])
        for cid, c in db.complaints.items():
            cat = classify(c["subject"] + " " + c["text"])
            outcome = common[cat].most_common(1)[0][0] if common[cat] else "INFO_ONLY"
            words = set(c["text"].lower().split())
            lang = "MS" if len(words & MALAY) >= 2 else "EN"
            route = {"INVESTIGATE": "FRAUD_TEAM", "DECLINE": "HUMAN_APPROVAL"}.get(outcome, "AUTO_RESOLVE")
            w.writerow([cid, cat, "", outcome, "0.00", PRIORITY[cat], lang, route, "Thank you for contacting Teratai Bank. We are looking into your complaint."])
    print(f"wrote {out / 'predictions.csv'} ({len(db.complaints)} complaints)")


if __name__ == "__main__":
    main()
