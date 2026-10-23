# Status: what's done and what's left

This file tracks progress against [PLAN.md](PLAN.md). When you finish an item, tick it (`[x]`) in the same PR. Owners: **A** is Dev A (decision engine), **B** is Dev B (LLM, pipeline, DB, API), **UI** is the UI developer.

Last updated: 2026-10-23, after the S2 regeneration (`665f3bc`).

## Done

- **Agent pipeline** (Phase 1):
  - LLM extraction (DeepSeek v4 Flash), code matching, policy and refund (engine)
  - LLM replies (Claude Haiku 5.5), self-check in code, fallbacks when an LLM fails
- **Accuracy:** training score **100.00** (baseline 31.9), holdout top-1 99.4%, messy-text test set 99.4. Details in [EXTRACTOR_RESULTS.md](EXTRACTOR_RESULTS.md).
- **Submission file:** `submissions/Santa_Claude/predictions.csv`, 750 valid rows, regenerated with the reply-language fix (S2).
- **Database:**
  - `agent_runs` is immutable
  - `cases`
  - `case_events` (append-only audit)
  - `outbound_messages` (outbox)
- **The organisers' contract API** ([api.md](api.md)): `api_check` scores **100.0**, with 9/9 probes. Approve, edit & approve (self-check re-runs), reject, and fraud acknowledge are built.
- **UI read API** ([UI_API.md](UI_API.md)): `GET /api/cases`, `GET /api/cases/{id}`, `GET /api/metrics`, `GET /api/audit`. CORS is open; there's no login yet.
- **`backend.bat`:** double-click to start the backend on port 8000.
- **Bonus platform backend** (B1–B9, `b-ops-platform`):
  - logins for 4 seeded users, role-filtered reads
  - two-tier approval (officers RM2,000, fraud RM5,000, 65+ always to the manager)
  - escalate, second tier, reassign, send back, fraud steps
  - one gated send, agent vs human, more dashboard numbers

  `api_check` is still 100.0, with 9/9 probes. Documented in [UI_API.md](UI_API.md#login-roles-and-the-platform-actions).

## Core (main ranking)

- [ ] **C1 · Simple UI:** queues, one case (complaint, transaction, evidence, decision, reply, self-check), Approve / Edit & approve / Reject buttons. Needed for the 10-point human gate. *(UI, in progress; PLAN Phase 3)*
- [ ] **C2 · API reachable from the organisers' laptop** (venue Wi-Fi or a tunnel), for Checkpoint 2 on Day 2 at 12:00. *(B)*
- [x] C3 · Reply-language fix: `agent/language_mix.py` checks the LLM's mixed-language flag in code (no English word → not mixed; LLM says not mixed but English + Malay words → mixed). Training reply_language 98.4% → 100%, score 99.92 → 100.00 on the same cached clues; messy set unchanged; 8 of 750 test replies change language, each matching a labelled training pattern. **Regenerate `predictions.csv` (S2) to pick it up.** *(A, `feat/a-reply-language`)*
- [x] C4 · `categories/fee.py` fee-type match fixed: changed `any()` to `all()` for word matching, so "debit card annual fee" no longer matches "credit card annual fee". CMP-00010 now confidently matches the correct transaction. 2,334 tests pass. *(A, `feat/a-fee-type-fix`)*
- [x] C5 · **Second-issue check** (`b-second-issue`): a complaint raising a second, different problem is held for an officer ("Complaint raises a second issue"); the reply mentions it in one sentence. LLM issues check plus code quote verification; final test half 16/16 caught, 0 false flags on 2,604 complaints; scores unchanged. Kill switch `LLM_ISSUES=off`. *(B, agreed with A)*

## Bonus platform backend (PLAN 2.2–2.4)

- [x] **B1 · Login:** `users` table, 3 seeded users (officer1, fraud1, manager1), `POST /api/auth/login`, `GET /api/auth/me` (JWT). *(B)*
- [x] **B2 · Role checks** on every `/api/*` route, and role-filtered queues: the officer sees approval cases, the fraud analyst sees fraud cases, the manager sees all. The contract routes stay open. *(B)*
- [x] **B3 · New case fields:** workflow status, final outcome / refund / reply, approved by, sensitive, assigned to, escalated to. *(B)*
- [x] **B4 · Officer actions:** approve (limit check), reject, edit reply (self-check, diff, clears the approval), send back (agent re-run), escalate, flag sensitive. *(B)*
- [x] **B5 · Manager actions:** second-tier approve / reject, reassign. *(B)*
- [x] **B6 · Fraud actions:** log investigation / recall attempt, record outcome (acknowledge is done). *(B)*
- [x] **B7 · One send function** for every human-gated send: right role, approved (second tier if escalated), reply passed the self-check, not already sent. *(B)*
- [x] **B8 · Agent vs human comparison** for overridden cases. *(B)*
- [x] **B9 · More dashboard numbers:**
  - SLA compliance %
  - trends over time
  - approval turnaround
  - by channel and language
  - total refunds in RM

  *(B)*

## Bonus screens (PLAN Phase 3, after C1)

- [ ] U1 · Login page, role-based redirect, role-aware menu *(UI)*
- [ ] U2 · Officer Resolution Desk: limit headroom, "Escalate" instead of "Approve" when over the limit *(UI)*
- [ ] U3 · Fraud Investigation Workbench: auth method, timeline, acknowledge → investigate → outcome *(UI)*
- [ ] U4 · Manager Console: tiles, escalation queue, all cases, audit log, agent vs human *(UI)*
- [ ] U5 · Intake form, for rehearsing. Optional. *(UI)*

## Bonus extras (PLAN Phase 4, only if time is left)

- [ ] X1 · WebSocket live push (`/ws`); polling stays as the fallback *(B + UI)*
- [ ] X2 · Manager charts (the data is mostly in `/api/metrics`) *(UI)*
- [ ] X3 · Chatbot panel (`POST /api/chat`, read-only) *(B + UI)*
- [ ] X4 · SLA timers and notifications *(UI)*

## Small optional backend items

- [ ] O1 · `GET /api/export/predictions` (today: `python -m backend.batch.submit`) *(B)*
- [ ] O2 · Retry for cases that failed (`status: error`) *(B)*
- [ ] O3 · `inbox/` folder watcher or CSV-paste intake *(B)*

## Day 2: submission and demo (PLAN Phase 5)

- [ ] S1 · Run `scoring/api_check.py` against the served URL **from another laptop** (before 12:00) *(B)*. From the serving laptop over Wi-Fi (`http://10.0.30.131:8000`, `main` at `665f3bc`): 100.0, 9/9 probes; 20 at once 100.0, slowest 6.2s. The other-laptop run is still to do.
- [x] S2 · Final rerun of changed test complaints, then regenerate and validate `predictions.csv`, and record the final training score (before 15:00) *(B)*. `665f3bc`: 750/750 valid; scored fields unchanged except reply_language on 12 rows (C3); RM0.0136. Final training score **100.00** (1,750 complaints, 0 critical errors).
- [ ] S3 · `dev` → `main`, then PR `Submission: Santa_Claude` with `predictions.csv`, the freeze commit hash and the API URL (before 15:00) *(B)*
- [ ] S4 · End-to-end demo test of the 3 flows: within the limit, over the limit → manager, fraud *(all, after B and U)*
- [ ] S5 · Live-round rehearsal: post example and messy complaints, watch them appear in the UI, approve one *(all, after C1)*
- [ ] S6 · Fill the demo database with the 750 test cases: `python -m backend.batch.runner --ids test --db backend/api.db` *(B)*
- [ ] S7 · Keep the server running from 15:00 until the demo; keep the laptop awake *(B)*
- [ ] S8 · Run guide `docs/RUNNING.md`: start, fill, regenerate, check *(B)*

## Bonus decisions (Dev B, 2026-10-23)

- 65+ customers are always sensitive (they go to the manager); a manual flag also counts.
- Send back is built.
- The contract route stays open (typed name, no limits) but refuses escalated, re-running and closed cases.
- All five dashboard additions are built. `AUTH_REQUIRED` stays off until the UI's login page exists.
- Limits: officers RM2,000, fraud analyst RM5,000, manager none.
