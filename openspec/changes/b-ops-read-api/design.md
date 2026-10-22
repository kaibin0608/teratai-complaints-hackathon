## Context

The app (`backend/main.py`) serves the organisers' contract API over one `CaseStore` (SQLite in WAL mode, at `API_DB_PATH`). The store already keeps everything the UI needs:
- `cases`: state, `sent`, `human_action`
- `agent_runs`: indexed columns for category, outcome, refund, priority, route, hold, self-check, cost and latency, plus `run_json`, the full `AgentRun` with clues, candidates, evidence, calculation and usage
- `case_events`: the audit trail
- `outbound_messages`

Only `case_view()` is exposed today, in the contract's narrow shape.

The UI developer is starting a React app now. They need a stable, documented shape before they start. Login and roles are bonus work, to be added later on these same routes.

## Goals / Non-Goals

**Goals:**
- Four read endpoints (`/api/cases`, `/api/cases/{id}`, `/api/metrics`, `/api/audit`) that give the core UI and the manager dashboard everything they need.
- A guide the UI developer can build from without reading the backend.
- No change to the contract routes or their `api_check` results.

**Non-Goals:**
- Login, roles, role-filtered queues
- Bonus actions: escalate, second-tier approval, reassign, send-back, investigate, record outcome
- WebSocket push
- The UI itself

## Decisions

### D1. Read logic in `backend/db/queries.py`; thin routers in `backend/api/`
Plain functions take a `sqlite3.Connection` and return JSON-ready dicts: `list_cases`, `case_detail`, `metrics` and `audit`. The routers are `api/cases.py`, `api/metrics.py` and `api/audit.py`, the files DEV_B.md names. They only parse the query parameters and map `None` to 404. This keeps `CaseStore` focused on writes and state rules, and makes the queries testable without HTTP.

*Alternative:* more methods on `CaseStore`. That class is already 300 lines and owns the integrity rules; reads don't belong in it.

### D2. List in SQL, joining the autonomous run and using `json_extract` for the rest
`cases LEFT JOIN agent_runs ON run_id = autonomous_run_id`. Most fields come from the indexed columns. The fields that are only in `run_json` come from SQLite's built-in JSON functions: `decision.resolve_due_at`, `decision.vulnerable` and `evidence.customer.full_name`. The machine has SQLite 3.50. Filtering, ordering, counting and paging all run in SQL, so the list never loads 2,500 full runs.

*Alternative:* adding columns for due date and customer name. That needs a schema migration for little gain at this size.

### D3. Detail and metrics parse in Python
`case_detail` loads one `AgentRun` with `model_validate_json` and dumps sections with `model_dump(mode="json")`, so the Pydantic types do the formatting:
- Decimals become strings; `refund_amount_myr` is formatted with two decimals
- datetimes become ISO strings

`metrics` reads the indexed columns of every autonomous run in one query. It reads `run_json` only for `redraft_count` and the drafting model, via `json_extract`. It computes percentiles in Python (nearest rank). At about 2,500 rows this takes well under a second.

### D4. The waiting reason is code, in one table
A dict from `hold_reason` to text, plus the route and outcome rules in the spec. The refund limit comes from `get_auto_refund_limit()` (Dev A's tools; read-only use), so the text follows the policy file. The list and the detail share one function.

### D5. CORS: any origin, no credentials
`CORSMiddleware(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])` in `main.py`. The React app may run on `localhost:5173` or on a teammate's laptop at a venue IP we can't know in advance.

There are no cookies. The later bonus login will use a bearer token in the `Authorization` header, which works with `*`. The contract routes are open by design anyway, so CORS adds no exposure. This covers the contract routes too, so the UI's approve buttons work from the browser.

*Alternative:* an env var listing the origins. That changes `config.py`, a shared file, and breaks whenever the UI's address changes.

### D6. `async def` handlers on the loop thread
As with the contract routes (b-contract-api D2), the handlers are `async def`, so every SQLite access stays on the event-loop thread with the one connection. The queries take milliseconds. A thread pool would share a `check_same_thread=False` connection across threads.

### D7. Time handling
- Stored datetimes look like `YYYY-MM-DD HH:MM[:SS]` in `cases` and `case_events`, and ISO in `run_json`. They're returned as ISO with a `T`.
- `as_of`, `since` and `until` are parsed with `contracts.parse_myt` / `parse_date`, so they accept the same formats as complaints. A date alone means the start of the day for `since`, and the end of the day for `until`.
- String comparison works because every stored form starts with `YYYY-MM-DD`.

### D8. Filling the demo database
The API database starts empty except for what's posted to it. For a full dashboard and queues in the demo:

```
python -m backend.batch.runner --ids test --db backend/api.db
```

The runner already takes `--db`. The LLM cache makes this free and quick. The guide documents it, with a warning not to run it while `api_check` runs: two writers to one SQLite file wait on each other (`busy_timeout` of 5 s), which is safe but slow.

### D9. The UI guide is a document, checked by tests
`docs/UI_API.md` has the endpoints, parameters, TypeScript interfaces and example JSON. The example JSON is generated from a real offline run (`fake:*` models). The tests pin each response's top-level and item keys to fixed lists that match the guide, so a shape change fails a test until the guide and the lists are updated together.

## Risks / Trade-offs

- [Open read endpoints expose all case data to anyone on the network] → The data is synthetic, and the contract API is already open. The bonus login adds a role dependency to these routes later.
- [Metrics over the API database differ from the batch database's] → That's by design: the API server reports what it has processed. D8 seeds it for the demo.
- [SLA "overdue" against the real clock marks every September complaint overdue] → `as_of` (spec). The guide tells the UI to pass `as_of` in demo mode.
- [The UI polls the list often] → The list is one indexed SQL query. A 3–5 s poll is fine; the guide recommends it.
- [Shape changes after the UI developer starts] → The guide is the contract. Changes after this PR are additive only, and noted in the guide's changelog.

## Migration Plan

No schema change. Deploy: merge, restart uvicorn. Rollback: revert the commit. The contract routes are untouched.

## Decisions confirmed with Dev B (2026-10-23)

- No login now; it's added later on the same routes.
- The UI is React. The response shape is ours to design, documented for the UI developer.
- `GET /api/audit` is included.
