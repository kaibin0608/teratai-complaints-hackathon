"""Build the fixed second-issue evaluation set. Owner: Dev B.

Complaints that raise a second, different problem must be held for an officer, and single-issue complaints must
not be, even when they use words that belong to another category ("kena caj 2 kali", "kad ATM"). This writes a
frozen set to measure that, built from labelled training complaints (never pilot, holdout, extraction few-shots or
messy-set sources), so the main issue keeps its real label:

- two-issue: the complaint rewritten in a messy style plus ONE more, separate problem of a stated other category
- tricky single-issue: the complaint rewritten using another category's words without raising that problem
- Dev A's 6 mixed tests (PLAN.md "Complaints with two issues"): a training complaint plus his exact second-issue
  phrase; the full texts weren't kept, so they are rebuilt from the same pairs and phrases

Output (committed; never edited to suit the prompt):
    backend/eval/issues/complaints.csv   six complaint fields, IDs ISS-nnnnn
    backend/eval/issues/labels.csv       complaint_id, main_category, other_categories (;-list), kind, split, note
    backend/eval/issues/sources.csv      source complaint and the rewrite, for reading

Run once:  python -m backend.eval.make_issues
Then:      python -m backend.eval.issues_eval --split dev
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

from backend import config
from backend.agent.tools import load_complaint
from backend.llm.client import get_client
from backend.llm.prompts import load_fewshot
from backend.llm.types import ModelSpec
from starter.data import read

EVAL_DIR = Path(__file__).resolve().parent
OUT_DIR = EVAL_DIR / "issues"
FIELDS = ["complaint_id", "customer_id", "received_at", "channel", "subject", "text"]
LABEL_FIELDS = ["complaint_id", "main_category", "other_categories", "kind", "split", "note"]

PROBLEM = {  # a second problem, in plain words, for the rewrite prompt
    "DUPLICATE_CHARGE": "being charged twice for the same purchase",
    "FAILED_TRANSFER": "a money transfer that failed or never reached the recipient",
    "ATM_NOT_DISPENSED": "an ATM that took the money from the account but did not give out the cash",
    "UNAUTHORISED_CARD": "a card payment the customer did not make",
    "SCAM_TRANSFER": "being tricked by a scammer into sending money",
    "FEE_DISPUTE": "an unexpected or wrong bank fee they want explained or refunded (annual fee, service charge)",
    "SERVICE_QUALITY": "poor service: rude staff, a hotline nobody answers, the app logging them out, a long queue",
}
OVERLAP = {"SCAM_TRANSFER": {"FAILED_TRANSFER", "UNAUTHORISED_CARD"}, "UNAUTHORISED_CARD": {"SCAM_TRANSFER"}}
TRICK = {  # single-issue rewrites that use another category's words without raising that problem
    "DUPLICATE_CHARGE": "use the Malay word 'caj' or the word 'charged' for the double charge (e.g. 'kena caj 2 kali')",
    "FAILED_TRANSFER": "say the transfer was made at an ATM or through the app, and that the money 'did not reach' "
                       "the recipient",
    "ATM_NOT_DISPENSED": "say they already called the hotline to report it, without complaining about the hotline",
    "UNAUTHORISED_CARD": "say the card was used twice or for two payments they did not make (one problem)",
    "SCAM_TRANSFER": "say they transferred the money and it 'cannot be recovered', and that the scammer 'tipu'",
    "FEE_DISPUTE": "call the debit card a 'kad ATM' (as Malaysians do), e.g. 'caj tahunan kad ATM'",
    "SERVICE_QUALITY": "mention a card, a fee or a transfer only as background to where the bad service happened, "
                       "without disputing any money",
}
STYLES = [
    "SMS style with short forms ('sy', 'x', 'dh', 'tq', 'pls', 'smlm'), no capitals",
    "rushed phone typing with typos and little punctuation",
    "Manglish, mixing English and Malay mid-sentence ('lah', 'leh')",
    "angry, a few words in CAPS, '!!!', one emoji",
    "polite but casual chat, a few short forms",
]
DEV_A_TESTS = [  # main category, second category, Dev A's exact second-issue phrase (PLAN.md)
    ("FAILED_TRANSFER", "FEE_DISPUTE", "pastu ada caj fee pulak"),
    ("DUPLICATE_CHARGE", "SERVICE_QUALITY", "staff kurang ajar and tak nak tolong"),
    ("ATM_NOT_DISPENSED", "SERVICE_QUALITY", "call hotline 3 kali xde org angkat"),
    ("FEE_DISPUTE", "SERVICE_QUALITY", "app korang asyik logout"),
    ("UNAUTHORISED_CARD", "ATM_NOT_DISPENSED", "atm pun tak keluar duit"),
    ("SCAM_TRANSFER", "UNAUTHORISED_CARD", "card transaction yg bukan saya buat"),
]

TWO_ISSUE = """Rewrite this bank complaint the way a real Malaysian customer types. Style: {style}.

Keep every fact of the original problem exactly (amounts, merchant or recipient, date meaning, card digits).
Then ADD ONE more, separate complaint in the same message: {problem}. Write it as a real, second thing the customer
wants the bank to deal with, in one or two short sentences. Do not give the second problem an amount, a date or a
transaction reference. The original problem stays the main one.

