## Context

What exists today:
- **The case store** (`backend/db/store.py`) keeps the contract state: `status`, `case_state`, `sent` and `human_action`. Its state rules cover the contract actions (approve, edit_approve, reject) and the fraud acknowledge. Every send goes through `_outbox`, which uses `INSERT OR IGNORE` on `UNIQUE (complaint_id, kind)`.
- **Read routes** (`backend/api/{cases,metrics,audit}.py`, queries in `backend/db/queries.py`) are open, and documented for the UI developer in `docs/UI_API.md`.
- **The pipeline** takes a `run_kind` argument, and `AgentService` runs work in the background on the event loop.
- **Libraries:** `python-jose` and `bcrypt` are already in `requirements.txt`.

Data facts that shaped the decisions:
- **No refund in the data exceeds RM5,000** (the largest is RM4,687.10). 128 of 466 approval refunds are over RM2,000, which led to the RM2,000 officer limit.
- 146 of 1,115 approval cases and 78 of 520 fraud cases are for customers 65 or older. All of them will go to the manager.
- 126 of 520 fraud cases have a disputed transaction over RM5,000.

## Goals / Non-Goals

**Goals:**
- the three demo flows from bonus_platform.md, end to end over HTTP
- role separation enforced in the backend
- a two-tier rule that can't be bypassed, even through the contract route
- the agent-vs-human record
- the extra dashboard numbers
- `api_check` unchanged

**Non-Goals:**
- the UI screens
- WebSocket push, the chatbot, notifications
- password changes, user admin, refresh tokens
- production-grade identity

## Decisions

### D1. Workflow rules in `backend/db/workflow.py`, beside `CaseStore`
A `Workflow` class wraps the store's connection and owns the platform actions:
- approve, reject, edit_reply, escalate, flag_sensitive
- second_tier, reassign, send_back
- investigate, record_outcome

Each takes a `User` and raises typed errors: `Forbidden(why, **info)` → 403, plus the existing `WrongState` → 409 and `InvalidAction` → 422.

`CaseStore` keeps the contract actions and gains the one gated send (D5). That keeps `store.py` from doubling in size, and leaves every state rule out of the HTTP layer, as before.

*Alternative:* put everything in `CaseStore`. That's one 700-line class mixing contract and platform rules.

### D2. Schema: a `users` table, and new nullable columns on `cases` added by migration
- `users (username PK, password_hash, full_name, role, approval_limit_sen NULL)`, seeded by `backend/db/seed.py` in the app lifespan (insert-or-ignore).
- New `cases` columns, all NULL by default:

  | Column | Holds |
  |---|---|
  | `workflow` | NULL, `escalated`, `reprocessing`, `investigating` or `closed` |
  | `sensitive_reason` | manual flag only |
  | `assigned_to` | the assignee's username |
  | `escalation` | JSON |
  | `draft_reply` | JSON `{text, self_check, problems, by, at}` |
  | `fraud_outcome` | JSON |

- `init_db` adds missing columns in a loop, as it does for `human_action` today, so existing batch and API databases keep working.

JSON blobs instead of many columns: they're read whole and never queried by inner field, except `workflow` and `assigned_to`, which are plain columns. The batch runner never touches them.

### D3. Auth
- `backend/auth/jwt.py`: `make_token(user)` and `read_token(token)`, HS256 with `config.JWT_SECRET`, 12-hour expiry, payload `{sub, role}`.
- `backend/auth/dependencies.py`:
  - `viewer(request)` returns a `User`, or `None` when there's no token and `AUTH_REQUIRED` is off (the manager view). It raises 401 on a bad token, or on a missing one when auth is required.
  - `actor(request)` always needs a valid token.
  - `require(*roles)` wraps either one.
- The user is looked up in the database on every request, so a role change takes effect at once.
- `backend/auth/router.py` serves `/api/auth/login`, `/api/auth/me` and `/api/users`.
- Passwords are checked with `bcrypt.checkpw`. A login failure takes the same time and gives the same message whether the user exists or not.

