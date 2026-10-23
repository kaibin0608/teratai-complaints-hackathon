"""Score extracted Clues field by field against training labels and each label's matched transaction.

The extractor can be measured before the matcher exists: the labelled transaction says what the amount,
counterparty, card, date, fee type and month should have been. A field is only expected when the complaint
text actually contains it, so a correct None is not penalised.

Verdicts: correct, wrong (a value that does not fit the gold), missed (None although the text has it).
A failed extraction counts every expected field as missed.

date_window runs Dev A's resolver on the extracted date clues and checks the labelled transaction falls inside the
window, which is what the matcher actually uses. --engine also runs match_and_decide and reports how often the
labelled transaction ends up on top, with no drafting.

Usage:
    python -m backend.eval.clue_eval                                   # fake_extract on the pilot
    python -m backend.eval.clue_eval --ids holdout --details clue_details.csv
    python -m backend.eval.clue_eval --extractor backend.agent.parser:extract --ids all --engine
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import importlib
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, get_args

from backend import config
from backend.agent.categories.base import CategoryHandler
from backend.agent.date_resolver import ALL_MONTHS, resolve_date, resolve_fee_month
from backend.agent.router import compute_language
from backend.agent.tools import get_db, get_match_window_days, load_complaint
from backend.contracts import Clues, Complaint, Extractor, FeeType, LLMUsage, to_money
from starter.data import read

EVAL_DIR = Path(__file__).resolve().parent
OWN_BANK = "Teratai Bank"
FEE_TYPES = get_args(FeeType)
NAME_CATEGORIES = {"DUPLICATE_CHARGE", "UNAUTHORISED_CARD", "FAILED_TRANSFER", "SCAM_TRANSFER", "ATM_NOT_DISPENSED"}
GENERIC_WORDS = {"bin", "binti", "a/p", "a/l", "the", "sdn", "bhd", "bank", "market", "mall", "store", "shop", "online"}
AMOUNT_RE = re.compile(r"RM\s?([\d,]+(?:\.\d+)?)", re.IGNORECASE)
LAST4_RE = re.compile(r"(?<!\d)\d{4}(?!\d)")
MONTHS = r"jan|feb|mac|mar|apr|mei|may|jun|jul|ogo|aug|sep|okt|oct|nov|dis|dec"
EXPLICIT_DATE_RE = re.compile(rf"\b\d{{1,2}}(?:[/-]\d{{1,2}}[/-]\d{{2,4}}|\s+(?:{MONTHS})[a-z]*)", re.IGNORECASE)
MONTH_NAME_RE = re.compile(rf"\b(?:{'|'.join(sorted(ALL_MONTHS, key=len, reverse=True))})\b", re.IGNORECASE)
FIELDS = ["category", "reply_language", "amount_mentioned", "amount_approximate", "counterparty_name",
          "counterparty_bank", "atm_location", "card_last4", "date_exact", "date_window", "fee_type", "fee_month"]

Verdict = Literal["correct", "wrong", "missed"]


@dataclass
class FieldResult:
    complaint_id: str
    field: str
    verdict: Verdict
    got: Any
    gold: Any


class _NoClues:
    """Stands in for a failed extraction: every field reads as None."""

    def __getattr__(self, name: str) -> None:
        return None


def name_tokens(name: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9/]+", name.lower()) if len(w) >= 3 and w not in GENERIC_WORDS}


def same_name(got: str, gold: str) -> bool:
    """Substring either way ("Haziq" / "Haziq bin Yusof"), or most of the extracted words appear in the gold."""
    g, t = got.lower().strip(), gold.lower().strip()
    if g and (g in t or t in g):
        return True
    words = name_tokens(got)
    return bool(words) and 2 * len(words & name_tokens(gold)) > len(words)


def amount_close(got: Decimal, gold: Decimal, approximate: bool) -> bool:
    """Would Dev A's matcher accept this amount for the gold transaction at all?"""
    return CategoryHandler.score_amount(float(gold), got, approximate) > 0


