"""Run many complaints through the pipeline and store every run. Owner: Dev B.

Resumable: complaints whose case already has a decision are skipped, so rerunning the same command after a crash
only pays for what is left. --rerun makes new runs for everything selected (after a prompt, model or engine change);
unchanged LLM requests still come from the cache.

Usage:
    python -m backend.batch.runner --ids pilot --no-draft
    python -m backend.batch.runner --ids train
    python -m backend.batch.runner --ids test
    python -m backend.batch.runner --ids my_ids.txt --rerun
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Callable

from backend import config
from backend.agent.pipeline import run_pipeline
from backend.agent.stubs import stub_draft
from backend.agent.tools import get_db, load_complaint
from backend.contracts import AgentRun
from backend.db.store import CaseConflict, CaseStore, HumanActedError, run_cost
from backend.llm.types import ConfigError

EVAL_DIR = config.ROOT / "backend" / "eval"
PROGRESS_EVERY = 50


def select_ids(which: str, limit: int | None = None) -> list[str]:
    """test | train | pilot | holdout | path to a file with one complaint_id per line (a CSV header is skipped)."""
    if which == "test":
        path = config.DATA_DIR / "test_ids.csv"
    elif which == "train":
        path = config.DATA_DIR / "labels_train.csv"
    elif which in ("pilot", "holdout"):
        path = EVAL_DIR / f"{which}_ids.txt"
    else:
        path = Path(which)
    with open(path, encoding="utf-8") as fh:
        first_column = [row[0].strip() for row in csv.reader(fh) if row and row[0].strip()]
    ids = [i for i in first_column if i != "complaint_id"]
    return ids[:limit] if limit else ids


@dataclass
class BatchResult:
    selected: int = 0
    skipped: int = 0
    runs: list[tuple[AgentRun, int]] = field(default_factory=list)  # (run, end-to-end latency ms)
    rejected: list[tuple[str, str]] = field(default_factory=list)   # stored nothing: conflict or human acted
    wall_s: float = 0.0

    @property
    def failed(self) -> list[AgentRun]:
        return [r for r, _ in self.runs if r.decision is None]


async def run_batch(
    ids: list[str],
    store: CaseStore,
    *,
    concurrency: int = config.LLM_MAX_CONCURRENCY,
    rerun: bool = False,
    pipeline_kwargs: dict | None = None,
    log: Callable[[str], None] = print,
) -> BatchResult:
    get_db()  # load the CSVs once, before tasks start
    result = BatchResult(selected=len(ids))
    existing = store.cases_for(ids)
    todo = [i for i in ids if rerun or existing.get(i, {}).get("status") != "done"]
    result.skipped = len(ids) - len(todo)
    gate = asyncio.Semaphore(concurrency)
    start = time.perf_counter()

    async def one(complaint_id: str) -> None:
        complaint = load_complaint(complaint_id)
        async with gate:
            began = time.perf_counter()
            run = await run_pipeline(complaint, **(pipeline_kwargs or {}))
            latency_ms = max(1, int((time.perf_counter() - began) * 1000))
        try:
            store.save_run(complaint, run, latency_ms, rerun=rerun)
        except (CaseConflict, HumanActedError) as exc:
            result.rejected.append((complaint_id, str(exc)))
            return
        result.runs.append((run, latency_ms))
        if len(result.runs) % PROGRESS_EVERY == 0:
            cost = sum((run_cost(r) for r, _ in result.runs), Decimal("0"))
            log(f"  {len(result.runs)}/{len(todo)} stored, {len(result.failed)} failed, RM{cost:.4f} so far")

    await asyncio.gather(*(one(i) for i in todo))
    result.wall_s = time.perf_counter() - start
    return result


def summarize(result: BatchResult) -> str:
    runs = [r for r, _ in result.runs]
    decided = [r.decision for r in runs if r.decision is not None]
    latencies = sorted(ms for _, ms in result.runs)
    cost = sum((run_cost(r) for r in runs), Decimal("0"))
    lines = [f"Selected {result.selected}: {len(runs)} processed, {result.skipped} skipped (already done), "
             f"{len(result.failed)} failed, {len(result.rejected)} rejected, in {result.wall_s:.1f}s"]
    if decided:
        lines.append("Routes:       " + ", ".join(f"{k} {v}" for k, v in Counter(d.route for d in decided).most_common()))
        holds = Counter(d.hold_reason or "none" for d in decided)
        lines.append("Hold reasons: " + ", ".join(f"{k} {v}" for k, v in holds.most_common()))
        if holds.get("llm_error"):
            lines.append(f"WARNING: {holds['llm_error']} complaints fell back to keywords or the template reply "
                         f"(llm_error). Rerun them once the provider is healthy.")
    if runs:
        p95 = latencies[min(len(latencies) - 1, int(0.95 * len(latencies)))]
        lines.append(f"Cost:         RM{cost:.4f} total, RM{cost / len(runs):.5f} per complaint")
        lines.append(f"Latency:      {sum(latencies) / len(latencies) / 1000:.1f}s mean, {p95 / 1000:.1f}s p95 per complaint")
    for run in result.failed[:10]:
        lines.append(f"  failed {run.complaint_id}: {run.error}")
    for complaint_id, reason in result.rejected[:10]:
        lines.append(f"  rejected {complaint_id}: {reason}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ids", default="pilot", help="test | train | pilot | holdout | path to an ID file")
    parser.add_argument("--limit", type=int, help="only the first N selected complaints")
    parser.add_argument("--concurrency", type=int, default=config.LLM_MAX_CONCURRENCY)
    parser.add_argument("--rerun", action="store_true", help="new runs even for complaints that are already done")
    parser.add_argument("--no-draft", action="store_true", help="template replies, no drafting LLM calls")
    parser.add_argument("--no-cache", action="store_true", help="send every LLM call to the provider")
    parser.add_argument("--db", type=Path, default=config.DB_PATH)
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # progress shows up live, even when redirected to a file

    from backend.llm.client import get_client
    from backend.llm.registry import check_config

    try:
        check_config()
    except ConfigError as exc:
        sys.exit(f"Config error: {exc}")
    if args.no_cache:
        get_client().use_cache = False

    ids = select_ids(args.ids, args.limit)
    store = CaseStore(args.db)
    print(f"Running {len(ids)} complaints ({args.ids}) with extractor {config.LLM_EXTRACT}, "
          f"concurrency {args.concurrency}, db {args.db}")
    kwargs = {"draft": stub_draft} if args.no_draft else {}
    result = asyncio.run(run_batch(ids, store, concurrency=args.concurrency, rerun=args.rerun, pipeline_kwargs=kwargs))
    print(summarize(result))
    if result.failed or result.rejected:
        sys.exit(1)


if __name__ == "__main__":
    main()
