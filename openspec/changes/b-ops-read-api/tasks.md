## 1. Queries

- [x] 1.1 `backend/db/queries.py`: shared helpers (ISO time, money and cost strings, queue key, `waiting_reason` with the hold texts and `get_auto_refund_limit()`), and parsing of filter values with errors for unknown values
- [x] 1.2 `list_cases(conn, filters, sort, limit, offset)`: join the autonomous run, `json_extract` for due date, vulnerable flag and customer name; filters, both sort orders, paging, `total`, and `counts` over all cases
- [x] 1.3 `case_detail(conn, complaint_id)`: all sections from the autonomous run, plus runs, events (parsed detail) and outbound; null sections for processing or error cases; None when unknown
- [x] 1.4 `metrics(conn, as_of)`: counts, rates, holds, self-check catches, human counts and override rate, SLA (`open`, `overdue`, `due_within_24h`), cost and latency stats (nearest rank), models, throughput; nulls when there's no data
- [x] 1.5 `audit(conn, filters, limit, offset)`: filters, newest first, `facets`
- [x] 1.6 Tests (`backend/tests/test_queries.py`) on a store filled through `save_run` / `act` / `acknowledge` with the offline pipeline:
  - every spec scenario: mixed counts, officer queue, several values, bad filter, urgent first, newest first, the waiting reasons, the detail sections, after an approval, processing, unknown case, the small metrics database, empty database, `as_of`, who did what, refused edit, people only
  - pinned key lists

## 2. Routes

- [x] 2.1 `backend/api/cases.py`, `backend/api/metrics.py`, `backend/api/audit.py`: `async def` GET handlers, query parameters checked (422), 404 for an unknown case
- [x] 2.2 `backend/main.py`: mount the three routers and add CORS (any origin, no credentials)
- [x] 2.3 Tests (`backend/tests/test_ops_api.py`, `TestClient`): each route over HTTP, 422s, 404, CORS header with an `Origin` request header, GET leaves the database unchanged, contract routes unchanged (existing `test_api.py` still passes)

## 3. Guide and checks

- [x] 3.1 `docs/UI_API.md` for the UI developer:
  - run the backend locally with free `fake:*` models
  - the base URL and CORS
  - each endpoint with its parameters, a real example response and TypeScript interfaces
  - the actions each queue allows, using the existing `POST /cases/{id}/actions` and `/acknowledge`, with their error codes
  - polling every 3–5 s, demo mode `as_of`
  - filling the database for the demo (D8)
  - a changelog
- [x] 3.2 Run the full test suite. Start the server on a copy of the batch database and spot-check `/api/cases`, one detail and `/api/metrics` timing on ~2,500 cases. Re-run `scoring/api_check.py` on a fresh API database and confirm the score is unchanged.
- [x] 3.3 Record the check results in `docs/EXTRACTOR_RESULTS.md`, and update `docs/PLAN.md` 2.3 to say these four routes exist with no login yet