def reply_language(complaint: Complaint, clues: Any) -> str | None:
    """Dev A's reply-language rule, applied to the extracted language."""
    return None if clues.language is None else compute_language(clues, complaint)


def date_window(complaint: Complaint, clues: Any, category: str) -> tuple[Any, Any]:
    """The search window Dev A's handlers would use for these clues."""
    if category == "FEE_DISPUTE":
        return resolve_fee_month(clues.fee_month, clues.date_phrase, complaint.received_at)
    return resolve_date(clues.date_phrase, clues.date_exact, complaint.received_at, get_match_window_days())


def score_complaint(complaint: Complaint, label: dict[str, str], clues: Clues | None, db: Any) -> list[FieldResult]:
    c = clues or _NoClues()
    text = f"{complaint.subject} {complaint.text}"
    category = label["category"]
    checks: list[tuple[str, bool, Any, Any, bool]] = [  # (field, expected, got, gold, ok)
        ("category", True, c.category, category, c.category == category),
    ]
    language = reply_language(complaint, c)
    checks.append(("reply_language", True, language, label["reply_language"], language == label["reply_language"]))

    txn = db.txns.get(label["matched_txn_id"])
    if txn:
        stated = [to_money(a) for a in AMOUNT_RE.findall(text)]
        amount = to_money(txn["amount_myr"])
        got = c.amount_mentioned
        checks.append(("amount_mentioned", bool(stated), got, amount,
                       got is not None and amount_close(got, amount, bool(c.amount_approximate))))
        if stated:  # the flag must be set when the stated amount is off; setting it on an exact amount is harmless
            approximate = amount not in stated
            checks.append(("amount_approximate", True, c.amount_approximate, approximate,
                           bool(c.amount_approximate) or not approximate))

        if category in NAME_CATEGORIES:
            field = "atm_location" if category == "ATM_NOT_DISPENSED" else "counterparty_name"
            gold, got = txn["merchant_or_counterparty"], getattr(c, field)
            expected = bool(name_tokens(gold) & name_tokens(text)) or gold.lower() in text.lower()
            checks.append((field, expected, got, gold, got is not None and same_name(got, gold)))

        if (bank := txn["counterparty_bank"]) and bank != OWN_BANK:  # "Dear Teratai Bank" is not a clue
            got = c.counterparty_bank
            checks.append(("counterparty_bank", bank.lower() in text.lower(), got, bank,
                           got is not None and same_name(got, bank)))

        if last4 := txn["card_last4"]:
            checks.append(("card_last4", last4 in LAST4_RE.findall(text), c.card_last4, last4, c.card_last4 == last4))

        day = txn["time"].date()
        if category != "FEE_DISPUTE":  # fees are matched by month, not day
            checks.append(("date_exact", bool(EXPLICIT_DATE_RE.search(text)), c.date_exact, day, c.date_exact == day))
        else:
            fee_type = next((f for f in FEE_TYPES if txn["description"].startswith(f)), None)
            checks.append(("fee_type", True, c.fee_type, fee_type, c.fee_type == fee_type))
            month = txn["txn_time"][:7]  # the month the customer names is the posting month
            checks.append(("fee_month", bool(MONTH_NAME_RE.search(text)), c.fee_month, month, c.fee_month == month))

        if clues is not None:  # a failed extraction has no window; it counts as missed below
            start, end = date_window(complaint, c, category)
            window = f"{start}..{end} ({(end - start).days + 1}d)"
            checks.append(("date_window", True, window, day, start <= day <= end))
        else:
            checks.append(("date_window", True, None, day, False))

    results = []
    for field, expected, got, gold, ok in checks:
        if got is None:
            if expected:
                results.append(FieldResult(complaint.complaint_id, field, "missed", None, gold))
        else:
            results.append(FieldResult(complaint.complaint_id, field, "correct" if ok else "wrong", got, gold))
    return results


