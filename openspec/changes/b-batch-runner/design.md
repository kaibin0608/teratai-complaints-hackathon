## Context

`run_pipeline` (b-llm-extractor) returns an `AgentRun` per complaint, with the real engine and the DeepSeek extractor. Nothing stores it. The organisers' API (`docs/api.md`) will read cases back with `status`, the decision fields, `self_check`, `case_state`, `sent` and `human_action`, so this store is built to serve that next.

Constraints:
- Python stdlib plus what is in `requirements.txt`. No ORM is installed and none is needed.
- `contracts.py` and Dev A's files stay unchanged.
- `*.db` is gitignored; `DB_PATH` defaults to `backend/teratai.db`.
- One process at a time writes: the runner now, the API server later.
- Data volume is tiny (2,500 complaints, a few runs each).

## Goals / Non-Goals

**Goals:**
- Every run is stored and can't be altered afterwards. The exported run per complaint is explicit.
- A full batch survives a crash and resumes without paying for finished complaints again.
- `predictions.csv` is produced only from autonomous runs, and validated, with gaps reported, not filled.
- The case shape already matches what `GET /cases/{id}` must return.

**Non-Goals:**
- HTTP endpoints, human actions, and approval limits. That's the API change.
- The LLM reply drafter. Template replies until step 4.
- Users, roles, auth (bonus platform).
- Postgres or multi-process write access.

## Decisions

### D1. stdlib `sqlite3` behind one small store class
`backend/db/store.py` exposes `CaseStore(path)` with `save_run(complaint, run, latency_ms, rerun=False)`, `get_case(id)`, `autonomous_run(id)`, `cases_for(ids)`, and `events(id)`. `schema.py` holds the DDL and `init_db(conn)`. WAL mode, one connection per process, writes from the event-loop thread only: the runner awaits the pipeline, then saves synchronously.

*Alternative:* SQLAlchemy or SQLModel. Rejected: a new dependency and a shared-files PR for five tables.

### D2. Schema
```
agent_runs        run_id PK, complaint_id, run_kind, created_at,
                  category, matched_txn_id, outcome, refund_sen INT, priority, reply_language, route,
                  hold_reason, self_check ('passed'|'flagged'|NULL), error,
                  extract_model, prompt_version, schema_version, cost_myr TEXT, latency_ms INT,
                  run_json TEXT                      -- full AgentRun, source of truth
cases             complaint_id PK, customer_id, received_at, channel, subject, text, content_hash,
                  autonomous_run_id, current_run_id, status, case_state, sent INT, error,
                  created_at, updated_at
case_events       id PK AUTOINCREMENT, complaint_id, actor, action, run_id, detail, created_at
outbound_messages id PK AUTOINCREMENT, complaint_id, run_id, kind, reply_text, refund_sen INT,
                  authorised_by, status, created_at, UNIQUE(complaint_id, kind)
```
- `BEFORE UPDATE` / `BEFORE DELETE` triggers on `agent_runs` and `case_events` do `RAISE(ABORT, 'append-only')`, so immutability holds in the database, not just in our code.
- Money is integer sen in columns. JSON keeps `Decimal` strings.
- Cost is stored as a TEXT decimal, so tiny amounts don't lose precision.

### D3. The `AgentRun` JSON is the source of truth
`run_json = run.model_dump_json()`. Export and the future API rebuild the run with `AgentRun.model_validate_json` and use `prediction_row()`, so the export format comes from `contracts.py`, not a second copy. The flat columns are for queries and the summary only.

### D4. Reruns repoint the exported run, but only before a human acts
During development we rerun after prompt, model or Dev A engine changes, and the new run must be the one exported. `save_run(..., rerun=True)` inserts a new immutable run, sets `autonomous_run_id = current_run_id = new`, recomputes `status`, `case_state` and `sent`, and logs an `agent_run` event naming the old and new run IDs. It refuses (and the runner reports) if any `case_events` row has an actor other than `agent`. This keeps the integrity rule: the agent's decision never changes after a human acts, and human actions never touch `agent_runs`.

*Alternative:* never repoint, and export the latest run. Rejected: it's implicit, and after the API lands "latest" could be a reprocess run.

### D5. Content hash for idempotency
`sha256` over the six complaint fields, normalised (`received_at` as `%Y-%m-%d %H:%M`, stripped strings). The same ID with the same hash is the same complaint. A different hash raises `CaseConflict`. This is the rule `POST /complaints` needs next.

### D5b. Outbox only for AUTO_RESOLVE
An auto-resolved run writes `outbound_messages(kind='resolution', authorised_by='auto')`. `UNIQUE(complaint_id, kind)` plus `INSERT OR IGNORE` makes reruns and retries unable to send twice. On a rerun that changes the route away from AUTO_RESOLVE, an already-sent message stays (it was "sent"). `sent` stays true, and the event log records it.

### D6. Runner concurrency and resume
`asyncio.Semaphore(concurrency)` bounds pipelines in flight; `LLMClient`'s own gate also bounds LLM calls. `get_db()` is warmed up before tasks start, so the first CSV load doesn't stall the loop. Resume: skip IDs whose case has `status = done`; retry `error` and missing ones. `--rerun` processes everything selected.

### D7. Template replies by default
`stub_draft` is the drafter until `reply_generator.py` exists. `--no-draft` is accepted now and will keep forcing the template once the LLM drafter becomes the default.

### D8. Export validation and scoring
`submit.py` builds rows from autonomous runs, validates each row and the ID set, writes valid rows with `csv.writer` (UTF-8, `newline=''`), and prints a report. With `--score` it runs `scoring/score.py` through `sys.executable` (no import, so the scorer stays exactly what the organisers run) and passes `--details` through.

### D9. Latency and summary
The runner times each `run_pipeline` call with `time.perf_counter()` and stores `latency_ms`. The summary shows: counts by route and hold_reason, `llm_error` count (an LLM outage shows up as keyword fallbacks), total and per-complaint RM, mean and p95 latency, and wall time.

## Risks / Trade-offs

- [The LLM goes down mid-batch and the fallback quietly produces keyword answers] → the summary prints the `llm_error` count prominently. Rerun those complaints with `--rerun --ids <file>` once the provider is back.
- [The engine is synchronous and blocks the event loop briefly per complaint] → acceptable: matching is milliseconds, while LLM calls take seconds.
- [SQLite locking once the API server and the runner run at the same time] → WAL plus a busy timeout. Don't run both against the same DB during a batch; the API change revisits this.
- [Reruns repoint the exported run, which could be misused after a human acts] → guarded by the human-event check, and tested.
- [A wrong `TEAM_NAME` writes the submission to the wrong folder] → the export prints the full output path, and `--out` overrides it.

## Migration Plan

New tables only; `init_db` uses `CREATE TABLE IF NOT EXISTS`. Rollback = delete `backend/teratai.db`, which is regenerated by rerunning (LLM calls come from the cache).

## Decisions confirmed with Dev B (2026-10-22)

- **Team name:** `teratai-team` placeholder for now (`TEAM_NAME`); change it in `.env` before submitting.
- **Replies:** the first 750 test file uses template replies. Rerun with LLM replies once `reply_generator.py` exists; extraction comes from the cache, so only the drafting is paid.
- **Spending:** the real runs are approved: all 1,750 training complaints (~RM3) and the 750 test complaints (~RM1.50).
- **Fraud holding reply:** goes out only after a fraud analyst acknowledges it. FRAUD_TEAM cases are stored with `sent = false`.
