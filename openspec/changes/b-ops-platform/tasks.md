## 1. Shared config (approved by Dev A, 2026-10-23)

- [x] 1.1 `config.py`: `JWT_SECRET` (default `dev-only-not-secret`), `AUTH_REQUIRED` (default false). `.env.example`: both, documented

## 2. Database

- [x] 2.1 `schema.py`: the `users` table; new `cases` columns (`workflow`, `sensitive_reason`, `assigned_to`, `escalation`, `draft_reply`, `fraud_outcome`) added by the migration loop
- [x] 2.2 `seed.py`: the four users (bcrypt), idempotent; called in the app lifespan
- [x] 2.3 `store.py`:
  - the gated `send()` (D5), used by contract approve, edit_approve and acknowledge (which sets `workflow = investigating`)
  - `act()` uses the current run and refuses a non-null workflow
  - `save_reprocess()`
  - restart cleanup of `reprocessing`
- [x] 2.4 Tests: migration on an existing database; seeding twice; a double send → 409 with one outbox row; contract approve refused on an escalated case; `case_view` stays autonomous after a reprocess

## 3. Auth

- [x] 3.1 `backend/auth/jwt.py`, `dependencies.py` (`viewer`, `actor`, `require`), `router.py` (login, me, users)
- [x] 3.2 Tests: login ok and wrong (401, same message), me, expired and bad token, the `AUTH_REQUIRED` switch on and off, `/api/users` manager-only, contract routes need no token

## 4. Workflow

- [x] 4.1 `backend/db/workflow.py`: `User`, `Forbidden`, `limit_check`, sensitivity, team and assignee checks
- [x] 4.2 Officer actions: approve, reject, edit_reply (draft and diff event), escalate (proposal), flag_sensitive
- [x] 4.3 Manager actions: second_tier approve / reject (approval and fraud branches), reassign
- [x] 4.4 Fraud actions: investigate, record_outcome (limit on the disputed transaction)
- [x] 4.5 Send back: `Workflow.send_back` plus `AgentService.reprocess` (note appended, `run_kind = reprocess`, never auto-resolved, crash → `send_back_failed`)
- [x] 4.6 Tests for every spec scenario:
  - within / over the limit, elderly → sensitive, reject without a reason
  - edit with an invented amount locks approve
  - escalate → second-tier approve and reject (both teams)
  - first tier and contract can't clear an escalation
  - reassign (wrong team, assignee rule)
  - send back with a note, and a crash
  - fraud acknowledge → investigate → outcome, high-value fraud → escalate → manager
  - double click

## 5. Routes and reads

- [x] 5.1 `backend/api/actions.py`: the `POST /api/cases/{id}/<action>` routes, with role guards and error → status mapping (D10), returning the case detail; mount it in `main.py`
- [x] 5.2 `queries.py`:
  - scope (role filter) on the list and detail, including counts
  - join on the current run
  - new item and case fields (`workflow`, `sensitive`, `sensitive_reason`, `assigned_to`, `escalation`), `workflow_counts`
  - filters: `workflow`, `sensitive`, `assigned_to` (`me` / `none`), `overridden`
  - detail adds `autonomous`, `final`, `differs`, `draft_reply`, `fraud_outcome`
- [x] 5.3 `queries.metrics`: `by_channel`, `by_language`, `by_workflow`, `sla.compliance`, `turnaround_minutes`, `trends.received_by_day`, `refunds_myr`
- [x] 5.4 `cases.py`, `metrics.py`, `audit.py`: pass the viewer's scope; metrics and audit manager-only when a user is known
- [x] 5.5 Tests: role-filtered list, counts and detail 404; manager-only reads; the new filters and fields; the agent-vs-human scenarios; metrics scenarios (compliance, refund totals, trend); the pinned key lists updated

## 6. Check and document

- [x] 6.1 Full test suite; `api_check` on a fresh API database (expect 100.0, 9/9 probes); drive the three demo flows over HTTP with the real models and record them
- [x] 6.2 `docs/UI_API.md`:
  - login and the token header, `AUTH_REQUIRED`
  - the roles table, every action with its request and errors
  - the new fields and filters, the agent-vs-human section, the new metrics
  - changelog
- [x] 6.3 `docs/EXTRACTOR_RESULTS.md` (the demo-flow run and its decisions), `docs/STATUS.md` (tick B1–B9), `docs/PLAN.md` (limits RM2,000 / RM5,000 and why)
