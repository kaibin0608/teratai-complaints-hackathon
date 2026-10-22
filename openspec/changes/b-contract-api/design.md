## Context

The case store already keeps the contract's `status`, `case_state` and `sent`. Each saved run sets them from the route, and auto-resolved cases get one outbox row. `run_pipeline` is async and never raises for business cases. Engine bugs give a run with no decision. `combined_check` checks any reply against an `EngineResult`. FastAPI and uvicorn are in `requirements.txt`. `docs/build_guide.md` has a reference app using an in-memory dict and a thread pool.

`scoring/api_check.py` (the organisers' test):
- posts N complaints at once, then polls `GET /cases/{id}` every 2 s, with 120 s allowed each
- validates fields, and checks that `case_state` and `sent` match the route
- probes: health; unknown ID → 404; no text → 4xx; unknown customer → no 5xx; repost unchanged
- human-in-the-loop probes on one `awaiting_approval` case: invented-amount edit → 4xx and still unsent; approve → approved, sent, actor recorded, decision unchanged; second approve → 409

## Goals / Non-Goals

**Goals:**
- `api_check.py` passes every probe, with no contract problems, on a fresh API database.
- Hidden test: 20 messy complaints at once, each done well within 120 s.
- The human gate holds: nothing that needs approval is sent before a person approves, and fraud cases wait.

**Non-Goals:** roles and logins, second-tier approval, reassignment, metrics, the UI (bonus platform). The `inbox/` watcher. Fraud investigate and record-outcome.

## Decisions

### D1. Async background work in the server's event loop, not a thread pool
`POST /complaints` stores the case, then `asyncio.create_task(worker(complaint))`, guarded by an `asyncio.Semaphore(LLM_MAX_CONCURRENCY)`. The pipeline is already async, and LLM calls dominate. A thread pool (as in the build guide) would need a loop per thread and would lose `LLMClient`'s shared concurrency gate. Tasks are kept in a set so they aren't garbage-collected. On shutdown, pending tasks are cancelled; their cases stay `processing` and are re-queued at the next startup (D5).

### D2. One store connection, writes only from the event loop
`CaseStore` (sqlite3, WAL) is created once in the app's lifespan. All writes happen in the loop thread: handlers and the worker after `await run_pipeline`. That avoids SQLite write contention without locks. The engine's synchronous CPU work is milliseconds.

### D3. Store additions
- `register(complaint)`: insert a `processing` case plus an `ingest` event. Same hash → return the existing case; different hash → `CaseConflict`. `save_run` already accepts a non-done existing case.
- `cases.human_action TEXT` (JSON): `init_db` adds the column with `ALTER TABLE ... ADD COLUMN` when it's missing, so existing batch databases keep working.
- `act(id, action, actor, reason, reply_text, check)`:
  - returns the updated case, or raises `NotFound` / `WrongState` / `InvalidAction` / `ReplyRefused(problems)`
  - rebuilds the `EngineResult` from the autonomous run's JSON for the check
  - approve / edit_approve: `case_state = approved`, `sent = 1`, outbox `resolution` (`authorised_by = actor`, `refund_sen` from the decision); reject: `rejected`
  - one transaction, plus an event (refused edits are logged as `edit_approve_refused`)
- `acknowledge(id, actor, reason)`: only `with_fraud_team` and not yet sent → outbox `holding_reply` with the agent's reply, `sent = 1`, `human_action`, event `acknowledge`.

Status changes go through these methods only; the HTTP layer just maps exceptions to codes.

### D4. Response shape built from the autonomous run
`case_view(case)`:
- processing → `{complaint_id, status}`
- error → `{complaint_id, status, error}`
- done → `run.prediction_row()` fields + `status` + `self_check` (from the run) + `case_state` + `sent` (bool) + `human_action` (parsed JSON or null) + `hold_reason`

The decision always comes from `autonomous_run_id`.

### D5. Startup
In the lifespan:
1. `check_config()`
2. open the store at `API_DB_PATH`
3. warm `get_db()`
4. re-queue every `processing` case

`main.py` exposes `app`. Run with `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.

### D6. Validation
A Pydantic request model: required strings with `min_length=1` after stripping; `received_at` parsed with `contracts.parse_myt`, failing with 422. FastAPI turns missing fields into 422. A store `CaseConflict` maps to 409.

### D7. Testing offline
Tests use FastAPI's `TestClient` with a temporary `API_DB_PATH` and the conftest's `fake:*` providers. A helper waits for background tasks (polls until done). The real-model check is `scoring/api_check.py` against a running server; its output is recorded in `docs/EXTRACTOR_RESULTS.md` (renamed section "API").

## Risks / Trade-offs

- [The hidden test's messy text (typos, SMS short forms, emoji) is harder than the training text] → separate from this change. Re-test the extractor on messy rewrites next; the API itself is text-agnostic.
- [A long LLM stall blocks a slot] → `LLM_TIMEOUT_S` (30 s) and one retry, then fallbacks hold the case: worst case ~60–70 s per complaint, inside 120 s. 20 at once with 8 slots ≈ 3 waves of 5–8 s.
- [The demo laptop sleeps or the Wi-Fi changes IP] → operational: keep the laptop awake from 15:00, or use a tunnel (ngrok / Cloudflare). Documented in the run instructions.
- [`api_check` training complaints re-run the pipeline on the fresh API database] → extractions and replies are mostly cache hits, so cost is cents.
- [SQLite writes from the batch runner and the API at the same time] → different files (decided), so no contention.

## Migration Plan

New database file; `init_db` creates or migrates it. Rollback: stop the server. Batch data is untouched.

## Decisions confirmed with Dev B (2026-10-22)

- The API server uses its own database (`API_DB_PATH`, default `backend/api.db`).
- No `inbox/` watcher in this change.
- Fraud acknowledge now (`POST /cases/{id}/acknowledge`); other fraud actions with the bonus platform.
