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
| `npm run typecheck` / `npm run lint` | TypeScript / oxlint |

`VITE_API_URL` points a built UI at another machine's backend; `BACKEND_URL` changes the dev proxy target; `VITE_DEMO_DATE` changes the demo clock date (default 2026-09-30).

---

## Stack and structure

React 19 · TypeScript 6 (strict) · Vite 8 · Tailwind CSS 4 (CSS-first tokens) · React Router 8 · Lucide icons · oxlint. No component library. Fonts are self-hosted: Geist for headings and KPIs, Inter for everything else.

```
frontend/src/
├── api/          client.ts (fetch, token, ApiError), auth.ts, cases.ts (list, get, act)
├── assets/       teratai-logo.png
├── components/
│   ├── layout/   AppLayout, Sidebar, UserCard, DemoClock, Page, route guards, navigation.ts
│   ├── shared/   Badge (+ Priority, Queue, Workflow, Category, Hold, Vulnerable, Simulated), SLATimer,
│   │             Button, TextField, Card, Banner, StatusMessage
│   └── case/     Case page parts: CaseBanners, CaseSla, CaseLoadError (and the 9b–9d cards)
├── context/      auth-context.ts, AuthProvider.tsx
├── hooks/        useAuth, useApi, useCaseDetail, useDemoNow
├── lib/          types.ts (UI_API.md mirror), format, clock, sla, case, labels, paths, cx
├── pages/        Login, CaseDetail, OfficerDesk, FraudWorkbench, ManagerConsole, Intake, dev/UiKit
├── styles/       tokens.css (colour system + TUNABLE layout tokens), base.css
├── routes.tsx    URL → page + role access
└── App.tsx       providers + router
```

**Conventions (UI_API.md):**
- Money is a 2-decimal string and Cost a 4-decimal string: format with `formatMoney`, never `parseFloat`.
- Times are Malaysia time with no offset: parse by parts (`lib/format.ts`), never `new Date(string)`. Display `DD-MM-YYYY HH:MM`.
- SLA timers run on the **demo clock** (30-09-2026 at the current time of day). The dashboard passes the same clock as `as_of`.
- Errors: `ApiError.status`, `.message`, `.problems` (refused reply) and `.limit` (over-limit refusal). 404 also means "another team's case". 409 means the case moved on: re-fetch.
- Design tokens only (`bg-card`, `text-secondary`, `rounded-card`…). Spacing, radius and shadow are tunable in `styles/tokens.css`.

---

## Done

| Piece | |
|---|---|
| Foundation | Formatting, demo clock, API client, login state, routes + role guards, design tokens + fonts, layout (borderless sidebar + bordered panel), Login page, shared badges, dev UI kit (`/dev/ui`) |
| Alignment | Types mirror UI_API.md; real backend instead of a mock; error shapes; queue and workflow badges |
| Case page 9a | Data loading, header (category, priority, queue, workflow, route), SLA timers, banners (error, processing, escalated, held, sensitive), not-found and retry states |

---

## Build order

### B. Core UI (STATUS C1: main ranking, the 10-point human gate)

Build first. Every check in the human-gate checklist ([USERFLOW.md §4](USERFLOW.md#4-flow-b-the-live-round-readme)) must be visible.

| Piece | Screen | Endpoint |
|---|---|---|
| **B1. Cases page** | Queue tabs with count badges from `counts`: Awaiting approval · Fraud team · Auto-resolved · Approved · Rejected · Processing · Error. Rows show priority, category, customer, outcome and refund, `waiting_reason`, hold, vulnerable, self-check, resolve SLA. **Polls every 3–5 s**, so new cases appear on their own (`sort=recent` option). Click → case page | `GET /api/cases?queue=…` |
| **B2. Case page cards** | Complaint (text, channel, language); customer and accounts; **evidence per category** (duplicate pair, transfer status and reversal, ATM journal, auth method, scam recipient, fee row); match candidates; **decision** (outcome, refund, priority, route, policy route vs held route, rule, calculation); **reply + self-check** (found IDs and amounts not in `allowed_*` highlighted); timeline (`events`) and outbound (Simulated); usage (cost, latency, models). Polls every 2 s while processing or re-running | `GET /api/cases/{id}` |
| **B3. Actions** | Approve · Edit reply (shows the self-check problems; Approve locked while flagged) · Reject, all with a reason · fraud Acknowledge. Disabled while a request is in flight; on 409 re-fetch; redraw from the response | `POST /api/cases/{id}/approve` · `edit-reply` · `reject` · `acknowledge` |

### C. Bonus role screens (STATUS U1–U4)

| Piece | Screen | Adds |
|---|---|---|
| **C1. Officer Resolution Desk** (U2) | Approval queue + case page with headroom ("Your limit: RM2,000. This refund: RM550. ✓"); **Escalate to manager** replaces Approve when over the limit or sensitive; Send back; Flag sensitive | `escalate`, `send-back`, `flag-sensitive`; the 403 `limit` error |
| **C2. Fraud Investigation Workbench** (U3) | Fraud queue; transaction and auth method first; timeline; Acknowledge → Log investigation / recall → Record outcome; Escalate when the disputed amount is over RM5,000 or sensitive | `investigate`, `record-outcome`, `escalate` with `outcome` |
| **C3. Manager Console** (U4) | Tiles; escalation queue (`workflow=escalated`) with second-tier approve / reject and the proposal; all cases with reassign; audit log; agent vs human (`overridden=true`) | `GET /api/metrics?as_of=`, `GET /api/audit`, `GET /api/users`, `second-tier-approve`, `second-tier-reject`, `reassign` |
| (U1 is done: Login page, role redirect, role-aware menu) | | |

### D. Extras (only if time is left)

- **Charts** (X2): `cases.by_category`, `by_priority`, `by_route`, `holds.by_reason`, `trends.received_by_day`
- **Intake form** (U5, optional): posts to `POST /complaints` for rehearsing; the judges post directly
- Not planned (PLAN.md): WebSocket push, chatbot panel, notifications. Polling is enough.

---

## Demo checklist (PLAN.md Phase 5)

1. Fill the backend with the 750 test cases (Dev B, STATUS S6) and keep it running.
2. **Human gate rehearsal:** post a complaint and watch it appear on its own; open it (transaction, evidence, decision, route, reply, self-check); approve one; check that a fraud complaint lands in the fraud queue.
3. **Bonus flows:** within the limit → officer approves; over RM2,000 → escalate → manager approves; fraud → acknowledge → investigate → record outcome.
4. Show the audit log, agent vs human, and an edited reply with an invented amount being refused.
