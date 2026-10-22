"""Read-only queries behind the UI's /api routes (queues, case detail, metrics, audit). Owner: Dev B.

Every function takes the store's connection and returns JSON-ready dicts. Nothing here writes.
Formats (docs/UI_API.md): money "550.00", cost "0.0021", datetimes ISO 8601 MYT with no offset.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sqlite3
from collections import Counter
from decimal import Decimal
from typing import Any, get_args

from backend.agent.tools import get_auto_refund_limit
from backend.contracts import AgentRun, Category, HoldReason, Outcome, Priority, Route, parse_date, parse_myt
from backend.db.store import run_cost

QUEUES = ("processing", "error", "auto_resolved", "awaiting_approval", "with_fraud_team", "approved", "rejected")
OPEN_QUEUES = ("awaiting_approval", "with_fraud_team")
HOLD_TEXT = {
    "customer_not_found": "Customer not found",
    "ambiguous_match": "Ambiguous match",
    "no_match": "No matching transaction",
    "category_revised": "Category revised",
    "self_check_failed": "Self-check failed",
    "unknown_auth_method": "Unknown authentication method",
    "llm_error": "Language model unavailable",
}
FILTERS = {  # list filter -> allowed values
    "queue": QUEUES,
    "route": get_args(Route),
    "category": get_args(Category),
    "priority": get_args(Priority),
    "hold_reason": (*get_args(HoldReason), "none"),
}
HUMAN_ACTIONS = ("approve", "reject", "edit_approve", "acknowledge")


class BadQuery(ValueError):
    """A filter or date the API should answer with 422."""


# --- formats ---

def iso(value: str | None) -> str | None:
    """Any stored datetime ("2026-09-30 14:05", "...:00", ISO) as ISO with seconds."""
    return parse_myt(value).isoformat() if value else None


def money(sen: int | None) -> str | None:
    return None if sen is None else f"{Decimal(sen) / 100:.2f}"


def cost(value: Decimal | str | None) -> str | None:
    return None if value is None else f"{Decimal(value):.4f}"


def when(value: str, *, end_of_day: bool = False) -> dt.datetime:
    """A query-string date or datetime. A bare date means the start of that day (or its end)."""
    try:
        return parse_myt(value)
    except ValueError:
        pass
    try:
        day = parse_date(value)
    except ValueError as exc:
        raise BadQuery(str(exc)) from exc
    return dt.datetime.combine(day, dt.time.max.replace(microsecond=0) if end_of_day else dt.time.min)


def split(name: str, raw: str | None) -> list[str]:
    """"a,b" -> ["a", "b"], checked against the allowed values."""
    values = [v.strip() for v in (raw or "").split(",") if v.strip()]
    bad = [v for v in values if v not in FILTERS[name]]
    if bad:
        raise BadQuery(f"unknown {name} {', '.join(bad)}; use {', '.join(FILTERS[name])}")
    return values


def limit_text() -> str:
    limit = get_auto_refund_limit()
    return f"RM{limit:,.0f}" if limit == limit.to_integral_value() else f"RM{limit:,.2f}"


def waiting_reason(queue: str, hold_reason: str | None, outcome: str | None) -> str | None:
    """Why the case is in its queue, for staff. Closed cases aren't waiting."""
    hold = HOLD_TEXT.get(hold_reason) if hold_reason else None
    if queue == "processing":
        return "Agent is working on it"
    if queue == "error":
        return "Agent error"
    if queue == "with_fraud_team":
        return "Fraud investigation" + (f" · {hold}" if hold else "")
    if queue == "awaiting_approval":
        if hold:
            return hold
        return {"REFUND": f"Refund over {limit_text()}", "DECLINE": "Decline needs approval"}.get(outcome,
                                                                                                    "Needs approval")
    return None


def _json(text: str | None) -> Any:
    return json.loads(text) if text else None


def _percentile(sorted_values: list, pct: float):
    """Nearest rank."""
    return sorted_values[max(0, math.ceil(pct / 100 * len(sorted_values)) - 1)] if sorted_values else None