`config.py` gains `JWT_SECRET` (default `"dev-only-not-secret"`, logged as a warning at startup when it's left as the default) and `AUTH_REQUIRED` (default false). This is a shared-file change, so it needs Dev A's approval.

### D4. Current run vs autonomous run
`cases.current_run_id` already exists. The platform works on the **current** run: decisions, limits, the reply to send, and the evidence the self-check uses. The contract view (`case_view`) and `predictions.csv` keep the **autonomous** run.

The list and detail queries switch their join from `autonomous_run_id` to `current_run_id`. Today the two are identical for every case, so nothing visible changes. The detail adds an `autonomous` section for the agent-vs-human view.

`store.act()` (contract approve) changes in two ways:
- it uses the current run's reply and refund
- it refuses (`WrongState` → 409) when `workflow` is not null, so an escalated, re-running or closed case can't be approved through the open contract route

`api_check` only acts on fresh `awaiting_approval` cases, so its probes are unaffected.

### D5. One gated send: `CaseStore.send(case, kind, reply, refund_sen, by, *, allow_escalated=False)`
Every human-triggered outbox write goes through it:
- contract approve and edit_approve
- platform approve
- second-tier approve
- acknowledge

It checks, in order:
1. the case is not escalated, unless the second tier is calling
2. the reply was checked with `combined_check` and passed. The caller passes the `CheckResult`, and a failure raises `ReplyRefused`.
3. the insert actually wrote a row (`cursor.rowcount == 1`). Otherwise it raises `WrongState("already sent")` → 409.

The state update and the outbox insert share one transaction, so a double click can't send twice or leave half a state.

### D6. Limits and sensitivity are computed, not stored
`limit_check(user, case, run) -> None | Forbidden`:
- **Amount:** the officer's is the current refund. The analyst's is `float(evidence.matched_txn.amount_myr)`, or 0.
- **Sensitive:** `decision.vulnerable` or `sensitive_reason` is set.
- **Manager:** never limited.

Everything comes from the run plus one column, so there's nothing to keep in sync after a send back. The `why` text names the rule: "refund RM2,500.00 is over your limit RM2,000.00", or "sensitive: Customer aged 65+".

### D7. Send back runs in the background, like intake
`Workflow.send_back` does the following:
1. checks the state and the note
2. sets `workflow = reprocessing` and appends a `send_back` event
3. returns at once (HTTP 202 with the case detail)

The route then calls `AgentService.reprocess(complaint, note)`. That builds a copy of the complaint with `text + "\n\n[Officer note: …]"` and runs `run_pipeline(..., run_kind="reprocess")` under the same semaphore. Then `CaseStore.save_reprocess(case_id, run)`:
- inserts the run
- updates `current_run_id`
- clears `draft_reply`
- sets `case_state` to `with_fraud_team` if the new route is FRAUD_TEAM, otherwise `awaiting_approval`. It's never auto-resolved: once a person has touched a case, nothing goes out without one.
- sets `workflow` back to NULL and appends an `agent_run` event

A crash leaves the current run as it was and appends `send_back_failed`.

On restart, cases stuck in `reprocessing` go back to NULL, with a `send_back_failed` event "server restarted". They aren't re-run silently.

The note changes the text, so the LLM cache misses and the extractor sees the officer's facts. This is why send back is useful: it gets the agent to redo an `ambiguous_match` with the date or amount the officer confirmed.

### D8. Role filter in SQL
The case's team comes from `r.route` of the current run. `list_cases` and `case_detail` take a `scope` argument:
- `None` (manager): all cases
- `"HUMAN_APPROVAL"`: the officer's cases
- `"FRAUD_TEAM"`: the analyst's cases

The scope is added to the WHERE clause, including the one behind `counts` and the new `workflow_counts`. A detail outside the scope returns None → 404.

### D9. Metric additions from tables we already have
- **Turnaround and SLA compliance** use `case_events`: the first `agent_run` event of the case, the `ingest` event, and the first closing event (`approve`, `edit_approve`, `reject`, `second_tier_*`, `record_outcome`). Event times are real (2026-10), and so are the durations between them. The allowance comes from the decision's `resolve_due_at − received_at`. Both are durations, so the synthetic dates don't distort it.
- **Refunds** use `outbound_messages` (`authorised_by` is `auto` or a person) for the paid amounts. Open approval cases give `awaiting`. Rejected cases give `rejected`.
- **Trends** group by `substr(received_at, 1, 10)`.

### D10. HTTP shapes

| Code | When |
|---|---|
| 401 | no token or a bad token |
| 403 | wrong role or team, not the assignee, or over the limit / sensitive. The limit case returns `{"detail": {"error": "escalate to a manager", "why", "limit", "amount"}}` |
| 404 | unknown case, or one outside your scope |
| 409 | wrong state: already acted, escalated, re-running |
| 422 | missing reason or note, a bad outcome, or a refused draft (`{"detail": {"error", "problems"}}`) |

Every platform action returns the case detail (the same shape as `GET /api/cases/{id}`), so the UI redraws from one response.

## Risks / Trade-offs

- [65+ customers mean about 13% of approval cases and 15% of fraud cases go to the manager] → This is the decided rule (Dev B, 2026-10-23). The `sensitive=true` filter and `waiting_reason` make it visible.
- [Without a token, the open read mode shows everything] → It's synthetic data, and the switch goes on once the login page exists. The demo should run with `AUTH_REQUIRED=true` to show role separation.
- [The default `JWT_SECRET`] → It's logged as a warning at startup, and `.env.example` documents setting one.
- [The contract approve can still approve a sensitive or over-limit case that nobody escalated] → Accepted: the judges' route has no identity (decided: keep it open). The platform route enforces the rule, and once a case is escalated the contract route refuses it (D4).
- [Switching the list and detail to the current run] → Identical for every existing case. A test pins that `case_view` and the submission still use the autonomous run after a send back.
- [The send-back pipeline costs money and time] → About RM0.002, a few seconds, only on demand.

## Migration Plan

`init_db` adds the columns and the users table on the next start; seeding is idempotent. Rollback: revert the commit. The new columns are ignored by the old code. The contract routes and the batch flow are unchanged.

## Decisions confirmed with Dev B (2026-10-23)

- 65+ is sensitive automatically, and a manual flag also counts.
- Send back is built.
- The contract route stays open: no login and no limits, but it refuses escalated cases.
- All five dashboard additions go in this change.
- `AUTH_REQUIRED` stays off until the login page is ready.
- Four users, sharing the password `teratai123`.
- `JWT_SECRET` lives in `.env` via `config.py`. Dev A approved this shared-file change (2026-10-23).
- Officer limit RM2,000; fraud analyst RM5,000; the manager has none.