def load_ids(which: str) -> list[str]:
    if which == "all":
        return [r["complaint_id"] for r in read("labels_train.csv")]
    path = EVAL_DIR / f"{which}_ids.txt" if which in ("pilot", "holdout") else Path(which)
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_extractor(spec: str) -> Extractor:
    module, _, attr = spec.partition(":")
    return getattr(importlib.import_module(module), attr)


async def run_extractor(extract: Extractor, ids: list[str], concurrency: int, progress_every: int = 0):
    """[(complaint, clues or None, usage or None, error or None)] in input order."""
    gate = asyncio.Semaphore(concurrency)
    done, cost = 0, Decimal("0")

    async def one(complaint_id: str):
        nonlocal done, cost
        complaint = load_complaint(complaint_id)
        async with gate:
            try:
                clues, usage = await extract(complaint)
                outcome = complaint, clues, usage, None
            except Exception as exc:  # reported, and scored as missed fields
                usage, outcome = None, (complaint, None, None, f"{type(exc).__name__}: {exc}")
        done += 1
        cost += usage.cost_myr if usage else 0
        if progress_every and done % progress_every == 0:
            print(f"  {done}/{len(ids)} extracted, RM{cost:.4f} so far", file=sys.stderr)
        return outcome

    return await asyncio.gather(*(one(i) for i in ids))


@dataclass
class EngineRow:
    complaint_id: str
    category: str  # gold
    status: str  # match status, or extract_error / engine_error
    got_txn: str
    gold_txn: str
    top1: bool
    in_candidates: bool
    outcome_ok: bool
    refund_ok: bool


def engine_check(complaint: Complaint, label: dict[str, str], clues: Clues | None) -> EngineRow:
    """Run Dev A's engine on the extracted clues; outcome and refund only count when the transaction is right."""
    from backend.agent.engine import match_and_decide

    gold = label["matched_txn_id"]
    row = EngineRow(complaint.complaint_id, label["category"], "extract_error", "", gold, False, False, False, False)
    if clues is None:
        return row
    try:
        result = match_and_decide(complaint, clues)
    except Exception as exc:  # engine bug: visible in the report, never hidden
        row.status, row.got_txn = "engine_error", f"{type(exc).__name__}: {exc}"
        return row
    decision = result.decision
    row.status, row.got_txn = result.match.status, decision.matched_txn_id or ""
    row.top1 = row.got_txn == gold
    row.in_candidates = row.top1 or gold in {c.txn_id for c in result.match.candidates}
    row.outcome_ok = row.top1 and decision.outcome == label["outcome"]
    row.refund_ok = row.top1 and decision.refund_amount_myr == to_money(label["refund_amount_myr"])
    return row


def engine_report(rows: list[EngineRow]) -> None:
    print(f"\nEngine on extracted clues (transaction gates outcome and refund, as in scoring.md)\n")
    print(f"{'category':<20}{'n':>5}{'top1':>8}{'in cands':>10}{'outcome':>9}{'refund':>8}   match status")
    groups: dict[str, list[EngineRow]] = defaultdict(list)
    for r in rows:
        groups[r.category].append(r)
    for category, group in [*sorted(groups.items()), ("ALL", rows)]:
        n = len(group)
        rate = lambda attr: sum(getattr(r, attr) for r in group) / n  # noqa: E731
        statuses = ", ".join(f"{s} {k}" for s, k in Counter(r.status for r in group).most_common())
        print(f"{category:<20}{n:>5}{rate('top1'):>8.1%}{rate('in_candidates'):>10.1%}{rate('outcome_ok'):>9.1%}"
              f"{rate('refund_ok'):>8.1%}   {statuses}")


