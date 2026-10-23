# Frontend Build Guide

Screen-by-screen plan and build order for the React UI in `frontend/` (Dev C).

**Source of truth:** [UI_API.md](UI_API.md) (endpoints, JSON, errors), [api.md](api.md), [PLAN.md](PLAN.md) Phase 3 and [STATUS.md](STATUS.md) (C1, U1–U5, X1–X4). The frontend builds only against UI_API.md; a missing backend field goes to Dev B instead of being worked around. How cases move: [USERFLOW.md](USERFLOW.md).

---

## Run it locally

```bash
# 1. Backend (repo root, once: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt)
.venv\Scripts\python -m backend.batch.runner --ids pilot --db backend/api.db   # fill 50 cases (once)
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000  # or double-click backend.bat

# 2. Frontend
cd frontend
npm install        # once
npm run dev        # http://localhost:5173, proxies /api to http://127.0.0.1:8000
```

Sign in as `officer1`, `officer2`, `fraud1` or `manager1`, password `teratai123`. To see a new complaint arrive on its own, post one: `curl -X POST 127.0.0.1:8000/complaints -H "content-type: application/json" -d @examples/live_complaint_example.json` (change the `complaint_id` each time). The backend's database is `backend/api.db`; delete it (server stopped) to start empty.

| Script | What |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Typecheck + production build |
| `npm run preview` | Serve the built app (same `/api` proxy as dev) |
| `npm test` / `npm run test:watch` | Unit tests for the business rules (Vitest) |
| `npm run typecheck` / `npm run lint` | TypeScript / oxlint |

`VITE_API_URL` points a built UI at another machine's backend; `BACKEND_URL` changes the dev and preview proxy target.

**On another laptop (venue Wi-Fi):** run the backend with `--host 0.0.0.0` (`backend.bat` does), then either `npm run dev -- --host` or `npm run build && npm run preview -- --host`, and open `http://<your-ip>:5173` (dev) or `:4173` (preview). With `AUTH_REQUIRED=true` in the backend's `.env` the UI works unchanged (verified): reads without a token get 401, which signs the user out.

**Tests** cover the rules where a mistake would be costly: approval limits and escalation (including RM2,000.00 vs RM2,000.01, sensitive, locked Approve), who may act on which case, the reply highlighter that marks invented IDs and amounts, auto-advance, CSV and intake parsing, money and time formatting, SLA states, the 65+ age rule, and audit wording.

---

## Stack and structure

React 19 · TypeScript 6 (strict) · Vite 8 · Tailwind CSS 4 (CSS-first tokens) · React Router 8 · Lucide icons · oxlint. No component library. Fonts are self-hosted: Geist for headings and KPIs, Inter for everything else.

```
frontend/src/
├── api/          client.ts (fetch, token, ApiError), auth.ts, cases.ts (list, get, act), metrics.ts, audit.ts, users.ts
├── assets/       teratai-logo.png
├── components/
│   ├── layout/   AppLayout, Sidebar, UserCard, Page, route guards, navigation.ts
│   ├── shared/   Badge (+ Priority, Queue, Workflow, Category, Hold, Vulnerable, Simulated), SLATimer,
│   │             Button, TextField, Card, Banner, StatusMessage
│   └── case/     Case page parts: CaseBanners, CaseSla, CaseLoadError (and the 9b–9d cards)
├── context/      auth-context.ts, AuthProvider.tsx
├── hooks/        useAuth, useApi, useCaseDetail, useNow
├── lib/          types.ts (UI_API.md mirror), format, clock, sla, case, labels, paths, cx
├── pages/        Login, CaseDetail, OfficerDesk, FraudWorkbench, ManagerConsole, Intake
├── styles/       tokens.css (colour system + TUNABLE layout tokens), base.css
├── routes.tsx    URL → page + role access
└── App.tsx       providers + router
```

