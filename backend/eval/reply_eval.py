"""Draft replies for a set of training complaints and measure them, to compare drafting models. Owner: Dev B.

Extraction comes from the LLM cache, so a second model only pays for drafting. Replies go to a CSV to read.

Usage:
    python -m backend.eval.reply_eval --model openrouter:deepseek/deepseek-v4-flash
    python -m backend.eval.reply_eval --model openrouter:anthropic/claude-haiku-5.5 --ids pilot
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from decimal import Decimal
from pathlib import Path

from backend import config
from backend.agent.pipeline import run_pipeline
from backend.agent.reply_rules import check as rules_check
from backend.agent.tools import get_db, load_complaint
from backend.batch.runner import select_ids
from backend.contracts import AgentRun, EngineResult


async def draft_all(ids: list[str], concurrency: int) -> list[AgentRun]:
    get_db()
    gate = asyncio.Semaphore(concurrency)

    async def one(complaint_id: str) -> AgentRun:
        async with gate:
            return await run_pipeline(load_complaint(complaint_id))

    return await asyncio.gather(*(one(i) for i in ids))


def report(runs: list[AgentRun], model: str) -> None:
    decided = [r for r in runs if r.decision is not None]
    n = len(decided)
    first = sum(r.redraft_count == 0 and r.self_check.passed for r in decided)
    final = sum(r.self_check.passed for r in decided)
    held = sum(r.decision.hold_reason == "self_check_failed" for r in decided)
    fallback = sum(r.decision.hold_reason == "llm_error" for r in decided)
    refunds = [r for r in decided if r.decision.refund_amount_myr > 0]
    stated = sum(not any("refund amount" in p for p in r.self_check.problems) for r in refunds)
    language_ok = sum(not any(p.startswith("the reply is not in") for p in
                              rules_check(r.reply_text, EngineResult(match=r.match, decision=r.decision,
                                                                     evidence=r.evidence)).problems) for r in decided)
    words = [len(r.reply_text.split()) for r in decided]
    cost = sum((u.cost_myr for r in decided for u in r.draft_usage), Decimal("0"))
    latency = sorted(sum(u.latency_ms for u in r.draft_usage) for r in decided)
    p95 = latency[min(n - 1, int(0.95 * n))] if n else 0
    print(f"Replies: {model} on {n} complaints\n")
    print(f"  self-check passed, first draft   {first}/{n} ({first / n:.0%})")
    print(f"  self-check passed, after redraft {final}/{n} ({final / n:.0%})")
    print(f"  held self_check_failed           {held}")
    print(f"  fell back to code reply          {fallback}")
    print(f"  refund amount stated             {stated}/{len(refunds)}")
    print(f"  language rule passed             {language_ok}/{n}")
    print(f"  words per reply                  {sum(words) / n:.0f} mean, {min(words)}-{max(words)}")
    print(f"  drafting cost                    RM{cost:.4f} (RM{cost / n:.5f} per reply)")
    print(f"  drafting latency                 {sum(latency) / n / 1000:.1f}s mean, {p95 / 1000:.1f}s p95")
    for r in [r for r in decided if r.error][:8]:
        print(f"  error {r.complaint_id}: {r.error[:200]}")


def write_replies(path: Path, runs: list[AgentRun]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["complaint_id", "outcome", "route", "reply_language", "refund", "passed", "redrafts",
                         "problems", "reply_text"])
        for r in runs:
            if r.decision is None:
                continue
            d = r.decision
            writer.writerow([r.complaint_id, d.outcome, d.route, d.reply_language, f"{d.refund_amount_myr:.2f}",
                             r.self_check.passed, r.redraft_count, "; ".join(r.self_check.problems), r.reply_text])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ids", default="pilot", help="pilot | holdout | train | path to an ID file")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--model", default=config.LLM_DRAFT, help="provider:model for drafting (overrides LLM_DRAFT)")
    parser.add_argument("--out", type=Path, help="replies CSV (default backend/.cache/replies_<model>.csv)")
    parser.add_argument("--concurrency", type=int, default=config.LLM_MAX_CONCURRENCY)
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)

    from backend.llm.registry import check_config

    config.LLM_DRAFT = args.model
    check_config()
    runs = asyncio.run(draft_all(select_ids(args.ids, args.limit), args.concurrency))
    report(runs, args.model)
    out = args.out or config.ROOT / "backend" / ".cache" / f"replies_{args.model.replace(':', '_').replace('/', '_')}.csv"
    write_replies(out, runs)
    print(f"\nReplies: {out}")


if __name__ == "__main__":
    main()