The text is a {channel}. Return only the new complaint text.

Original:
{text}"""
TRICKY = """Rewrite this bank complaint the way a real Malaysian customer types. Style: {style}.

Keep every fact exactly (amounts, merchant or recipient, date meaning, card digits) and keep it about ONE problem
only. While doing so, {trick}. Do not add any second complaint.

The text is a {channel}. Return only the new complaint text.

Original:
{text}"""


def eligible_sources(seed: int = 11) -> dict[str, list[dict[str, str]]]:
    excluded = {line.strip() for name in ("pilot", "holdout")
                for line in (EVAL_DIR / f"{name}_ids.txt").read_text(encoding="utf-8").splitlines()}
    excluded |= {e["complaint_id"] for e in load_fewshot()}
    messy = EVAL_DIR / "messy" / "sources.csv"
    if messy.exists():
        excluded |= {r["source_id"] for r in csv.DictReader(open(messy, encoding="utf-8"))}
    by_category: dict[str, list[dict[str, str]]] = defaultdict(list)
    for label in read("labels_train.csv"):
        if label["complaint_id"] not in excluded:
            by_category[label["category"]].append(label)
    rng = random.Random(seed)
    for rows in by_category.values():
        rng.shuffle(rows)
    return by_category


def plan(per_category_two: int, per_category_tricky: int) -> list[dict]:
    """Which source, kind and second category each row gets. Deterministic."""
    sources = eligible_sources()
    rows: list[dict] = []
    for cat in sorted(sources):
        pool = iter(sources[cat])
        seconds = [c for c in PROBLEM if c != cat and c not in OVERLAP.get(cat, set())]
        for i in range(per_category_two):
            rows.append({"kind": "two_issue", "source": next(pool), "second": seconds[i % len(seconds)]})
        for _ in range(per_category_tricky):
            rows.append({"kind": "tricky_single", "source": next(pool), "second": None})
    for cat, second, phrase in DEV_A_TESTS:
        rows.append({"kind": "dev_a", "source": sources[cat][-1], "second": second, "phrase": phrase})
    return rows


async def build(rows: list[dict], model: str) -> list[tuple[dict, dict, dict]]:
    spec, client = ModelSpec.parse(model), get_client()
    gate = asyncio.Semaphore(config.LLM_MAX_CONCURRENCY)

    async def one(i: int, row: dict):
        label, c = row["source"], load_complaint(row["source"]["complaint_id"])
        style = STYLES[i % len(STYLES)]
        if row["kind"] == "dev_a":  # Dev A's tests: the original text plus his phrase, no rewrite
            text = f"{c.text.rstrip()} {row['phrase'][0].upper()}{row['phrase'][1:]}."
        else:
            prompt = (TWO_ISSUE.format(style=style, problem=PROBLEM[row["second"]], channel=c.channel, text=c.text)
                      if row["kind"] == "two_issue" else
                      TRICKY.format(style=style, trick=TRICK[label["category"]], channel=c.channel, text=c.text))
            async with gate:
                text, _ = await client.text(spec, [{"role": "user", "content": prompt}], temperature=0.9,
                                            max_tokens=450, reasoning_effort="none")
        new_id = f"ISS-{i + 1:05d}"
        complaint = {"complaint_id": new_id, "customer_id": c.customer_id,
                     "received_at": f"{c.received_at:%Y-%m-%d %H:%M}", "channel": c.channel, "subject": c.subject,
                     "text": text.strip()}
        lab = {"complaint_id": new_id, "main_category": label["category"], "other_categories": row["second"] or "",
               "kind": row["kind"], "split": "dev" if i % 2 == 0 else "final",
               "note": row.get("phrase") or (TRICK[label["category"]] if row["kind"] == "tricky_single" else "")}
        source = {"complaint_id": new_id, "source_id": label["complaint_id"], "original": c.text,
                  "rewritten": complaint["text"]}
        return complaint, lab, source

    return await asyncio.gather(*(one(i, r) for i, r in enumerate(rows)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--two", type=int, default=4, help="two-issue rewrites per main category")
    parser.add_argument("--tricky", type=int, default=4, help="tricky single-issue rewrites per category")
    parser.add_argument("--model", default="openrouter:anthropic/claude-haiku-5.5")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    results = asyncio.run(build(plan(args.two, args.tricky), args.model))
    OUT_DIR.mkdir(exist_ok=True)
    with open(OUT_DIR / "complaints.csv", "w", newline="", encoding="utf-8") as fc, \
         open(OUT_DIR / "labels.csv", "w", newline="", encoding="utf-8") as fl, \
         open(OUT_DIR / "sources.csv", "w", newline="", encoding="utf-8") as fs:
        wc, wl, ws = (csv.DictWriter(fc, FIELDS), csv.DictWriter(fl, LABEL_FIELDS),
                      csv.DictWriter(fs, ["complaint_id", "source_id", "original", "rewritten"]))
        for w in (wc, wl, ws):
            w.writeheader()
        for complaint, label, source in results:
            wc.writerow(complaint)
            wl.writerow(label)
            ws.writerow(source)
    print(f"{len(results)} complaints written to {OUT_DIR}")


if __name__ == "__main__":
    main()