def _rate(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


# --- queues ---

CASE_ROWS = """
SELECT c.complaint_id, c.customer_id, c.received_at, c.channel, c.subject, c.status, c.case_state, c.sent,
       c.human_action, c.updated_at, COALESCE(c.case_state, c.status) AS queue,
       r.category, r.outcome, r.refund_sen, r.priority, r.route, r.hold_reason, r.self_check,
       json_extract(r.run_json, '$.decision.vulnerable') AS vulnerable,
       json_extract(r.run_json, '$.decision.resolve_due_at') AS resolve_due_at,
       json_extract(r.run_json, '$.evidence.customer.full_name') AS customer_name,
       (SELECT MAX(e.id) FROM case_events e WHERE e.complaint_id = c.complaint_id) AS last_event_id
FROM cases c LEFT JOIN agent_runs r ON r.run_id = c.autonomous_run_id
"""
ORDER = {
    "priority": "CASE priority WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 ELSE 4 END,"
                " resolve_due_at IS NULL, resolve_due_at, received_at, complaint_id",
    "recent": "last_event_id DESC, complaint_id",
}


def queue_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts = dict.fromkeys(QUEUES, 0)
    for queue, n in conn.execute("SELECT COALESCE(case_state, status), COUNT(*) FROM cases GROUP BY 1"):
        counts[queue] = n
    return counts


def _item(row: sqlite3.Row) -> dict[str, Any]:
    acted = _json(row["human_action"])
    return {
        "complaint_id": row["complaint_id"],
        "customer_id": row["customer_id"],
        "customer_name": row["customer_name"],
        "received_at": iso(row["received_at"]),
        "channel": row["channel"],
        "subject": row["subject"],
        "status": row["status"],
        "queue": row["queue"],
        "case_state": row["case_state"],
        "sent": bool(row["sent"]),
        "category": row["category"],
        "outcome": row["outcome"],
        "refund_amount_myr": money(row["refund_sen"]),
        "priority": row["priority"],
        "route": row["route"],
        "hold_reason": row["hold_reason"],
        "self_check": row["self_check"],
        "vulnerable": None if row["vulnerable"] is None else bool(row["vulnerable"]),
        "resolve_due_at": iso(row["resolve_due_at"]),
        "waiting_reason": waiting_reason(row["queue"], row["hold_reason"], row["outcome"]),
        "human_action": acted and {k: acted.get(k) for k in ("action", "actor", "at")},
        "updated_at": iso(row["updated_at"]),
    }


def list_cases(conn: sqlite3.Connection, *, queue: str | None = None, route: str | None = None,
               category: str | None = None, priority: str | None = None, hold_reason: str | None = None,
               q: str | None = None, sort: str = "priority", limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """GET /api/cases. Raises BadQuery for an unknown filter value."""
    where, args = [], []
    for name, raw in (("queue", queue), ("route", route), ("category", category), ("priority", priority),
                      ("hold_reason", hold_reason)):
        values = split(name, raw)
        if not values:
            continue
        named = [v for v in values if v != "none"]
        parts = [f"{name} IN ({','.join('?' * len(named))})"] if named else []
        if "none" in values:
            parts.append(f"{name} IS NULL")
        where.append("(" + " OR ".join(parts) + ")")
        args += named
    if q and q.strip():
        where.append("(" + " OR ".join(f"instr(lower(COALESCE({col}, '')), ?) > 0"
                                       for col in ("complaint_id", "customer_id", "customer_name", "subject")) + ")")
        args += [q.strip().lower()] * 4
    if sort not in ORDER:
        raise BadQuery(f"unknown sort {sort}; use {', '.join(ORDER)}")

    base = f"SELECT * FROM ({CASE_ROWS})" + (" WHERE " + " AND ".join(where) if where else "")
    total = conn.execute(f"SELECT COUNT(*) FROM ({base})", args).fetchone()[0]
    rows = conn.execute(f"{base} ORDER BY {ORDER[sort]} LIMIT ? OFFSET ?", [*args, limit, offset]).fetchall()
    return {"total": total, "limit": limit, "offset": offset, "counts": queue_counts(conn),
            "items": [_item(r) for r in rows]}


# --- one case ---

def _usage(usage) -> dict[str, Any]:
    return {**usage.model_dump(mode="json"), "cost_myr": cost(usage.cost_myr)}


def case_detail(conn: sqlite3.Connection, complaint_id: str) -> dict[str, Any] | None:
    """GET /api/cases/{id}: the whole decision trail, from the autonomous run. None when unknown."""
    case = conn.execute("SELECT *, COALESCE(case_state, status) AS queue FROM cases WHERE complaint_id = ?",
                        (complaint_id,)).fetchone()
    if case is None:
        return None
    run_row = conn.execute("SELECT run_json, latency_ms FROM agent_runs WHERE run_id = ?",
                           (case["autonomous_run_id"],)).fetchone() if case["autonomous_run_id"] else None
    run = AgentRun.model_validate_json(run_row["run_json"]) if run_row else None
    d = run.decision if run else None
    ev = run.evidence if d else None

    detail: dict[str, Any] = {
        "case": {
            "complaint_id": complaint_id,
            "status": case["status"],
            "queue": case["queue"],
            "case_state": case["case_state"],
            "sent": bool(case["sent"]),
            "error": case["error"],
            "waiting_reason": waiting_reason(case["queue"], d and d.hold_reason, d and d.outcome),
            "human_action": _json(case["human_action"]),
            "autonomous_run_id": case["autonomous_run_id"],
            "current_run_id": case["current_run_id"],
            "created_at": iso(case["created_at"]),
            "updated_at": iso(case["updated_at"]),
        },
        "complaint": {"customer_id": case["customer_id"], "received_at": iso(case["received_at"]),
                      "channel": case["channel"], "subject": case["subject"], "text": case["text"]},
        "customer": None, "clues": None, "match": None, "decision": None, "evidence": None, "reply": None,
        "usage": None,
    }
    if d is not None:
        evidence = ev.model_dump(mode="json")
        customer = evidence.pop("customer")
        accounts = evidence.pop("accounts")
        detail.update({
            "customer": customer and {**customer, "accounts": accounts},
            "clues": run.clues.model_dump(mode="json") if run.clues else None,
            "match": run.match.model_dump(mode="json") if run.match else None,
            "decision": {**d.model_dump(mode="json"), "refund_amount_myr": f"{d.refund_amount_myr:.2f}"},
            "evidence": evidence,
            "reply": {"text": run.reply_text, "redraft_count": run.redraft_count,
                      "self_check": run.self_check.model_dump(mode="json") if run.self_check else None},
            "usage": {"cost_myr": cost(run_cost(run)), "latency_ms": run_row["latency_ms"],
                      "prompt_version": run.prompt_version, "schema_version": run.schema_version,
                      "policy_version": run.policy_version, "extract": _usage(run.extract_usage),
                      "draft": [_usage(u) for u in run.draft_usage]},
        })

    runs = conn.execute("SELECT run_id, run_kind, created_at, route, outcome, hold_reason, cost_myr, latency_ms"
                        " FROM agent_runs WHERE complaint_id = ? ORDER BY created_at, rowid", (complaint_id,))
    detail["runs"] = [{**dict(r), "created_at": iso(r["created_at"]), "cost_myr": cost(r["cost_myr"])} for r in runs]
    events = conn.execute("SELECT * FROM case_events WHERE complaint_id = ? ORDER BY id", (complaint_id,))
    detail["events"] = [_event(e) for e in events]
    outbound = conn.execute("SELECT * FROM outbound_messages WHERE complaint_id = ? ORDER BY id", (complaint_id,))
    detail["outbound"] = [{"kind": m["kind"], "reply_text": m["reply_text"], "refund_amount_myr": money(m["refund_sen"]),
                           "authorised_by": m["authorised_by"], "status": m["status"],
                           "created_at": iso(m["created_at"])} for m in outbound]
    return detail


def _event(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "complaint_id": row["complaint_id"], "actor": row["actor"], "action": row["action"],
            "run_id": row["run_id"], "detail": _json(row["detail"]), "created_at": iso(row["created_at"])}


# --- dashboard ---

METRIC_ROWS = """
SELECT COALESCE(c.case_state, c.status) AS queue, r.route, r.category, r.priority, r.outcome, r.hold_reason,
       r.cost_myr, r.latency_ms, r.created_at AS run_at, r.extract_model,
       json_extract(r.run_json, '$.redraft_count') AS redrafts,
       json_extract(r.run_json, '$.draft_usage[0].provider') || ':' ||
       json_extract(r.run_json, '$.draft_usage[0].model') AS draft_model,
       json_extract(r.run_json, '$.decision.resolve_due_at') AS due
FROM cases c LEFT JOIN agent_runs r ON r.run_id = c.autonomous_run_id
"""


def _tally(rows: list, field: str, keys: tuple) -> dict[str, int]:
    counts = dict.fromkeys(keys, 0)
    counts.update(Counter(r[field] for r in rows if r[field] is not None))
    return counts


def metrics(conn: sqlite3.Connection, as_of: dt.datetime) -> dict[str, Any]:
    """GET /api/metrics over every case and its autonomous run."""
    rows = conn.execute(METRIC_ROWS).fetchall()
    decided = [r for r in rows if r["outcome"] is not None]
    ran = [r for r in rows if r["cost_myr"] is not None]
    actions = dict(conn.execute("SELECT action, COUNT(*) FROM case_events GROUP BY action").fetchall())
    human = {"approved": actions.get("approve", 0), "rejected": actions.get("reject", 0),
             "edited_and_approved": actions.get("edit_approve", 0), "acknowledged": actions.get("acknowledge", 0)}
    decided_by_people = human["approved"] + human["rejected"] + human["edited_and_approved"]

    open_due = [parse_myt(r["due"]) if r["due"] else None for r in rows if r["queue"] in OPEN_QUEUES]
    costs = sorted(Decimal(r["cost_myr"]) for r in ran)
    latencies = sorted(r["latency_ms"] for r in ran)
    run_times = sorted(parse_myt(r["run_at"]) for r in decided)
    hours = (run_times[-1] - run_times[0]).total_seconds() / 3600 if len(run_times) > 1 else 0
    total_cost = sum((Decimal(v) for (v,) in conn.execute("SELECT cost_myr FROM agent_runs")), Decimal("0"))
    holds = _tally(decided, "hold_reason", get_args(HoldReason))

    return {
        "cases": {
            "total": len(rows),
            "by_queue": _tally(rows, "queue", QUEUES),
            "by_route": _tally(decided, "route", get_args(Route)),
            "by_category": _tally(decided, "category", get_args(Category)),
            "by_priority": _tally(decided, "priority", get_args(Priority)),
            "by_outcome": _tally(decided, "outcome", get_args(Outcome)),
        },
        "auto_resolve_rate": _rate(sum(r["queue"] == "auto_resolved" for r in decided), len(decided)),
        "holds": {"total": sum(holds.values()), "by_reason": holds},
        "self_check": {
            "first_draft_failed": sum((r["redrafts"] or 0) > 0 for r in decided),
            "held_self_check_failed": holds["self_check_failed"],
            "human_edits_refused": actions.get("edit_approve_refused", 0),
        },
        "human": {**human, "override_rate": _rate(human["rejected"] + human["edited_and_approved"], decided_by_people)},
        "sla": {
            "as_of": as_of.isoformat(),
            "open": len(open_due),
            "overdue": sum(1 for due in open_due if due and due < as_of),
            "due_within_24h": sum(1 for due in open_due if due and as_of <= due < as_of + dt.timedelta(hours=24)),
        },
        "cost_myr": {
            "total": cost(total_cost),
            "mean": cost(sum(costs) / len(costs)) if costs else None,
            "p50": cost(_percentile(costs, 50)),
            "p95": cost(_percentile(costs, 95)),
            "max": cost(costs[-1]) if costs else None,
        },
        "latency_ms": {
            "mean": round(sum(latencies) / len(latencies)) if latencies else None,
            "p50": _percentile(latencies, 50),
            "p95": _percentile(latencies, 95),
            "max": latencies[-1] if latencies else None,
        },
        "models": {
            "extract": dict(Counter(r["extract_model"] for r in ran if r["extract_model"])),
            "draft": dict(Counter(r["draft_model"] or "none" for r in ran)),
        },
        "throughput": {
            "decided": len(decided),
            "first_at": run_times[0].isoformat() if run_times else None,
            "last_at": run_times[-1].isoformat() if run_times else None,
            "per_hour": round(len(decided) / hours, 1) if hours else None,
        },
    }


# --- audit log ---

def audit(conn: sqlite3.Connection, *, actor: str | None = None, action: str | None = None,
          complaint_id: str | None = None, since: str | None = None, until: str | None = None,
          people_only: bool = False, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    """GET /api/audit, newest first. Raises BadQuery for a bad date."""
    where, args = [], []
    if actor:
        where.append("actor = ?")
        args.append(actor)
    actions = [a.strip() for a in (action or "").split(",") if a.strip()]
    if actions:
        where.append(f"action IN ({','.join('?' * len(actions))})")
        args += actions
    if complaint_id:
        where.append("complaint_id = ?")
        args.append(complaint_id)
    if since:
        where.append("created_at >= ?")
        args.append(f"{when(since):%Y-%m-%d %H:%M:%S}")
    if until:
        where.append("created_at <= ?")
        args.append(f"{when(until, end_of_day=True):%Y-%m-%d %H:%M:%S}")
    if people_only:
        where.append("actor != 'agent'")
    clause = " WHERE " + " AND ".join(where) if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM case_events{clause}", args).fetchone()[0]
    rows = conn.execute(f"SELECT * FROM case_events{clause} ORDER BY id DESC LIMIT ? OFFSET ?", [*args, limit, offset])
    facets = {"actors": [a for (a,) in conn.execute("SELECT DISTINCT actor FROM case_events ORDER BY actor")],
              "actions": [a for (a,) in conn.execute("SELECT DISTINCT action FROM case_events ORDER BY action")]}
    return {"total": total, "limit": limit, "offset": offset, "facets": facets, "items": [_event(r) for r in rows]}
