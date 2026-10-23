## 1. Case store

- [x] 1.1 `backend/db/schema.py`: DDL for `agent_runs`, `cases`, `case_events`, `outbound_messages`, with append-only triggers on `agent_runs` and `case_events`; `init_db(conn)` (WAL, busy timeout)
- [x] 1.2 `backend/db/store.py`: `CaseStore` with `save_run` (new case + ingest event, run row, case state from the route, outbox for AUTO_RESOLVE, `CaseConflict` on a content-hash mismatch, the rerun rule)
- [x] 1.3 Read helpers: `get_case`, `autonomous_run` (rebuilds `AgentRun` from JSON), `cases_for(ids)`, `events(id)`
- [x] 1.4 Tests: run round-trips; UPDATE/DELETE on `agent_runs` and `case_events` raise; route → case_state/sent table; CMP-00244 waits with no outbox; AUTO_RESOLVE writes one outbox row even after a rerun; failed run → `error`; content conflict raises; rerun repoints and keeps the old run; rerun refused after a non-agent event

## 2. Batch runner

- [x] 2.1 `backend/batch/runner.py`: ID selection (`test` / `train` / `pilot` / `holdout` / file, `--limit`), `check_config()` first, warm-up of `get_db()`
- [x] 2.2 Concurrent processing with a semaphore; time each pipeline; save each run as it finishes
- [x] 2.3 Resume (skip done, retry error/missing) and `--rerun`; `--no-draft`; `--db` override
- [x] 2.4 Progress every 50 and a final summary: processed/skipped/failed, routes, hold reasons, `llm_error` count, RM total and per complaint, mean/p95 latency, wall time
- [x] 2.5 Tests (offline, keyword extractor, temporary DB): pilot run stores 50 cases; a second run skips all; `--rerun` makes new runs; a failing engine produces an `error` case and is retried on the next run; the summary counts add up

## 3. Export

- [x] 3.1 `backend/batch/submit.py`: rows from autonomous runs via `prediction_row()`; default output `submissions/<TEAM_NAME>/predictions.csv` for `--ids test`; `--out`
- [x] 3.2 Validation per row and of the ID set; report missing/failed/invalid by ID; write valid rows; non-zero exit on any gap; `--strict`
- [x] 3.3 `--score` / `--details`: run `scoring/score.py` on training exports through `sys.executable`
- [x] 3.4 Tests: valid export has exact header and rows; empty reply and bad refund format reported; missing IDs listed and not invented; `--strict` writes nothing; export ignores later human changes (reads the autonomous run)

## 4. Real runs

- [x] 4.1 Run the pilot end to end (`runner --ids pilot`, then `submit --ids pilot --score`) and check the score matches clue_eval's numbers
- [x] 4.2 Run all 1,750 training complaints with the DeepSeek extractor; export with `--score --details`; record the official score, critical-error rate, cost and latency in `docs/EXTRACTOR_RESULTS.md`
- [x] 4.3 Run the 750 test complaints; export `submissions/<TEAM_NAME>/predictions.csv` and confirm it validates (750 rows)
