## 1. Store additions

- [x] 1.1 `schema.py`: `cases.human_action` column; `init_db` adds it to existing databases (`ALTER TABLE` when missing)
- [x] 1.2 `store.py`: `register(complaint)` (processing case + ingest event; same hash → existing; different → `CaseConflict`), `processing_ids()`, `case_view(complaint_id)` in the contract's shape
- [x] 1.3 `store.py`: `act(...)` and `acknowledge(...)` with `NotFound` / `WrongState` / `InvalidAction` / `ReplyRefused`, the outbox, `human_action` and events
- [x] 1.4 Tests: migration on an old database; register idempotent and conflict; approve / reject / edit_approve (good and refused) / second action; acknowledge rules; decision fields never change

## 2. Service

- [x] 2.1 Shared config: `API_DB_PATH` in `config.py` (default `backend/api.db`) and `.env.example`
- [x] 2.2 `backend/api/contract.py`: request models, the four contract endpoints and `/acknowledge`, exception → status code mapping
- [x] 2.3 `backend/main.py`: FastAPI app with lifespan (`check_config`, store, `get_db` warm-up, re-queue `processing`), background worker with a semaphore, error → `status: error`
- [x] 2.4 Tests (`TestClient`, offline): new complaint → done; 422 cases; repost 200 unchanged; conflict 409; unknown customer done with `customer_not_found`; unknown case 404; health; 20 at once all done; pipeline failure → `error`; restart re-queues processing; full approve / edit / reject / acknowledge flows over HTTP

## 3. Real check and docs

- [x] 3.1 Start the server against a fresh API database; run `python scoring/api_check.py http://localhost:8000` (default 10) and `--n 30`; every probe passes, with no contract problems; record score, timing and probes in `docs/EXTRACTOR_RESULTS.md`
- [x] 3.2 `docs/PLAN.md`: replace the old `/api/*` core endpoint list and the live-round intake with the contract (bonus endpoints stay in the bonus section); add run instructions (uvicorn on 0.0.0.0:8000, tunnel option, keep running from 15:00 until the demo)