def report(results: list[FieldResult], runs, extractor: str, which: str) -> None:
    errors = [(c.complaint_id, err) for c, _, _, err in runs if err]
    print(f"Clue accuracy: {extractor} on {which} ({len(runs)} complaints, {len(errors)} extraction errors)\n")
    print(f"{'field':<20}{'correct':>8}{'wrong':>8}{'missed':>8}{'n':>6}{'accuracy':>10}")
    for field in FIELDS:
        counts = Counter(r.verdict for r in results if r.field == field)
        n = sum(counts.values())
        if n:
            print(f"{field:<20}{counts['correct']:>8}{counts['wrong']:>8}{counts['missed']:>8}{n:>6}"
                  f"{counts['correct'] / n:>10.1%}")

    confusion = Counter((r.gold, r.got) for r in results if r.field == "category" and r.verdict != "correct")
    if confusion:
        print("\nCategory errors (gold -> predicted):")
        for (gold, got), n in confusion.most_common():
            print(f"  {n:>4}  {gold} -> {got}")

    usages: list[LLMUsage] = [u for _, _, u, _ in runs if u]
    if usages:
        cost = sum((u.cost_myr for u in usages), Decimal("0"))
        latency = sum(u.latency_ms for u in usages) / len(usages)
        print(f"\nUsage: {usages[0].provider}/{usages[0].model}, RM{cost:.4f} total, "
              f"{latency:.0f} ms mean latency, {sum(u.cached for u in usages)} cached, "
              f"{sum(u.retries for u in usages)} retries")
    for complaint_id, err in errors[:10]:
        print(f"  error {complaint_id}: {err}")


def write_details(path: Path, results: list[FieldResult], runs) -> None:
    """One row per scored field, for error analysis (filter verdict != correct)."""
    texts = {c.complaint_id: c.text for c, _, _, _ in runs}
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["complaint_id", "field", "verdict", "got", "gold", "text"])
        for r in results:
            writer.writerow([r.complaint_id, r.field, r.verdict, "" if r.got is None else r.got, r.gold,
                             texts[r.complaint_id]])


def engine_field_results(rows: list[EngineRow]) -> list[FieldResult]:
    """The engine's pick as a details row, so one CSV holds both clue and match errors."""
    return [FieldResult(r.complaint_id, "matched_txn", "correct" if r.top1 else "wrong",
                        f"{r.got_txn} [{r.status}]", r.gold_txn) for r in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--extractor", default="backend.agent.stubs:fake_extract", help="module:callable")
    parser.add_argument("--ids", default="pilot", help="pilot | holdout | all | path to an ID file")
    parser.add_argument("--details", type=Path, help="write per-field verdicts to this CSV")
    parser.add_argument("--concurrency", type=int, default=config.LLM_MAX_CONCURRENCY)
    parser.add_argument("--engine", action="store_true", help="also run match_and_decide and score the transaction")
    parser.add_argument("--no-cache", action="store_true", help="send every LLM call to the provider")
    args = parser.parse_args()

    from backend.llm.client import get_client
    from backend.llm.registry import check_config

    check_config()  # unknown provider or missing key fails here, before any call
    if args.no_cache:
        get_client().use_cache = False

    db = get_db()
    labels = {r["complaint_id"]: r for r in read("labels_train.csv")}
    ids = load_ids(args.ids)
    runs = asyncio.run(run_extractor(load_extractor(args.extractor), ids, args.concurrency,
                                     progress_every=25 if len(ids) > 50 else 0))
    results = [r for c, clues, _, _ in runs for r in score_complaint(c, labels[c.complaint_id], clues, db)]

    report(results, runs, args.extractor, args.ids)
    if args.engine:
        rows = [engine_check(c, labels[c.complaint_id], clues) for c, clues, _, _ in runs]
        engine_report(rows)
        results += engine_field_results(rows)
    if args.details:
        write_details(args.details, results, runs)
        print(f"\nDetails: {args.details}")


if __name__ == "__main__":
    main()
