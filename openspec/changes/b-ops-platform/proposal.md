## Why

The Best Ops Platform award ([bonus_platform.md](../../../docs/bonus_platform.md)) judges whether:
- the human gate holds through **two tiers**
- each role sees only its own cases
- edits are re-checked
- the audit trail shows who did what and why

Its demo needs three flows the backend can't do yet:
- an officer escalating an over-limit refund to a manager, who approves it
- a fraud analyst acknowledging, investigating and recording an outcome
- the agent-vs-human record across them

Today there are no users or roles, no limits, no escalation, and only the contract's approve / edit / reject / acknowledge. The manager dashboard also lacks the SLA compliance, trends, turnaround and refund totals the plan's console calls for.

## What Changes

- **Login (`backend/auth/`)**:
  - a `users` table, seeded with `officer1`, `officer2`, `fraud1` and `manager1`. They share the demo password `teratai123`, stored as a bcrypt hash. The two officers have a RM2,000 limit (no refund in the data is over RM5,000, so a RM5,000 limit would never be reached; 128 of 466 approval refunds are over RM2,000), the fraud analyst RM5,000, and the manager none.
  - `POST /api/auth/login` returns a JWT; `GET /api/auth/me`; `GET /api/users` (for the reassign menu)
  - `JWT_SECRET` and `AUTH_REQUIRED` in `config.py` and `.env.example`. **This is a shared file, so it needs Dev A's approval.**
- **Role access on `/api/*`**:
  - With a token: the officer sees approval cases, the fraud analyst sees fraud cases, and the manager sees everything, including metrics, audit and users. This is enforced in the backend.
  - With no token, while `AUTH_REQUIRED` is off (the default until the login page exists): the read routes act as today, with the manager's view. Write actions always need a token.
  - **The organisers' contract routes stay open and unchanged.**
- **Officer actions**:
  - approve: refused over the limit or when the case is sensitive; then the officer must escalate
  - reject (with a reason)
  - edit reply: re-runs the self-check, saves the draft with the old → new diff, and approve stays locked while the check fails
  - send back: the agent re-runs with the officer's note as a new `reprocess` run; the autonomous run stays untouched
  - escalate, flag sensitive
- **Sensitive** means the customer is 65 or older (automatic) or a first-tier user flagged the case with a reason. A sensitive case always goes to the manager.
- **Fraud actions**: acknowledge (sends the holding reply; already built), log investigation / recall attempt, record outcome (confirmed fraud / not fraud / recall succeeded / recall failed). When the disputed transaction is over the analyst's limit, or the case is sensitive, the analyst escalates with a proposed outcome.
- **Manager actions**: second-tier approve or reject of escalations from both teams (reason required), reassign, and every first-tier action with no limit.
- **One gated send function** that every human send goes through: the right role, approved (by the manager if escalated), the reply passed the self-check, and not already sent.
- **Agent vs human**: the case detail shows the agent's autonomous decision next to the final action, plus what changed. The list can filter overridden cases.
- **More dashboard numbers** (new fields only):
  - SLA compliance %
  - complaints per day by category
  - approval turnaround
  - counts by channel and by reply language
  - refunds in RM (auto-paid, approved, awaiting, rejected)
  - counts of escalated, investigating and re-running cases
- **The UI guide (`docs/UI_API.md`)** gets updated with the login, the role rules, every action, the new fields and the changelog.

## Capabilities

### New Capabilities
- `platform-auth`: users, login, tokens, the `AUTH_REQUIRED` switch.
- `role-access`: what each role can see and do on `/api/*`, and assignment.
- `approval-workflow`: officer actions, limits, sensitivity, escalation, second-tier decisions, reassign, send back, the gated send.
- `fraud-workflow`: acknowledge → investigate → record outcome, and fraud escalation.
- `agent-vs-human`: the final action next to the agent's decision, and the overridden filter.
- `ops-metrics-more`: the added dashboard numbers.

### Modified Capabilities
<!-- None archived. The b-ops-read-api list and detail gain fields additively. The contract routes are unchanged, except that a case escalated or being re-run on the platform can't be approved through POST /cases/{id}/actions (409), so the two-tier rule can't be bypassed. -->

## Impact

- **New code**:
  - `backend/auth/` (`jwt.py`, `dependencies.py`, `router.py`), `backend/db/seed.py`
  - `backend/db/workflow.py` (the platform's state rules), `backend/api/actions.py`
  - tests
- **Changed**:
  - `backend/db/schema.py`: the `users` table, and new `cases` columns added by migration
  - `backend/db/store.py`: the gated send, `act()` uses the current run and refuses escalated cases
  - `backend/db/queries.py`: role filters, new fields, metrics
  - `backend/api/{cases,metrics,audit,contract}.py`, `backend/main.py` (the send-back worker)
  - `config.py`, `.env.example` (shared)
  - `docs/UI_API.md`, `docs/STATUS.md`
- **Not changed**:
  - `contracts.py` and Dev A's engine
  - `predictions.csv` (still the autonomous runs)
  - the contract responses; `api_check` is expected to stay 100.0 with 9/9 probes
- **Cost**: a send back makes one pipeline run (about RM0.002). Nothing else calls an LLM.
