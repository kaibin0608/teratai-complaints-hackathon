## Why

The extractor and engine work, but nothing yet runs all complaints, stores what the agent decided, or writes `predictions.csv`. Without that there is no official 0–100 training score, and no 750-complaint test file. The README warns not to leave that run for the last hour. The plan's Day 1 evening milestone is the first full test run.

The same store will back the organisers' fixed API (`docs/api.md`, next change). So the case record is shaped to that contract now: `status`, `case_state`, `sent`.

## What Changes

- **Case store (`backend/db/`)**: SQLite with stdlib `sqlite3`.
  - `agent_runs`: one immutable row per pipeline run; SQLite triggers reject UPDATE and DELETE.
  - `cases`: the complaint, its exported run, and its workflow state, shaped to `docs/api.md`.
  - `case_events`: append-only.
  - `outbound_messages`: the simulated outbox.
  - Auto-resolved cases get an outbox row and `sent = true`. Human-approval and fraud cases wait with `sent = false`.
- **Batch runner (`backend/batch/runner.py`)**:
  - Runs a set of complaints (test, all training, pilot, holdout, or an ID file) through `run_pipeline` with bounded concurrency, storing every run.
  - Resumes after a crash by skipping complaints that already have a run.
  - `--rerun` makes a new run after a prompt or model change.
  - `--no-draft` keeps the template reply (Checkpoint 1).
  - Prints progress and a summary: routes, hold reasons, failures, cost in RM, and latency per complaint.
- **Export (`backend/batch/submit.py`)**: writes `predictions.csv` from each case's exported autonomous run, never from human edits. It validates the result: header, the expected ID set (exactly the 750 test IDs for a submission), unique IDs, valid values, two-decimal refunds, transaction ID format, non-empty replies. Missing or failed complaints are reported, never filled in. `--score` runs `scoring/score.py` on training exports.
- **Run timing**: the runner records each run's end-to-end latency, for the per-complaint speed the judges score.

## Capabilities

### New Capabilities
- `case-store`: persisting runs and cases, immutable agent runs, the append-only event log, the case state set from the route, and the simulated outbox.
- `batch-runner`: running many complaints through the pipeline with concurrency, resume, rerun, no-draft mode and a run summary.
- `prediction-export`: writing and validating `predictions.csv` from autonomous runs, reporting gaps, and scoring training exports.

### Modified Capabilities
<!-- None: no spec in openspec/specs/ yet (b-llm-extractor is not archived). -->

## Impact

- **New code**: `backend/db/{schema,store}.py`, `backend/batch/{runner,submit}.py`, plus tests.
- **No change to `contracts.py` or Dev A's files.** `AgentRun` is stored as JSON alongside flattened decision columns for queries.
- **Config**: uses the existing `DB_PATH`, `TEAM_NAME` and `LLM_MAX_CONCURRENCY`. No shared-file change.
- **Cost**: all 1,750 training complaints with the DeepSeek extractor ≈ RM3; the 750 test complaints ≈ RM1.50. Reruns hit the LLM cache unless the prompt or model changed.
- **PLAN.md**: its `cases.status` values and `/api/*` endpoint names predate `docs/api.md`. Update it in the API change.
