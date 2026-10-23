"""Write predictions.csv from each case's autonomous run, validate it, and optionally score it. Owner: Dev B.

Only the agent's own decision is exported (cases.autonomous_run_id), never human edits. A complaint without a
stored decision is reported by ID and left out; a missing row scores 0, but an invented one could be a critical
error, so nothing is ever filled in.

Usage:
    python -m backend.batch.submit                                  # test set -> submissions/<TEAM_NAME>/predictions.csv
    python -m backend.batch.submit --ids train --score --details train_details.csv
    python -m backend.batch.submit --ids pilot --score
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import get_args

from backend import config
from backend.batch.runner import select_ids
from backend.contracts import PREDICTION_COLUMNS, Category, Language, Outcome, Priority, Route
from backend.db.store import CaseStore

ALLOWED = {"category": get_args(Category), "outcome": get_args(Outcome), "priority": get_args(Priority),
           "reply_language": get_args(Language), "route": get_args(Route)}
TXN_RE = re.compile(r"^TXN-\d{7}$")
MONEY_RE = re.compile(r"^\d+\.\d{2}$")


def validate_row(row: dict[str, str]) -> list[str]:
    problems = [f"{col}={row[col]!r} is not one of {', '.join(allowed)}"
                for col, allowed in ALLOWED.items() if row[col] not in allowed]
    if not MONEY_RE.match(row["refund_amount_myr"]):
        problems.append(f"refund_amount_myr={row['refund_amount_myr']!r} is not a non-negative two-decimal amount")
    if row["matched_txn_id"] and not TXN_RE.match(row["matched_txn_id"]):
        problems.append(f"matched_txn_id={row['matched_txn_id']!r} is not TXN-nnnnnnn")
    if not row["reply_text"].strip():
        problems.append("reply_text is empty")
    return problems


@dataclass
class ExportReport:
    requested: int = 0
    rows: list[dict[str, str]] = field(default_factory=list)
    missing: list[tuple[str, str]] = field(default_factory=list)  # (complaint_id, why there is no row)
    invalid: list[tuple[str, str]] = field(default_factory=list)  # (complaint_id, failed check)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.invalid and len(self.rows) == self.requested


def build_export(ids: list[str], store: CaseStore) -> ExportReport:
    report = ExportReport(requested=len(ids))
    for complaint_id, n in Counter(ids).items():
        if n > 1:
            report.invalid.append((complaint_id, f"requested {n} times"))
    cases = store.cases_for(list(dict.fromkeys(ids)))
    for complaint_id in dict.fromkeys(ids):
        case = cases.get(complaint_id)
        if case is None:
            report.missing.append((complaint_id, "never run"))
        elif case["status"] != "done":
            report.missing.append((complaint_id, f"{case['status']}: {case['error'] or ''}".strip()))
        else:
            run = store.run(case["autonomous_run_id"])
            row = run.prediction_row()
            problems = validate_row(row)
            if problems:
                report.invalid.extend((complaint_id, p) for p in problems)
            else:
                report.rows.append(row)
    return report


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=PREDICTION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def labels_for(ids: list[str], path: Path) -> Path:
    """score.py scores every label row (a missing prediction scores 0), so give it only the requested IDs."""
    wanted = set(ids)
    with open(config.DATA_DIR / "labels_train.csv", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = [r for r in reader if r["complaint_id"] in wanted]
        columns = reader.fieldnames
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


def default_out(which: str) -> Path:
    if which == "test":
        return config.ROOT / "submissions" / config.TEAM_NAME / "predictions.csv"
    return config.ROOT / "backend" / ".cache" / f"{Path(which).stem}_predictions.csv"  # gitignored


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ids", default="test", help="test | train | pilot | holdout | path to an ID file")
    parser.add_argument("--out", type=Path, help="default: submissions/<TEAM_NAME>/predictions.csv for test")
    parser.add_argument("--strict", action="store_true", help="write nothing unless every requested row is valid")
    parser.add_argument("--score", action="store_true", help="run scoring/score.py against labels_train.csv")
    parser.add_argument("--details", type=Path, help="with --score: the scorer's per-complaint details CSV")
    parser.add_argument("--db", type=Path, default=config.DB_PATH)
    args = parser.parse_args()

    ids = select_ids(args.ids)
    out = args.out or default_out(args.ids)
    report = build_export(ids, CaseStore(args.db))

    for complaint_id, why in report.missing[:20]:
        print(f"  missing {complaint_id}: {why}")
    for complaint_id, problem in report.invalid[:20]:
        print(f"  invalid {complaint_id}: {problem}")
    if args.strict and not report.ok:
        sys.exit(f"Not written (--strict): {len(report.missing)} missing, {len(report.invalid)} invalid "
                 f"of {report.requested} requested")
    write_csv(out, report.rows)
    verdict = "valid" if report.ok else f"INCOMPLETE: {len(report.missing)} missing, {len(report.invalid)} invalid"
    print(f"{len(report.rows)}/{report.requested} rows written to {out} ({verdict})")

    if args.score:
        if args.ids == "test":
            sys.exit("--score needs training IDs; the test set has no labels")
        labels = labels_for(ids, config.ROOT / "backend" / ".cache" / f"{Path(args.ids).stem}_labels.csv")
        command = [sys.executable, str(config.ROOT / "scoring" / "score.py"), str(out), str(labels)]
        if args.details:
            command += ["--details", str(args.details)]
        subprocess.run(command, check=False)
    if not report.ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