**Conventions (UI_API.md):**
- Money is a 2-decimal string and Cost a 4-decimal string: format with `formatMoney`, never `parseFloat`.
- Times are Malaysia time with no offset: parse by parts (`lib/format.ts`), never `new Date(string)`. Display `DD-MM-YYYY HH:MM`.
- SLA timers run on the real current time (Malaysia time). The dashboard leaves `as_of` out, so the backend measures as of now.
- Errors: `ApiError.status`, `.message`, `.problems` (refused reply) and `.limit` (over-limit refusal). 404 also means "another team's case". 409 means the case moved on: re-fetch.
- Design tokens only (`bg-card`, `text-secondary`, `rounded-card`…). Spacing, radius and shadow are tunable in `styles/tokens.css`.

---

## Done

| Piece | |
|---|---|
| Foundation | Formatting, clock, API client, login state, routes + role guards, design tokens + fonts, layout (borderless sidebar + bordered panel), Login page, shared badges |
| Alignment | Types mirror UI_API.md; real backend instead of a mock; error shapes; queue and workflow badges |
| Case page, read side | Header, SLA timers, banners; complaint, customer, **evidence per category**, match candidates, decision with calculation, **reply with invented IDs and amounts marked**, agent vs people, cost and speed, timeline with simulated outbound. Polls every 2 s only while the agent is working |
| **B1. Cases page** | Queue tabs with live counts per role, polled every 4 s so new complaints appear on their own; sort, paging. **Search and filters** (case / customer / subject, category, priority, hold, workflow with counts, assigned to me or unassigned, sensitive, and for the manager "changed by people"); tab, sort and filters all live in the URL. Rows show who closed a case, the holding reply being sent, manual sensitive flags, people overriding the agent, and agent errors |
| **Auto-advance** | After approve, reject, send back, escalate, a second-tier decision or recording an outcome, the next case that needs *you* opens (officer: untouched approval cases; analyst: unacknowledged fraud cases; manager: the next escalation), with a dismissible note; the queue if nothing is waiting. Edit, flag, log, acknowledge and reassign keep you on the case |
| **Case page, full** | Adds **what the agent understood** (the clues), the **fraud outcome**, the **agent run history** with a banner when the page shows a re-run (the first run is the scored one), what the manager is being asked to approve (the escalation **proposal**), the person's reason, versions, reversals and related transactions |
| **Manager console** | Escalations first, then 16 tiles in four groups (right now, the agent, people, refunds) and a chart for every breakdown `/api/metrics` returns (per-day trend, category, outcome, route, priority, holds, workflow, channel, language) plus models and throughput. Single-hue bars with the value at the tip, hover details and a Chart / Table switch on each |
| **Audit log** | Adds From / To dates (`since` / `until`) |
| **Policy page** (manager only, `/policy`) | The bank's fixed rules, read-only: the decision rule for each category, the limits and thresholds (including the routing and reply-language rules), the fee schedule, the service levels, and who may approve what (live approval limits from `GET /api/users`, plus the escalation rules). There is no backend route for policy, so it reads the same `data/*.csv` files the backend applies, at build time (alias `@data`); tests read the real files and fail if one changes shape |
| **Quality** | Responsive layout (icon rail below 1280 px), 85 unit tests, production preview proxy, `AUTH_REQUIRED=true` verified |
| **B3. Actions** | One decision bar and dialog for **every** platform action, with the rules in `lib/actions.ts` (headroom, escalate instead of approve, locked approve on a flagged reply, assigned-elsewhere and re-running notices). Covers the officer's and the fraud analyst's whole flow and the manager's second-tier approve / reject |

---

## Build order

### B. Core UI (STATUS C1: main ranking, the 10-point human gate): done

