## Why

The React UI (built by our third developer, not started yet) has nothing to show beyond one case at a time. The contract API has no list of cases, and `GET /cases/{id}` returns only the decision fields: no evidence, candidates, rule, calculation, audit trail or cost. Those exist only in the database. The core UI needs queues and a case view ([PLAN.md](../../../docs/PLAN.md) Phase 3). The **Engineering score (20%)** asks for observability ("show why it decided") and cost and speed per complaint. The demo's observability step needs an audit log and a dashboard.

## What Changes

- **Read-only `/api/*` endpoints**, served by the same app and database as the contract API:
  - `GET /api/cases`: the queues. Filters (state, route, category, priority, hold reason, search), sorted by priority then SLA due date, paged, with a count per queue for the tabs. Each row says why the case is waiting ("Refund over RM500", "Fraud investigation", "Ambiguous match").
  - `GET /api/cases/{id}`: everything about one case: complaint, customer, clues the LLM read, candidate transactions with scores and reasons, evidence, decision with rule and calculation, reply with its self-check result, cost and latency, run history, audit trail and outbox.
  - `GET /api/metrics`: totals by state, route, category, priority and outcome; auto-resolve rate; holds by reason; self-check catches; human approvals, rejections, edits and override rate; overdue cases; cost and latency per complaint; throughput.
  - `GET /api/audit`: the append-only event log across all cases, filtered by actor, action, case and date, newest first.
- **No login yet.** These routes are open, like the contract routes. Login and role filtering come later as the bonus step, added on top of the same routes. The UI's buttons keep calling the existing `POST /cases/{id}/actions` and `POST /cases/{id}/acknowledge`.
- **CORS** so the React dev server (another origin) can call the API from a browser.
- **A guide for the UI developer (`docs/UI_API.md`)**: how to run the backend locally for free (`fake:*` models), every endpoint with its parameters, real example responses and TypeScript types, which actions each queue allows, and how to fill the database with the 750 test cases for the demo.

## Capabilities

### New Capabilities
- `case-queue-api`: listing cases as queues, with filters, ordering, counts and a waiting reason.
- `case-detail-api`: the full decision trail of one case.
- `ops-metrics-api`: the dashboard numbers, including cost and latency per complaint.
- `audit-log-api`: reading the event log across cases.

### Modified Capabilities
<!-- None. The contract routes (`/complaints`, `/cases/{id}`, `/cases/{id}/actions`, `/cases/{id}/acknowledge`, `/health`) don't change. -->

## Impact

- **New code**: `backend/db/queries.py` (read-only SQL and response shaping), `backend/api/cases.py`, `backend/api/metrics.py`, `backend/api/audit.py` (thin routers, as named in DEV_B.md), tests, `docs/UI_API.md`.
- **Changed**: `backend/main.py` (mount the routers, add CORS).
- **Not changed**: `contracts.py`, `config.py`, the database schema, Dev A's files, the contract routes. `scoring/api_check.py` results stay the same.
- **Cost**: none. Reads only; no LLM calls.
