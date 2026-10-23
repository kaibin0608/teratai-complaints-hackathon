## Why

On 22 Oct the organisers fixed one HTTP API that every team must expose (`docs/api.md`), and test it with `scoring/api_check.py`. It now carries:
- **the hidden test (15 points):** right after the 15:00 freeze on Day 2, 20 unseen, messy complaints are sent at once and scored like the leaderboard
- **the human gate (10 points):** judges check that approvals hold and fraud cases reach the fraud queue
- **Checkpoint 2 (Day 2, 12:00):** requires `api_check.py` to pass and the API to be reachable

PLAN.md's own `/api/intake` design is replaced by this contract. The pipeline, case store and reply checks it needs already exist.

## What Changes

- **FastAPI service (`backend/main.py`, `backend/api/contract.py`)** implementing the contract exactly:
  - `POST /complaints`: validate the six fields; store the case as `processing`; run the pipeline in the background; answer `202 {"complaint_id", "status": "processing"}`.
    - Missing or empty required fields → `422`.
    - The same ID with the same content → the existing case's status (`200`), with no second case and no change.
    - The same ID with different content → `409`.
    - An unknown customer is accepted and held (`customer_not_found`), never a `5xx`.
  - `GET /cases/{id}`: `404` if unknown; `{"status": "processing"}` while working. When done: every contract field (the agent's decision as in `predictions.csv`, `self_check` passed/flagged, `case_state`, `sent` as a bool, `human_action`), plus `hold_reason`. `status: "error"` carries an `error` reason.
  - `POST /cases/{id}/actions`: `approve` / `reject` / `edit_approve` with `actor` (required) and `reason` (required for reject and edit_approve).
    - Only on `awaiting_approval`; otherwise `409`. Unknown case → `404`. Bad input → `422`.
    - An edited reply is re-checked with `combined_check` (Dev A's evidence check plus our reply rules) against the case's evidence. If it fails: `422`, nothing sent.
    - Approve or edit_approve → `approved`, `sent: true`, one outbox message. Reject → `rejected`, `sent: false`.
    - `human_action = {action, actor, reason, at, reply_text}`. The agent's decision fields never change.
  - `GET /health`: `200`.
- **Fraud acknowledge (decided with Dev B, outside the official contract)**: `POST /cases/{id}/acknowledge {actor, reason?}` on a `with_fraud_team` case sends the agent's holding reply (outbox `holding_reply`, `sent: true`) and records `human_action`. The case stays `with_fraud_team`. Anything else → `409`.
- **Separate API database (decided with Dev B)**: the service uses `API_DB_PATH` (default `backend/api.db`), so probes and demo clicks never touch the batch data behind `predictions.csv`.
- **Store additions (`backend/db/store.py`)**: register a `processing` case before the run; `human_action` column (added to existing databases without data loss); `act()` and `acknowledge()` with the state rules above, all appended to `case_events`.
- **Robustness**: `check_config()` at startup; complaints left `processing` by a crash are re-queued on startup; at most `LLM_MAX_CONCURRENCY` pipelines in flight; a pipeline failure becomes `status: error` with a reason, never a stuck case.
- **PLAN.md**: the endpoint list and live-round section updated to the contract; the bonus endpoints stay under the bonus section.
- **Not in this change (decided with Dev B)**: the watched `inbox/` folder; other fraud-workbench actions (investigate, record outcome) and roles, which belong to the bonus platform.

## Capabilities

### New Capabilities
- `complaint-intake-api`: `POST /complaints`, validation, idempotency, background processing, restart recovery.
- `case-api`: `GET /cases/{id}` in the contract's shape, and `GET /health`.
- `human-actions-api`: approve / reject / edit_approve with the self-check on edits, plus fraud acknowledge.

### Modified Capabilities
<!-- None archived yet. Builds on case-store (b-batch-runner): adds the processing state, human_action, and act/acknowledge. -->

## Impact

- **New code**: `backend/main.py`, `backend/api/contract.py`, and tests using FastAPI's `TestClient` (offline, `fake:*` LLM providers).
- **Changed**: `backend/db/schema.py` (`human_action` column + migration), `backend/db/store.py`, `docs/PLAN.md`.
- **Shared file**: `backend/config.py` gets `API_DB_PATH` (needs Dev A's review). `.env.example` documents it.
- **Run**: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`, then `python scoring/api_check.py http://localhost:8000`. LLM cost is small: `api_check` sends training complaints, whose extractions and replies are mostly cached.
- **Unchanged**: `contracts.py` and Dev A's files.
