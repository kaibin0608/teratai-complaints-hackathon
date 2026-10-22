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
from typing import Any, Callable

from backend import config
from backend.contracts import AgentRun, CheckResult, Complaint, EngineResult, now_myt
from backend.db.schema import init_db

CASE_STATE = {  # route -> (case_state, sent) per docs/api.md; fraud holding replies wait for an analyst
    "AUTO_RESOLVE": ("auto_resolved", True),
    "HUMAN_APPROVAL": ("awaiting_approval", False),
    "FRAUD_TEAM": ("with_fraud_team", False),
}


ACTIONS = ("approve", "reject", "edit_approve")


class CaseConflict(Exception):
    """Same complaint_id, different content."""


class NotFound(Exception):
    """No case with that complaint_id."""


class WrongState(Exception):
    """The case is not in a state that allows this action (HTTP 409)."""


class InvalidAction(Exception):
    """Missing actor or reason, or an unknown action (HTTP 422)."""


class ReplyRefused(Exception):
    """An edited reply failed the self-check; nothing was sent (HTTP 422)."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


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
                self._insert_case(complaint, digest, status, now, run_id=run.run_id, case_state=case_state,
                                  sent=sent, error=error)
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
                self._outbox(complaint.complaint_id, run.run_id, "resolution", run.reply_text,
                             int(d.refund_amount_myr * 100), "auto", now)
        return self.get_case(complaint.complaint_id)

    def _insert_case(self, complaint: Complaint, digest: str, status: str, now: str, *, run_id: str | None = None,
                     case_state: str | None = None, sent: bool = False, error: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO cases (complaint_id, customer_id, received_at, channel, subject, text, content_hash,"
            " autonomous_run_id, current_run_id, status, case_state, sent, error, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?, ?,?, ?,?,?,?, ?,?)",
            (complaint.complaint_id, complaint.customer_id, f"{complaint.received_at:%Y-%m-%d %H:%M}",
             complaint.channel, complaint.subject, complaint.text, digest,
             run_id, run_id, status, case_state, int(sent), error, now, now),
        )

    def register(self, complaint: Complaint) -> tuple[dict[str, Any], bool]:
        """Store a new complaint as processing before the pipeline runs. Returns (case, created).
        The same complaint again returns the existing case untouched; different content raises CaseConflict."""
        existing = self.get_case(complaint.complaint_id)
        if existing:
            if existing["content_hash"] != content_hash(complaint):
                raise CaseConflict(f"{complaint.complaint_id} already exists with different content")
            return existing, False
        with self.conn:
            self._insert_case(complaint, content_hash(complaint), "processing", _now())
            self._event(complaint.complaint_id, "ingest", None, None)
        return self.get_case(complaint.complaint_id), True

    # --- human actions (docs/api.md) ---

    def act(self, complaint_id: str, action: str, actor: str, reason: str = "", reply_text: str | None = None,
            *, check: Callable[[str, EngineResult], CheckResult]) -> dict[str, Any]:
        """approve / reject / edit_approve a case awaiting approval. The agent's run is never changed."""
        case = self._require(complaint_id)
        actor, reason = (actor or "").strip(), (reason or "").strip()
        if action not in ACTIONS:
            raise InvalidAction(f"unknown action {action!r}; use {', '.join(ACTIONS)}")
        if not actor:
            raise InvalidAction("actor is required")
        if action in ("reject", "edit_approve") and not reason:
            raise InvalidAction(f"reason is required for {action}")
        if action == "edit_approve" and not (reply_text or "").strip():
            raise InvalidAction("reply_text is required for edit_approve")
        if case["case_state"] != "awaiting_approval":
            raise WrongState(f"{complaint_id} is {case['case_state'] or case['status']}, not awaiting_approval")

        run = self.run(case["autonomous_run_id"])
        reply = run.reply_text
        if action == "edit_approve":
            result = check(reply_text, EngineResult(match=run.match, decision=run.decision, evidence=run.evidence))
            if not result.passed:
                with self.conn:
                    self._event(complaint_id, "edit_approve_refused", run.run_id,
                                {"reason": reason, "problems": result.problems, "reply_text": reply_text}, actor=actor)
                raise ReplyRefused(result.problems)
            reply = reply_text.strip()

        approved, now = action != "reject", _now()
        human_action = {"action": action, "actor": actor, "reason": reason, "at": now,
                        "reply_text": reply if approved else None}
        with self.conn:
            self.conn.execute(
                "UPDATE cases SET case_state=?, sent=?, human_action=?, updated_at=? WHERE complaint_id=?",
                ("approved" if approved else "rejected", int(approved), json.dumps(human_action), now, complaint_id))
            if approved:
                self._outbox(complaint_id, run.run_id, "resolution", reply,
                             int(run.decision.refund_amount_myr * 100), actor, now)
            self._event(complaint_id, action, run.run_id,
                        {"reason": reason, "self_check": "passed" if action == "edit_approve" else None}, actor=actor)
        return self.get_case(complaint_id)

    def acknowledge(self, complaint_id: str, actor: str, reason: str = "") -> dict[str, Any]:
        """A fraud analyst releases the agent's holding reply. The case stays with the fraud team."""
        case = self._require(complaint_id)
        actor = (actor or "").strip()
        if not actor:
            raise InvalidAction("actor is required")
        if case["case_state"] != "with_fraud_team" or case["sent"]:
            raise WrongState(f"{complaint_id} is not a fraud case waiting for acknowledgement")
        run, now = self.run(case["autonomous_run_id"]), _now()
        human_action = {"action": "acknowledge", "actor": actor, "reason": (reason or "").strip(), "at": now,
                        "reply_text": run.reply_text}
        with self.conn:
            self.conn.execute("UPDATE cases SET sent=1, human_action=?, updated_at=? WHERE complaint_id=?",
                              (json.dumps(human_action), now, complaint_id))
            self._outbox(complaint_id, run.run_id, "holding_reply", run.reply_text, 0, actor, now)
            self._event(complaint_id, "acknowledge", run.run_id, {"reason": human_action["reason"]}, actor=actor)
        return self.get_case(complaint_id)

    def _require(self, complaint_id: str) -> dict[str, Any]:
        case = self.get_case(complaint_id)
        if case is None:
            raise NotFound(complaint_id)
        if case["status"] != "done":
            raise WrongState(f"{complaint_id} is {case['status']}")
        return case

    def _outbox(self, complaint_id: str, run_id: str, kind: str, reply: str, refund_sen: int, by: str, now: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO outbound_messages"
            " (complaint_id, run_id, kind, reply_text, refund_sen, authorised_by, status, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (complaint_id, run_id, kind, reply, refund_sen, by, "sent", now))

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

    def processing_ids(self) -> list[str]:
        return [r[0] for r in self.conn.execute("SELECT complaint_id FROM cases WHERE status = 'processing'")]

    def complaint(self, complaint_id: str) -> Complaint | None:
        case = self.get_case(complaint_id)
        return Complaint(**{k: case[k] for k in ("complaint_id", "customer_id", "received_at", "channel", "subject",
                                                 "text")}) if case else None

    def case_view(self, complaint_id: str) -> dict[str, Any] | None:
        """GET /cases/{id} in docs/api.md's shape. The decision always comes from the autonomous run."""
        case = self.get_case(complaint_id)
        if case is None:
            return None
        if case["status"] == "processing":
            return {"complaint_id": complaint_id, "status": "processing"}
        if case["status"] == "error":
            return {"complaint_id": complaint_id, "status": "error", "error": case["error"]}
        run = self.run(case["autonomous_run_id"])
        return {
            **run.prediction_row(),
            "status": "done",
            "self_check": "passed" if run.self_check and run.self_check.passed else "flagged",
            "case_state": case["case_state"],
            "sent": bool(case["sent"]),
            "human_action": json.loads(case["human_action"]) if case["human_action"] else None,
            "hold_reason": run.decision.hold_reason,
        }

    def human_acted(self, complaint_id: str) -> bool:
        return self.conn.execute("SELECT 1 FROM case_events WHERE complaint_id = ? AND actor != 'agent' LIMIT 1",
                                 (complaint_id,)).fetchone() is not None