Every check in the human-gate checklist ([USERFLOW.md §4](USERFLOW.md#4-flow-b-the-live-round-readme)) is visible: a new case appears on its own, the matched transaction, evidence, decision, route, reply and self-check are on the case page, approval waits for a click, and fraud cases sit in the fraud queue.

### C. Bonus role screens (STATUS U1–U4)

| Piece | Status |
|---|---|
| **U1 Login, role redirect, role-aware menu** | Done |
| **U2 Officer Resolution Desk** | Done: approval queue, headroom, Escalate instead of Approve over the limit or when sensitive, Send back, Flag sensitive, Edit reply with the self-check result beside it |
| **U3 Fraud Investigation Workbench** | Done: fraud queue; auth method in large type; Acknowledge → Log investigation / recall → Record outcome; Escalate with a proposed outcome |
| **U4 Manager Console** | Done: `/manager` has nine metric tiles (`GET /api/metrics`, polled every 10 s) and the escalation queue (`workflow=escalated`, both teams, with who escalated and why; second-tier approve / reject on the case page). `/cases` shows every queue. `/audit` is the audit log with filters from the log's own facets, "people only", load more and **CSV export**. **Reassign** is a manager button on every open case (people from `GET /api/users`) |

### D. Extras: done

- **Charts** (X2): the manager console (see above).
- **Intake** (U5): `/intake` posts to `POST /complaints` (the contract route, proxied in dev and preview) from a form or pasted CSV rows in the live-round format, and shows each complaint's result; the manager also sees it tracked live to its queue. The judges post to the API directly.
- Not planned (PLAN.md): WebSocket push, chatbot panel, notifications. Polling is enough.

---

## What the UI uses from the backend

Every route in `docs/UI_API.md` is used: `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/cases`, `GET /api/cases/{id}`, all 12 platform actions, `GET /api/metrics`, `GET /api/audit`, `GET /api/users`, and the organisers' `POST /complaints`. The contract routes `POST /cases/{id}/actions` and `/acknowledge` are for the judges and `api_check.py`; the UI uses the platform actions, which add limits and roles. Every section of the case detail is shown, and every metric from `/api/metrics` is a tile, a chart or in the "Agent activity" card. Left out on purpose: the customer's email address (not needed to decide), the reply's `found_*` lists (the highlighter uses `allowed_*`, which is stricter), and the outbound `status` (always sent in this simulation).

## Open requests for Dev B (not blockers)

0. **A real bug: one shared database connection.** `backend/db/store.py` opens a single SQLite connection (`check_same_thread=False`) and every request uses it at once. When a page sends several requests together, some collide: the backend log shows `sqlite3.InterfaceError: bad parameter or other API misuse` inside `get_user`, followed by `401` on valid logins, so people were signed out at random. Fix: a lock around the connection, or one connection per request or thread. The frontend now retries a 401 once before signing anyone out, which hides the symptom but does not cure it.

1. **Related transactions on the same account** for the fraud workbench (PLAN §3.4). `evidence.related_txns` only carries a duplicate's earlier charge, so the UI shows what it is given.
2. **A customer search** (`GET /api/customers?q=`) for autocomplete on the Intake form; today the customer ID is typed.
3. **A retry for failed cases** (STATUS O2): the UI shows an agent error but has nothing to call.
4. **An outbound-messages list** (`GET /api/outbound`) if a cross-case "nothing was sent without a human" view is wanted; today each case's timeline shows its own simulated messages.
5. **Names with people.** Actors, assignees and escalators come back as usernames, and only the manager can list users, so an officer sees other people as a tidied username. Return `full_name` beside them, or open a read-only name list to every signed-in role.

---

## Demo checklist (PLAN.md Phase 5)

1. Fill the backend with the 750 test cases (Dev B, STATUS S6) and keep it running.
2. **Human gate rehearsal:** post a complaint and watch it appear on its own; open it (transaction, evidence, decision, route, reply, self-check); approve one; check that a fraud complaint lands in the fraud queue.
3. **Bonus flows:** within the limit → officer approves; over RM2,000 → escalate → manager approves; fraud → acknowledge → investigate → record outcome.
4. Show the audit log, agent vs human, and an edited reply with an invented amount being refused.
