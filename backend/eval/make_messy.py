"""Build a fixed messy test set: training complaints rewritten the way real customers write. Owner: Dev B.

The hidden test sends "typos, SMS short forms, emoji, mixed English and Malay". This rewrites labelled training
complaints (never pilot, holdout or few-shot ones) in those styles while keeping every fact, so the original labels
still apply. Output (committed, so the test set is fixed):
    backend/eval/messy/complaints_messy.csv   six complaint fields, IDs MSY-nnnnn
    backend/eval/messy/labels_messy.csv       the source complaints' labels under the new IDs

Run once:   python -m backend.eval.make_messy --per-category 6
Then test:  python scoring/api_check.py http://localhost:8000 --complaints backend/eval/messy/complaints_messy.csv \
                --labels backend/eval/messy/labels_messy.csv --all --no-probes
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from backend import config
from backend.agent.tools import load_complaint
from backend.llm.client import get_client
from backend.llm.prompts import load_fewshot
from backend.llm.types import ModelSpec
from starter.data import read

OUT_DIR = Path(__file__).resolve().parent / "messy"
EVAL_DIR = Path(__file__).resolve().parent
FIELDS = ["complaint_id", "customer_id", "received_at", "channel", "subject", "text"]
STYLES = [
    "SMS style: short forms like 'x' (tak), 'dh' (dah), 'sy' (saya), 'tq', 'pls', 'u', 'ur', 'nk', 'blh', 'smlm', 'mgg lps', no capitals",
    "rushed phone typing: several typos and missing letters, almost no punctuation, run-on sentence",
    "Manglish: mix English and Malay mid-sentence, particles like 'lah', 'leh', 'meh', 'ah'",
    "angry: some words in CAPS, '!!!' and '???', one or two emoji like 😡 🙏",
    "voice-to-text: no punctuation, numbers written oddly but unambiguously (e.g. 'rm 1500' or '1,500 ringgit')",
    "polite but casual chat with emoji 🙏😢, a few short forms",
]
REWRITE = """Rewrite this bank complaint the way a real Malaysian customer would type it. Style: {style}.

Keep EVERY fact exactly: the same amount(s) (you may write them informally, e.g. "rm1500", "1.5k", "RM 1,500", but the value must stay the same), the same merchant or recipient (you may shorten or lowercase it, e.g. "foodku", "aina"), the same date meaning (keep relative dates relative: "yesterday" may become "semalam" or "ytd", but never a different day), the same card digits, the same fee type and month, the same problem. Do not add new facts, amounts or dates. Keep it roughly the same length.

The text is a {channel}. {staff_note}Return only the rewritten text, nothing else.

Original:
{text}"""
STAFF_NOTE = "It is a call-centre note written by staff: keep it as a staff note in English, but make it hurried, with abbreviations (cust, txn, acct, w/d). "


def pick_sources(per_category: int, seed: int = 7) -> list[dict[str, str]]:
    excluded = {line.strip() for name in ("pilot", "holdout")
                for line in (EVAL_DIR / f"{name}_ids.txt").read_text(encoding="utf-8").splitlines()}
    excluded |= {e["complaint_id"] for e in load_fewshot()}
    by_category: dict[str, list[dict[str, str]]] = defaultdict(list)
    for label in read("labels_train.csv"):
        if label["complaint_id"] not in excluded:
            by_category[label["category"]].append(label)
    rng = random.Random(seed)
    return [lab for cat in sorted(by_category) for lab in rng.sample(by_category[cat], per_category)]


def amounts(text: str) -> set[str]:
    """Digits of every amount, so a rewrite that changed a value is caught (1,500 / 1500 / 1.5k all → 1500)."""
    found = set()
    for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*(k)?", text.lower()):
        number, k = m.group(1).replace(",", ""), m.group(2)
        try:
            value = float(number) * (1000 if k else 1)
        except ValueError:
            continue
        if value >= 1 and not re.fullmatch(r"\d{4}", number):  # skip card digits and years
            found.add(f"{value:.2f}")
    return found


async def rewrite_all(sources: list[dict[str, str]], model: str) -> list[tuple[dict, dict, str, str]]:
    spec, client = ModelSpec.parse(model), get_client()
    gate = asyncio.Semaphore(config.LLM_MAX_CONCURRENCY)

    async def one(i: int, label: dict[str, str]):
        c = load_complaint(label["complaint_id"])
        prompt = REWRITE.format(style=STYLES[i % len(STYLES)], channel=c.channel, text=c.text,
                                staff_note=STAFF_NOTE if c.is_staff_note else "")
        async with gate:
            text, _ = await client.text(spec, [{"role": "user", "content": prompt}], temperature=0.9,
                                        max_tokens=400, reasoning_effort="none")
        new_id = f"MSY-{i + 1:05d}"
        row = {"complaint_id": new_id, "customer_id": c.customer_id, "received_at": f"{c.received_at:%Y-%m-%d %H:%M}",
               "channel": c.channel, "subject": c.subject, "text": text.strip()}
        return row, {**label, "complaint_id": new_id}, label["complaint_id"], c.text

    return await asyncio.gather(*(one(i, lab) for i, lab in enumerate(sources)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--per-category", type=int, default=6)
    parser.add_argument("--model", default="openrouter:anthropic/claude-haiku-5.5")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    results = asyncio.run(rewrite_all(pick_sources(args.per_category), args.model))
    OUT_DIR.mkdir(exist_ok=True)
    label_cols = list(read("labels_train.csv")[0])
    with open(OUT_DIR / "complaints_messy.csv", "w", newline="", encoding="utf-8") as fc, \
         open(OUT_DIR / "labels_messy.csv", "w", newline="", encoding="utf-8") as fl, \
         open(OUT_DIR / "sources.csv", "w", newline="", encoding="utf-8") as fs:
        wc, wl, ws = (csv.DictWriter(fc, FIELDS), csv.DictWriter(fl, label_cols),
                      csv.DictWriter(fs, ["complaint_id", "source_id", "amounts_kept", "original", "messy"]))
        for w in (wc, wl, ws):
            w.writeheader()
        for row, label, source_id, original in results:
            wc.writerow(row)
            wl.writerow(label)
            ws.writerow({"complaint_id": row["complaint_id"], "source_id": source_id,
                         "amounts_kept": amounts(original) <= amounts(row["text"]),
                         "original": original, "messy": row["text"]})
    print(f"{len(results)} messy complaints written to {OUT_DIR}")


if __name__ == "__main__":
    main()
