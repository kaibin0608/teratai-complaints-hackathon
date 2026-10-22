"""Export: exact columns, validation, gaps reported not invented, autonomous run only."""
import asyncio
import csv

import pytest

from backend.batch.runner import run_batch, select_ids
from backend.batch.submit import build_export, labels_for, validate_row, write_csv
from backend.contracts import PREDICTION_COLUMNS
from backend.db.store import CaseStore

IDS = select_ids("pilot", limit=6)


@pytest.fixture
def store():
    s = CaseStore(":memory:")
    asyncio.run(run_batch(IDS, s, log=lambda _: None))
    return s


GOOD = {"complaint_id": "CMP-1", "category": "ATM_NOT_DISPENSED", "matched_txn_id": "TXN-0088211", "outcome": "REFUND",
        "refund_amount_myr": "550.00", "priority": "P2", "reply_language": "EN", "route": "HUMAN_APPROVAL",
        "reply_text": "Dear customer"}


def test_valid_export_has_exact_header_and_rows(store, tmp_path):
    report = build_export(IDS, store)
    assert report.ok and len(report.rows) == 6
    out = tmp_path / "predictions.csv"
    write_csv(out, report.rows)
    with open(out, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0]) == PREDICTION_COLUMNS and [r["complaint_id"] for r in rows] == IDS


@pytest.mark.parametrize("change, problem", [
    ({"reply_text": "  "}, "reply_text is empty"),
    ({"refund_amount_myr": "550.5"}, "two-decimal"),
    ({"refund_amount_myr": "-1.00"}, "two-decimal"),
    ({"matched_txn_id": "88211"}, "TXN-nnnnnnn"),
    ({"route": "AUTO"}, "route="),
])
def test_bad_rows_are_reported(change, problem):
    assert validate_row(GOOD) == []
    assert any(problem in p for p in validate_row({**GOOD, **change}))


def test_missing_complaints_are_listed_not_invented(store):
    report = build_export(IDS + ["CMP-00004", "CMP-00010"], store)  # two test complaints never run
    assert not report.ok and len(report.rows) == 6
    assert [cid for cid, _ in report.missing] == ["CMP-00004", "CMP-00010"]


def test_failed_case_is_missing_with_reason(store):
    def broken(complaint, clues):
        raise RuntimeError("bug")

    asyncio.run(run_batch(["CMP-00004"], store, pipeline_kwargs={"engine": broken}, log=lambda _: None))
    report = build_export(["CMP-00004"], store)
    assert report.missing[0][0] == "CMP-00004" and "engine failed" in report.missing[0][1]


def test_export_reads_the_autonomous_run(store):
    cid = IDS[0]
    exported = build_export([cid], store).rows[0]["reply_text"]
    with store.conn:  # a human edit lives in events, never in agent_runs
        store._event(cid, "edit", None, {"reply_text": "EDITED BY OFFICER"}, actor="Aina")
    assert build_export([cid], store).rows[0]["reply_text"] == exported


def test_duplicate_requested_ids_are_invalid(store):
    report = build_export([IDS[0], IDS[0]], store)
    assert any("requested 2 times" in p for _, p in report.invalid)


def test_labels_filtered_to_requested_ids(tmp_path):
    path = labels_for(IDS, tmp_path / "labels.csv")
    with open(path, encoding="utf-8", newline="") as fh:
        assert [r["complaint_id"] for r in csv.DictReader(fh)] == IDS


def test_strict_writes_nothing_when_incomplete(tmp_path, monkeypatch):
    from backend.batch import submit

    db = tmp_path / "t.db"
    asyncio.run(run_batch(IDS[:2], CaseStore(db), log=lambda _: None))
    ids_file = tmp_path / "ids.txt"
    ids_file.write_text("\n".join(IDS[:3]), encoding="utf-8")  # third one never ran
    out = tmp_path / "p.csv"
    monkeypatch.setattr("sys.argv", ["submit", "--ids", str(ids_file), "--out", str(out), "--db", str(db), "--strict"])
    with pytest.raises(SystemExit) as exit_info:
        submit.main()
    assert "Not written" in str(exit_info.value) and not out.exists()

    monkeypatch.setattr("sys.argv", ["submit", "--ids", str(ids_file), "--out", str(out), "--db", str(db)])
    with pytest.raises(SystemExit) as exit_info:  # default: write the valid rows, exit non-zero
        submit.main()
    with open(out, encoding="utf-8", newline="") as fh:  # replies span lines: count CSV rows, not lines
        assert exit_info.value.code == 1 and len(list(csv.DictReader(fh))) == 2
