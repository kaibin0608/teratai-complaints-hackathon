"""Compare extraction models end to end: extract → Dev A's engine → the leaderboard's scoring. Owner: Dev B.

Only the extraction model changes; the prompt (extract-v2), the engine and the scoring are the same for every model.
No reply drafting and no second-issue check (LLM_ISSUES=off), so only extraction is compared. Every call goes to the
provider (no cache), so latency and cost are comparable. A failed extraction falls back to keyword clues, exactly as
the pipeline does, and is counted.

Some newer models (e.g. Claude Haiku 5.5, GPT-6 Luna) reject `temperature`; with OpenRouter's require_parameters (which
guarantees strict JSON) they then get no endpoint at all (HTTP 404). --no-temperature MODEL... leaves it out for those
models only; the others are sent exactly what production sends.

Sets:
  holdout   340 training complaints never used for tuning (the honest one)
  messy     42 training complaints rewritten in real customer style (the hidden test's style)
  langmiss  training complaints the current extractor gets the reply language wrong on (biased toward the
            current model by construction: it shows whether another model fixes those, not overall language accuracy)

    python -m backend.eval.model_compare --models openrouter:deepseek/deepseek-v4-flash openrouter:anthropic/claude-haiku-5.5
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import importlib.util
import math
import sys
import time
from collections import Counter
from decimal import Decimal
from pathlib import Path

from backend import config
from backend.agent.engine import match_and_decide
from backend.agent.parser import extract
from backend.agent.stubs import fake_extract
from backend.agent.tools import load_complaint
from backend.contracts import Complaint
from backend.llm.client import get_client
from backend.llm.openai_compatible_adapter import OpenAICompatibleAdapter
from starter.data import read

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent.parent
_spec = importlib.util.spec_from_file_location("leaderboard_score", ROOT / "scoring" / "score.py")
score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score)  # the organisers' scorer: WEIGHTS, GATED, field_ok, money

FIELDS = ("category", "matched_txn_id", "outcome", "refund_amount_myr", "priority", "reply_language")


def load_set(name: str) -> list[tuple[Complaint, dict[str, str]]]:
    labels = {r["complaint_id"]: r for r in read("labels_train.csv")}
    if name == "holdout":
        ids = (EVAL_DIR / "holdout_ids.txt").read_text(encoding="utf-8").split()
        return [(load_complaint(i), labels[i]) for i in ids]
    if name == "langmiss":
        ids = (EVAL_DIR / "langmiss_ids.txt").read_text(encoding="utf-8").split()
        return [(load_complaint(i), labels[i]) for i in ids]
    if name == "messy":
        messy = {r["complaint_id"]: r for r in csv.DictReader(open(EVAL_DIR / "messy" / "labels_messy.csv",
                                                                   encoding="utf-8"))}
        return [(Complaint(**r), messy[r["complaint_id"]])
                for r in csv.DictReader(open(EVAL_DIR / "messy" / "complaints_messy.csv", encoding="utf-8"))]
    raise ValueError(name)


async def run_model(model: str, rows: list[tuple[Complaint, dict[str, str]]]) -> list[dict]:
    config.LLM_EXTRACT = model
    gate = asyncio.Semaphore(config.LLM_MAX_CONCURRENCY)

    async def one(complaint: Complaint, label: dict[str, str]) -> dict:
        async with gate:
            began = time.perf_counter()
            try:
                clues, usage = await extract(complaint)
                failed = False
            except Exception:  # the pipeline's fallback
                clues, usage = await fake_extract(complaint)
                failed = True
            seconds = time.perf_counter() - began
        d = match_and_decide(complaint, clues).decision
        pred = {"category": d.category, "matched_txn_id": d.matched_txn_id or "", "outcome": d.outcome,
                "refund_amount_myr": f"{d.refund_amount_myr:.2f}", "priority": d.priority,
                "reply_language": d.reply_language}
        got = {f: score.field_ok(f, pred[f], label[f]) for f in score.WEIGHTS}
        for f in score.GATED:
            got[f] = got[f] and got["matched_txn_id"]
        critical = ((score.money(pred["refund_amount_myr"]) or 0) > 0 and label["outcome"] in ("DECLINE", "INVESTIGATE")) \
            or (label["outcome"] == "INVESTIGATE" and pred["outcome"] != "INVESTIGATE")
        return {"complaint_id": complaint.complaint_id, "points": sum(score.WEIGHTS[f] for f, ok in got.items() if ok),
                "got": got, "critical": critical, "failed": failed, "seconds": seconds,
                "cost": usage.cost_myr, "wrong": [f"{f}: {pred[f]} vs {label[f]}" for f, ok in got.items() if not ok]}

    return await asyncio.gather(*(one(c, lab) for c, lab in rows))


def summarise(results: list[dict]) -> dict:
    n = len(results)
    mean = sum(r["points"] for r in results) / n
    crit = sum(r["critical"] for r in results)
    secs = sorted(r["seconds"] for r in results)
    return {"final": max(0.0, mean * (1 - 2 * crit / n)), "critical": crit,
            "acc": {f: sum(r["got"][f] for r in results) / n for f in score.WEIGHTS},
            "failed": sum(r["failed"] for r in results),
            "p50": secs[n // 2], "p95": secs[max(0, math.ceil(0.95 * n) - 1)],
            "cost": sum((r["cost"] for r in results), Decimal("0"))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--sets", nargs="+", default=["holdout", "messy", "langmiss"])
    parser.add_argument("--out", type=Path, default=ROOT / "backend" / ".cache" / "model_compare.csv")
    parser.add_argument("--no-temperature", nargs="*", default=[], help="models that reject the temperature parameter")
    args = parser.parse_args()
    no_temperature = {m.split(":", 1)[-1] for m in args.no_temperature}
    production_body = OpenAICompatibleAdapter.body

    def body(self, request):  # eval only: drop temperature for the named models
        sent = production_body(self, request)
        if request.model in no_temperature:
            sent.pop("temperature", None)
        return sent

    OpenAICompatibleAdapter.body = body
    sys.stdout.reconfigure(encoding="utf-8")
    config.LLM_ISSUES = "off"  # extraction only
    get_client().use_cache = False  # fair latency and cost for every model

    sets = {name: load_set(name) for name in args.sets}
    detail = []
    print(f"{'set':<9} {'model':<44} {'score':>6} {'crit':>4} {'txn':>6} {'cat':>6} {'lang':>6} "
          f"{'fail':>4} {'p50':>6} {'p95':>6} {'cost RM':>8}")
    for name, rows in sets.items():
        for model in args.models:
            results = asyncio.run(run_model(model, rows))
            s = summarise(results)
            print(f"{name:<9} {model.removeprefix('openrouter:'):<44} {s['final']:>6.2f} {s['critical']:>4} "
                  f"{s['acc']['matched_txn_id']:>6.1%} {s['acc']['category']:>6.1%} {s['acc']['reply_language']:>6.1%} "
                  f"{s['failed']:>4} {s['p50']:>5.1f}s {s['p95']:>5.1f}s {s['cost']:>8.4f}", flush=True)
            detail += [{"set": name, "model": model, "complaint_id": r["complaint_id"], "points": r["points"],
                        "critical": r["critical"], "failed": r["failed"], "seconds": f"{r['seconds']:.1f}",
                        "wrong": " | ".join(r["wrong"])} for r in results]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(detail[0]))
        w.writeheader()
        w.writerows(detail)
    print(f"details: {args.out}")


if __name__ == "__main__":
    main()
