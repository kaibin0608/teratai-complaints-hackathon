"""Bonus platform workflow: who may do what to a case, two-tier approval, fraud steps, send back. Owner: Dev B.

Rules (docs/bonus_platform.md, PLAN.md "Roles"):
- A case's team is its current run's route: HUMAN_APPROVAL (officers) or FRAUD_TEAM (fraud analysts).
  The manager acts on every team and has no limit.
- First tier clears a case only within its limit and when it isn't sensitive; otherwise it escalates and the case
  waits for the manager. Limits: officers on the refund, analysts on the disputed transaction.
- Sensitive: the customer is 65+ on received_at (decision.vulnerable), or someone flagged it with a reason.
- Every customer message goes through CaseStore.send (the one gate); every action appends a case_events row;
  agent_runs never change.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Callable

from backend.agent.reply_rules import combined_check
from backend.auth.users import User, get_user
from backend.contracts import AgentRun, CheckResult, EngineResult
from backend.db.store import CaseStore, InvalidAction, WrongState, _now, engine_result

TEAM_OF_ROLE = {"officer": "HUMAN_APPROVAL", "fraud": "FRAUD_TEAM"}
FRAUD_OUTCOMES = ("confirmed_fraud", "not_fraud", "recall_succeeded", "recall_failed")
INVESTIGATION_KINDS = ("investigation", "recall_attempt")
VULNERABLE_REASON = "Customer aged 65+"


class Forbidden(Exception):
    """HTTP 403. With `why`, the case needs the manager (over the limit or sensitive)."""

    def __init__(self, error: str, why: str | None = None, **info: Any):
        super().__init__(why or error)
        self.error, self.why, self.info = error, why, info


def _json(text: str | None) -> Any:
    return json.loads(text) if text else None


def _required(value: str | None, what: str) -> str:
    value = (value or "").strip()
    if not value:
        raise InvalidAction(f"{what} is required")
    return value


def team(run: AgentRun) -> str | None:
    return run.decision.route if run.decision and run.decision.route != "AUTO_RESOLVE" else None


def sensitive_reason(case: dict[str, Any], run: AgentRun | None) -> str | None:
    if case.get("sensitive_reason"):
        return case["sensitive_reason"]
    return VULNERABLE_REASON if run and run.decision and run.decision.vulnerable else None


def limit_amount(run: AgentRun) -> tuple[Decimal, str]:
    """What a first-tier limit is measured on: the refund (approval) or the disputed transaction (fraud)."""
    if run.decision.route == "FRAUD_TEAM":
        txn = run.evidence.matched_txn if run.evidence else None
        return Decimal(str(txn["amount_myr"])) if txn else Decimal("0"), "disputed transaction"
    return run.decision.refund_amount_myr, "refund"


class Workflow:
    def __init__(self, store: CaseStore, check: Callable[[str, EngineResult], CheckResult] = combined_check):
        self.store, self.check = store, check

    # --- shared checks ---

    def _load(self, complaint_id: str, user: User, *, team_needed: str | None = None) -> tuple[dict, AgentRun]:
        """The case and its current run, after the team and assignee checks."""
        case = self.store._require(complaint_id)  # NotFound, or WrongState while processing / after an error
        run = self.store.current_run(case)
        case_team = team(run)
        if user.role != "manager":
            if TEAM_OF_ROLE.get(user.role) != case_team:
                raise Forbidden("this case belongs to another team")
            if case["assigned_to"] and case["assigned_to"] != user.username:
                raise Forbidden(f"this case is assigned to {case['assigned_to']}")
        if team_needed and case_team != team_needed:
            raise WrongState(f"{complaint_id} is not a {'fraud' if team_needed == 'FRAUD_TEAM' else 'approval'} case")
        return case, run

    @staticmethod
    def _state(case: dict, case_state: str, workflow: str | None = None) -> None:
        if case["case_state"] != case_state or case["workflow"] != workflow:
            now = case["workflow"] or case["case_state"]
            raise WrongState(f"{case['complaint_id']} is {now}")

    def limit_check(self, user: User, case: dict, run: AgentRun) -> None:
        """First tier only clears what is within its limit and not sensitive."""
        if user.role == "manager":
            return
        amount, basis = limit_amount(run)
        limit = user.limit_myr
        info = {"limit": None if limit is None else f"{limit:.2f}", "amount": f"{amount:.2f}"}
        reason = sensitive_reason(case, run)
        if reason:
            raise Forbidden("escalate to a manager", f"sensitive: {reason}", **info)
        if limit is not None and amount > limit:
            raise Forbidden("escalate to a manager", f"{basis} RM{amount:,.2f} is over your limit RM{limit:,.2f}",
                            **info)

    def _reply(self, case: dict, run: AgentRun) -> tuple[str, CheckResult, bool]:
        """The reply to send: the saved edit if there is one, else the agent's. Checked again now."""
        draft = _json(case["draft_reply"])
        if draft:
            return draft["text"], self.check(draft["text"], engine_result(run)), True
        return run.reply_text, run.self_check, False

    def _touch(self, complaint_id: str, action: str, user: User, run_id: str | None, detail: dict,
               **columns: Any) -> None:
        """Update case columns (if any) and append the event, in one transaction."""
        sets = "".join(f"{name}=?, " for name in columns)
        with self.store.conn:
            self.store.conn.execute(f"UPDATE cases SET {sets}updated_at=? WHERE complaint_id=?",
                                    (*columns.values(), _now(), complaint_id))
            self.store._event(complaint_id, action, run_id, detail, actor=user.username)

    # --- approval team ---

    def approve(self, complaint_id: str, user: User, reason: str = "") -> None:
        case, run = self._load(complaint_id, user, team_needed="HUMAN_APPROVAL")
        self._state(case, "awaiting_approval")
        self.limit_check(user, case, run)
        reply, checked, edited = self._reply(case, run)
        self.store.resolve(case, run, "approve", user.username, (reason or "").strip(), reply, checked,
                           detail={"edited": edited})

    def reject(self, complaint_id: str, user: User, reason: str) -> None:
        reason = _required(reason, "reason")
        case, run = self._load(complaint_id, user, team_needed="HUMAN_APPROVAL")
        self._state(case, "awaiting_approval")
        self.store.resolve(case, run, "reject", user.username, reason, None, None)

    def edit_reply(self, complaint_id: str, user: User, reply_text: str, reason: str) -> CheckResult:
        """Save an edited reply with its self-check result. Approve stays locked while it fails."""
        text, reason = _required(reply_text, "reply_text"), _required(reason, "reason")
        case, run = self._load(complaint_id, user, team_needed="HUMAN_APPROVAL")
        if not (case["case_state"] == "awaiting_approval"
                and (case["workflow"] is None or (case["workflow"] == "escalated" and user.role == "manager"))):
            raise WrongState(f"{complaint_id} is {case['workflow'] or case['case_state']}")
        checked = self.check(text, engine_result(run))
        old = (_json(case["draft_reply"]) or {}).get("text", run.reply_text)
        result = "passed" if checked.passed else "flagged"
        draft = {"text": text, "self_check": result, "problems": checked.problems, "by": user.username, "at": _now()}
        self._touch(complaint_id, "edit_reply", user, run.run_id,
                    {"old": old, "new": text, "reason": reason, "self_check": result, "problems": checked.problems},
                    draft_reply=json.dumps(draft))
        return checked

    def send_back(self, complaint_id: str, user: User, note: str) -> str:
        """Mark the case for an agent re-run with the officer's note. Returns the note; AgentService runs it."""
        note = _required(note, "note")
        case, run = self._load(complaint_id, user, team_needed="HUMAN_APPROVAL")
        self._state(case, "awaiting_approval")
        self._touch(complaint_id, "send_back", user, run.run_id, {"note": note}, workflow="reprocessing")
        return note

    # --- both teams ---

    def escalate(self, complaint_id: str, user: User, reason: str, outcome: str | None = None) -> None:
        reason = _required(reason, "reason")
        if user.role == "manager":
            raise Forbidden("the manager decides directly; escalation is for the first tier")
        case, run = self._load(complaint_id, user)
        if team(run) == "FRAUD_TEAM":
            self._state(case, "with_fraud_team", "investigating")
            if outcome not in FRAUD_OUTCOMES:
                raise InvalidAction(f"outcome is required to escalate a fraud case; use {', '.join(FRAUD_OUTCOMES)}")
            proposal = {"action": "record_outcome", "outcome": outcome}
        else:
            self._state(case, "awaiting_approval")
            reply, checked, edited = self._reply(case, run)
            proposal = {"action": "approve", "reply_text": reply, "edited": edited,
                        "self_check": "passed" if checked and checked.passed else "flagged"}
        escalation = {"by": user.username, "at": _now(), "reason": reason, "proposal": proposal}
        self._touch(complaint_id, "escalate", user, run.run_id, {"reason": reason, "proposal": proposal},
                    workflow="escalated", escalation=json.dumps(escalation))

    def flag_sensitive(self, complaint_id: str, user: User, reason: str) -> None:
        reason = _required(reason, "reason")
        case, run = self._load(complaint_id, user)
        if case["case_state"] not in ("awaiting_approval", "with_fraud_team") or case["workflow"] == "closed":
            raise WrongState(f"{complaint_id} is already closed")
        if case["sensitive_reason"]:
            raise WrongState(f"{complaint_id} is already flagged sensitive")
        self._touch(complaint_id, "flag_sensitive", user, run.run_id, {"reason": reason}, sensitive_reason=reason)

    # --- manager ---

    def second_tier(self, complaint_id: str, user: User, approve: bool, reason: str) -> None:
        reason = _required(reason, "reason")
        if user.role != "manager":
            raise Forbidden("only the manager decides escalations")
        case, run = self._load(complaint_id, user)
        if case["workflow"] != "escalated":
            raise WrongState(f"{complaint_id} is not escalated")
        escalation = _json(case["escalation"])
        action = "second_tier_approve" if approve else "second_tier_reject"
        detail = {"escalated_by": escalation["by"], "proposal": escalation["proposal"]}
        if team(run) == "FRAUD_TEAM":
            if approve:
                outcome = {"outcome": escalation["proposal"]["outcome"], "by": user.username, "at": _now(),
                           "reason": reason, "proposed_by": escalation["by"]}
                self._touch(complaint_id, action, user, run.run_id, {"reason": reason, **detail},
                            workflow="closed", fraud_outcome=json.dumps(outcome))
            else:  # back to the analyst
                self._touch(complaint_id, action, user, run.run_id, {"reason": reason, **detail},
                            workflow="investigating")
            return
        if approve:
            reply, checked, _ = self._reply(case, run)  # the manager may have edited it while escalated
            self.store.resolve(case, run, action, user.username, reason, reply, checked, second_tier=True,
                               workflow="closed", detail=detail)
        else:
            self.store.resolve(case, run, action, user.username, reason, None, None, workflow="closed",
                               detail=detail)

    def reassign(self, complaint_id: str, user: User, username: str, reason: str = "") -> None:
        if user.role != "manager":
            raise Forbidden("only the manager reassigns cases")
        case, run = self._load(complaint_id, user)
        target = get_user(self.store.conn, (username or "").strip())
        if target is None:
            raise InvalidAction(f"unknown user {username!r}")
        if target.role != "manager" and TEAM_OF_ROLE.get(target.role) != team(run):
            raise InvalidAction(f"{target.username} ({target.role}) can't work on this case's team")
        self._touch(complaint_id, "reassign", user, run.run_id,
                    {"from": case["assigned_to"], "to": target.username, "reason": (reason or "").strip()},
                    assigned_to=target.username)

    # --- fraud team ---

    def acknowledge(self, complaint_id: str, user: User, reason: str = "") -> None:
        self._load(complaint_id, user, team_needed="FRAUD_TEAM")
        self.store.acknowledge(complaint_id, user.username, reason)

    def investigate(self, complaint_id: str, user: User, note: str, kind: str = "investigation") -> None:
        note = _required(note, "note")
        if kind not in INVESTIGATION_KINDS:
            raise InvalidAction(f"unknown kind {kind!r}; use {', '.join(INVESTIGATION_KINDS)}")
        case, run = self._load(complaint_id, user, team_needed="FRAUD_TEAM")
        self._state(case, "with_fraud_team", "investigating")
        self._touch(complaint_id, "investigate", user, run.run_id, {"kind": kind, "note": note})

    def record_outcome(self, complaint_id: str, user: User, outcome: str, reason: str) -> None:
        reason = _required(reason, "reason")
        if outcome not in FRAUD_OUTCOMES:
            raise InvalidAction(f"unknown outcome {outcome!r}; use {', '.join(FRAUD_OUTCOMES)}")
        case, run = self._load(complaint_id, user, team_needed="FRAUD_TEAM")
        self._state(case, "with_fraud_team", "investigating")
        self.limit_check(user, case, run)
        record = {"outcome": outcome, "by": user.username, "at": _now(), "reason": reason}
        self._touch(complaint_id, "record_outcome", user, run.run_id, {"outcome": outcome, "reason": reason},
                    workflow="closed", fraud_outcome=json.dumps(record))
