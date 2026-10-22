"""SQLite schema. agent_runs and case_events are append-only, enforced by triggers in the database itself.

agent_runs holds what the agent decided on its own (what predictions.csv exports); cases holds where the case is
now. Money columns are integer sen.
"""
from __future__ import annotations

import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id          TEXT PRIMARY KEY,
    complaint_id    TEXT NOT NULL,
    run_kind        TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    category        TEXT,
    matched_txn_id  TEXT,
    outcome         TEXT,
    refund_sen      INTEGER,
    priority        TEXT,
    reply_language  TEXT,
    route           TEXT,
    hold_reason     TEXT,
    self_check      TEXT,            -- passed | flagged | NULL (no decision)
    error           TEXT,
    extract_model   TEXT,
    prompt_version  TEXT,
    schema_version  TEXT,
    cost_myr        TEXT NOT NULL,   -- decimal string: tiny amounts keep their precision
    latency_ms      INTEGER NOT NULL,
    run_json        TEXT NOT NULL    -- the full AgentRun; the source of truth
);
CREATE INDEX IF NOT EXISTS agent_runs_complaint ON agent_runs (complaint_id);

CREATE TABLE IF NOT EXISTS cases (
    complaint_id      TEXT PRIMARY KEY,
    customer_id       TEXT NOT NULL,
    received_at       TEXT NOT NULL,
    channel           TEXT NOT NULL,
    subject           TEXT NOT NULL,
    text              TEXT NOT NULL,
    content_hash      TEXT NOT NULL,
    autonomous_run_id TEXT REFERENCES agent_runs (run_id),
    current_run_id    TEXT REFERENCES agent_runs (run_id),
    status            TEXT NOT NULL,  -- processing | done | error (docs/api.md)
    case_state        TEXT,           -- auto_resolved | awaiting_approval | with_fraud_team | approved | rejected
    sent              INTEGER NOT NULL DEFAULT 0,
    error             TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    human_action      TEXT            -- JSON {action, actor, reason, at, reply_text}; NULL until a person acts
);

CREATE TABLE IF NOT EXISTS case_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id TEXT NOT NULL,
    actor        TEXT NOT NULL,       -- "agent" or a person
    action       TEXT NOT NULL,       -- ingest | agent_run | approve | ...
    run_id       TEXT,
    detail       TEXT,
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS case_events_complaint ON case_events (complaint_id);

CREATE TABLE IF NOT EXISTS outbound_messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id  TEXT NOT NULL,
    run_id        TEXT,
    kind          TEXT NOT NULL,      -- resolution | holding_reply
    reply_text    TEXT NOT NULL,
    refund_sen    INTEGER NOT NULL,
    authorised_by TEXT NOT NULL,      -- "auto" or a person
    status        TEXT NOT NULL,      -- sent (simulated)
    created_at    TEXT NOT NULL,
    UNIQUE (complaint_id, kind)       -- a retry or rerun can never send twice
);

CREATE TRIGGER IF NOT EXISTS agent_runs_no_update BEFORE UPDATE ON agent_runs
BEGIN SELECT RAISE(ABORT, 'agent_runs is append-only'); END;
CREATE TRIGGER IF NOT EXISTS agent_runs_no_delete BEFORE DELETE ON agent_runs
BEGIN SELECT RAISE(ABORT, 'agent_runs is append-only'); END;
CREATE TRIGGER IF NOT EXISTS case_events_no_update BEFORE UPDATE ON case_events
BEGIN SELECT RAISE(ABORT, 'case_events is append-only'); END;
CREATE TRIGGER IF NOT EXISTS case_events_no_delete BEFORE DELETE ON case_events
BEGIN SELECT RAISE(ABORT, 'case_events is append-only'); END;
"""


def init_db(conn: sqlite3.Connection) -> None:
    """Create everything that is missing; never drops or rewrites data."""
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(cases)")}
    if "human_action" not in columns:  # databases created before the API change
        conn.execute("ALTER TABLE cases ADD COLUMN human_action TEXT")
    conn.commit()
