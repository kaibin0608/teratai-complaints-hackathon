"""CaseStore: saves pipeline runs and keeps each case's state. Owner: Dev B.

Integrity rules (PLAN.md "Data Model"):
- agent_runs rows never change (triggers); a rerun adds a new run.
- cases.autonomous_run_id is what predictions.csv exports. Only an agent rerun may repoint it, and only before any
  human has acted on the case.
- case_events only grows. outbound_messages can hold at most one message per kind per complaint.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Any

from backend import config
from backend.contracts import AgentRun, Complaint, now_myt
from backend.db.schema import init_db

CASE_STATE = {  # route -> (case_state, sent) per docs/api.md; fraud holding replies wait for an analyst
    "AUTO_RESOLVE": ("auto_resolved", True),
    "HUMAN_APPROVAL": ("awaiting_approval", False),
    "FRAUD_TEAM": ("with_fraud_team", False),
}


class CaseConflict(Exception):
    """Same complaint_id, different content."""


class HumanActedError(Exception):
    """A rerun would replace the agent's decision on a case a person has already acted on."""


def content_hash(complaint: Complaint) -> str:
    fields = [complaint.complaint_id, complaint.customer_id, f"{complaint.received_at:%Y-%m-%d %H:%M}",
              complaint.channel, complaint.subject, complaint.text]
    return hashlib.sha256("\x1f".join(f.strip() for f in fields).encode("utf-8")).hexdigest()


def _now() -> str:
    return f"{now_myt():%Y-%m-%d %H:%M:%S}"


def run_cost(run: AgentRun) -> Decimal:
    return run.extract_usage.cost_myr + sum((u.cost_myr for u in run.draft_usage), Decimal("0"))


class CaseStore:
    def __init__(self, path: Path | str = config.DB_PATH):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        init_db(self.conn)

    # --- writes ---

    def save_run(self, complaint: Complaint, run: AgentRun, latency_ms: int, *, rerun: bool = False) -> dict[str, Any]:
        """Store one run and move its case to the state its route implies. Returns the updated case."""
        existing = self.get_case(complaint.complaint_id)
        digest = content_hash(complaint)
        if existing:
            if existing["content_hash"] != digest:
                raise CaseConflict(f"{complaint.complaint_id} already exists with different content")
            if existing["status"] == "done" and not rerun:
                raise ValueError(f"{complaint.complaint_id} already has a decision; pass rerun=True to replace it")
            if self.human_acted(complaint.complaint_id):
                raise HumanActedError(f"{complaint.complaint_id}: a person has acted; the agent decision is final")

        d, now = run.decision, _now()
        if d is not None:
            status, error = "done", None
            case_state, sent = CASE_STATE[d.route]
        else:
            status, error, case_state, sent = "error", run.error or "no decision", None, False
        if existing and existing["sent"]:  # a message that went out stays sent
            sent = True

        with self.conn:  # one transaction
            self.conn.execute(
                "INSERT INTO agent_runs VALUES (?,?,?,?, ?,?,?,?,?,?,?, ?,?,?, ?,?,?, ?,?,?)",
                (run.run_id, run.complaint_id, run.run_kind, _now(),
                 d and d.category, d and (d.matched_txn_id or ""), d and d.outcome,
                 d and int(d.refund_amount_myr * 100), d and d.priority, d and d.reply_language, d and d.route,
                 d and d.hold_reason, None if run.self_check is None else ("passed" if run.self_check.passed else "flagged"),
                 run.error,
                 f"{run.extract_usage.provider}:{run.extract_usage.model}", run.prompt_version, run.schema_version,
                 str(run_cost(run)), latency_ms, run.model_dump_json()),
            )
            if not existing:
                self.conn.execute(
                    "INSERT INTO cases VALUES (?,?,?,?,?,?,?, ?,?, ?,?,?,?, ?,?)",
                    (complaint.complaint_id, complaint.customer_id, f"{complaint.received_at:%Y-%m-%d %H:%M}",
                     complaint.channel, complaint.subject, complaint.text, digest,
                     run.run_id, run.run_id, status, case_state, int(sent), error, now, now),
                )
                self._event(complaint.complaint_id, "ingest", None, None)
            else:
                autonomous = run.run_id if run.run_kind == "autonomous" else existing["autonomous_run_id"]
                self.conn.execute(
                    "UPDATE cases SET autonomous_run_id=?, current_run_id=?, status=?, case_state=?, sent=?, error=?,"
                    " updated_at=? WHERE complaint_id=?",
                    (autonomous, run.run_id, status, case_state, int(sent), error, now, complaint.complaint_id),
                )
            detail = {"route": d and d.route, "hold_reason": d and d.hold_reason, "error": run.error,
                      "previous_run_id": existing and existing["current_run_id"]}
            self._event(complaint.complaint_id, "agent_run", run.run_id, detail)
            if case_state == "auto_resolved":
                self.conn.execute(
                    "INSERT OR IGNORE INTO outbound_messages"
                    " (complaint_id, run_id, kind, reply_text, refund_sen, authorised_by, status, created_at)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (complaint.complaint_id, run.run_id, "resolution", run.reply_text,
                     int(d.refund_amount_myr * 100), "auto", "sent", now),
                )
        return self.get_case(complaint.complaint_id)

    def _event(self, complaint_id: str, action: str, run_id: str | None, detail: dict | None, actor: str = "agent") -> None:
        self.conn.execute(
            "INSERT INTO case_events (complaint_id, actor, action, run_id, detail, created_at) VALUES (?,?,?,?,?,?)",
            (complaint_id, actor, action, run_id, json.dumps(detail) if detail else None, _now()),
        )

    # --- reads ---

    def get_case(self, complaint_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM cases WHERE complaint_id = ?", (complaint_id,)).fetchone()
        return dict(row) if row else None

    def cases_for(self, complaint_ids: list[str]) -> dict[str, dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        for start in range(0, len(complaint_ids), 500):  # stay under SQLite's variable limit
            chunk = complaint_ids[start:start + 500]
            rows = self.conn.execute(
                f"SELECT * FROM cases WHERE complaint_id IN ({','.join('?' * len(chunk))})", chunk).fetchall()
            found.update({r["complaint_id"]: dict(r) for r in rows})
        return found

    def run(self, run_id: str) -> AgentRun | None:
        row = self.conn.execute("SELECT run_json FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
        return AgentRun.model_validate_json(row[0]) if row else None

    def autonomous_run(self, complaint_id: str) -> AgentRun | None:
        case = self.get_case(complaint_id)
        return self.run(case["autonomous_run_id"]) if case and case["autonomous_run_id"] else None

    def events(self, complaint_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM case_events WHERE complaint_id = ? ORDER BY id", (complaint_id,))
        return [dict(r) for r in rows]

    def outbound(self, complaint_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM outbound_messages WHERE complaint_id = ? ORDER BY id", (complaint_id,))
        return [dict(r) for r in rows]

    def human_acted(self, complaint_id: str) -> bool:
        return self.conn.execute("SELECT 1 FROM case_events WHERE complaint_id = ? AND actor != 'agent' LIMIT 1",
                                 (complaint_id,)).fetchone() is not None
