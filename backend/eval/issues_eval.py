"""Second-issue check report: caught, false flags, cost and latency. Owner: Dev B.

Runs detect_issues() + other_issues() on the frozen set (backend/eval/issues/) against each row's labelled main
category, so the engine isn't needed and only the issues call is paid (and cached).

    python -m backend.eval.issues_eval --split dev            # tune the prompt on this half only
    python -m backend.eval.issues_eval --split final          # the merge gate, run once
    python -m backend.eval.issues_eval --split none --extra train   # every flag on single-issue sets is a false flag

--extra train|messy|test adds those sets: training and messy complaints carry one labelled issue each, so any flag
there is a false flag; test complaints (category from predictions.csv) are listed for reading.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import math
import sys
import time
from decimal import Decimal
from pathlib import Path

from backend import config
from backend.agent.issues import detect_issues, other_issues
from backend.contracts import Complaint
from starter.data import read

EVAL_DIR = Path(__file__).resolve().parent
ISSUES_DIR = EVAL_DIR / "issues"
ROOT = EVAL_DIR.parent.parent


def load_csv(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(open(path, encoding="utf-8")))


def rows_for(source: str, split: str) -> list[tuple[Complaint, str, set[str], str]]:
    """(complaint, main category, expected other categories, set name)."""
    if source == "issues":
        labels = {r["complaint_id"]: r for r in load_csv(ISSUES_DIR / "labels.csv")}
        out = []
        for r in load_csv(ISSUES_DIR / "complaints.csv"):
            lab = labels[r["complaint_id"]]
            if split in ("all", lab["split"]):
                out.append((Complaint(**r), lab["main_category"],
                            {c for c in lab["other_categories"].split(";") if c}, f"issues/{lab['split']}"))
        return out
    if source == "messy":
        labels = {r["complaint_id"]: r["category"] for r in load_csv(EVAL_DIR / "messy" / "labels_messy.csv")}
        return [(Complaint(**r), labels[r["complaint_id"]], set(), "messy")
                for r in load_csv(EVAL_DIR / "messy" / "complaints_messy.csv")]
    complaints = {r["complaint_id"]: r for r in read("complaints.csv")}
    if source == "train":
        return [(Complaint(**{k: complaints[lab["complaint_id"]][k] for k in
                              ("complaint_id", "customer_id", "received_at", "channel", "subject", "text")}),
                 lab["category"], set(), "train") for lab in read("labels_train.csv")]
    if source == "test":
        preds = load_csv(ROOT / "submissions" / config.TEAM_NAME / "predictions.csv")
        return [(Complaint(**{k: complaints[p["complaint_id"]][k] for k in
                              ("complaint_id", "customer_id", "received_at", "channel", "subject", "text")}),
                 p["category"], set(), "test") for p in preds]
    raise ValueError(source)


async def run(rows: list[tuple[Complaint, str, set[str], str]]) -> list[dict]:
    gate = asyncio.Semaphore(config.LLM_MAX_CONCURRENCY)

    async def one(complaint: Complaint, main: str, expected: set[str], name: str) -> dict:
        async with gate:
            began = time.perf_counter()
            try:
                issues, usage = await detect_issues(complaint)
                error = ""
            except Exception as exc:  # the pipeline treats this as "no second issue"
                issues, usage, error = [], None, f"{type(exc).__name__}: {exc}"
            seconds = time.perf_counter() - began
        kept = other_issues(issues, main, complaint)
        return {"set": name, "complaint_id": complaint.complaint_id, "main": main, "expected": expected,
                "kept": {i.category for i in kept}, "quotes": [f"{i.category}: {i.quote}" for i in kept],
                "all": [f"{i.category}: {i.quote}" for i in issues], "error": error, "seconds": seconds,
                "cost": usage.cost_myr if usage else Decimal("0"), "cached": bool(usage and usage.cached),
                "text": complaint.text}

    return await asyncio.gather(*(one(*r) for r in rows))


def report(results: list[dict], out: Path) -> None:
    for name in sorted({r["set"] for r in results}):
        rs = [r for r in results if r["set"] == name]
        two = [r for r in rs if r["expected"]]
        single = [r for r in rs if not r["expected"]]
        caught = [r for r in two if r["expected"] <= r["kept"]]
        flagged = [r for r in single if r["kept"]]
        line = f"{name:<14} {len(rs):>5} complaints"
        if two:
            line += f" | caught {len(caught)}/{len(two)} ({len(caught) / len(two):.0%})"
        line += f" | false flags {len(flagged)}/{len(single)}" if single else ""
        errors = sum(1 for r in rs if r["error"])
        print(line + (f" | {errors} errors" if errors else ""))
        for r in two:
            if not r["expected"] <= r["kept"]:
                print(f"    missed  {r['complaint_id']} {r['main']} expected {sorted(r['expected'])}, got {r['all']}")
        for r in flagged:
            print(f"    flagged {r['complaint_id']} {r['main']} -> {r['quotes']}")
    secs = sorted(r["seconds"] for r in results if not r["cached"]) or [0.0]
    total = sum((r["cost"] for r in results), Decimal("0"))
    print(f"cost RM{total:.4f} ({sum(r['cached'] for r in results)} cached) | "
          f"latency p50 {secs[len(secs) // 2]:.1f}s p95 {secs[max(0, math.ceil(0.95 * len(secs)) - 1)]:.1f}s")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["set", "complaint_id", "main", "expected", "kept", "quotes", "all", "error", "text"])
        w.writeheader()
        for r in results:
            w.writerow({k: ";".join(sorted(r[k])) if isinstance(r[k], set) else
                        (" | ".join(r[k]) if isinstance(r[k], list) else r[k]) for k in w.fieldnames})
    print(f"details: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", default="dev", choices=["dev", "final", "all", "none"])
    parser.add_argument("--extra", action="append", default=[], choices=["train", "messy", "test"])
    parser.add_argument("--out", type=Path, default=ROOT / "backend" / ".cache" / "issues_eval.csv")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    rows = [] if args.split == "none" else rows_for("issues", args.split)
    for extra in args.extra:
        rows += rows_for(extra, args.split)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    report(asyncio.run(run(rows)), args.out)


if __name__ == "__main__":
    main()
