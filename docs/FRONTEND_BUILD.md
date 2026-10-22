# Frontend Build Guide

Screen-by-screen spec and build order for the React frontend in `frontend/`.

**Source of truth:** [PLAN.md](PLAN.md) (Phase 3 and Phase 4, data model, API) and [backend/contracts.py](../backend/contracts.py). The frontend mirror of the contract is [frontend/src/lib/types.ts](../frontend/src/lib/types.ts). How cases move: [USERFLOW.md](USERFLOW.md).

---

## Timeline (PLAN.md)

| When | Frontend work |
|---|---|
| Day 1 → Day 2 12:00 | Backend delivers the core; until Checkpoint 2 it is demoed through FastAPI `/docs`. Frontend foundation only (done: scaffold + contract mirror) |
| **Day 2 10:00–13:00, Phase 3** | Foundation → Login → Intake → Officer Resolution Desk → Fraud Workbench → Manager Console |
| Day 2, after Phase 3 passes the three-case demo, **Phase 4** | Bonus extras, each with a fallback: WebSocket push, manager charts, chatbot panel, SLA timers + notifications |
| Day 2 13:00–15:00, Phase 5 | Demo rehearsal (USERFLOW.md §11) |

**Cut line:** Phase 3 is required for the bonus MVP. Phase 4 items are optional and must never break Phase 3.

---

## Stack

| Concern | Choice |
|---|---|
| Build | Vite 8 + TypeScript 6 (strict) |
| UI | React 19 |
| Styling | Tailwind CSS 4 (Vite plugin, CSS-first config; no `tailwind.config.ts`) |
| Lint | oxlint |
| HTTP | `fetch` wrapper in `src/api/` with JWT header |
| Icons | Lucide React (when first needed) |
| Charts | Recharts (Phase 4 only) |

> **Open with the team:** PLAN.md lists React 18 + shadcn/ui + Axios. The frontend currently uses React 19 and Tailwind v4 without shadcn/ui. Update PLAN.md or the frontend so they match.

---

## File structure (PLAN.md)

```
frontend/src/
├── main.tsx
├── App.tsx
├── api/                   # fetch + JWT; auth, cases, intake, audit, metrics, chat
├── context/               # Auth, WebSocket (Phase 4)
├── hooks/                 # useAuth, useCases, useWebSocket
├── pages/
│   ├── Login.tsx
│   ├── OfficerDesk.tsx    # Resolution desk
│   ├── FraudWorkbench.tsx # Investigation workbench
│   ├── ManagerConsole.tsx # Metrics + escalations + all cases + audit
│   ├── CaseDetail.tsx     # Shared, adapts to role
│   └── Intake.tsx         # Live-round complaint form
├── components/
│   ├── layout/            # Sidebar, Header, ProtectedRoute
│   ├── dashboard/         # KPIs, charts (manager)
│   ├── officer/           # ReplyEditor, ApprovalActions, EvidencePanel
│   ├── fraud/             # TxnDetail, AuthMethod, Timeline, InvestigationLog
│   ├── manager/           # EscalationQueue, AuditLog, OverrideRate
│   ├── chat/              # ChatPanel, ChatMessage, ChatInput (Phase 4)
│   └── shared/            # PriorityBadge, StatusBadge, SLATimer, CategoryBadge, SimulatedBadge
└── lib/                   # types.ts (contract mirror), money/date formatting, utils
```

---

## Foundation

### F1. Contract mirror ✅
[src/lib/types.ts](../frontend/src/lib/types.ts) mirrors `contracts.py` and the PLAN.md tables. Keep it in step with every contract PR.

**Wire-format rules every screen follows:**
- **Money** arrives as a Decimal string (`"550.00"`). Display as `RM550.00` with thousands separators. Never do arithmetic on floats; compare limit vs refund on the backend's decision (the backend blocks over-limit approval anyway).
- **Datetimes** arrive as naive MYT (`"2026-09-30T10:15:00"`). Parse the parts directly; never `new Date(str)`, which treats them as UTC or local. Display `DD-MM-YYYY HH:MM:SS`.
- **Evidence rows** are raw CSV rows: string values, and an empty string means absent.

### F2. API layer (`src/api/`)
One `request<T>()` wrapper: base URL from `VITE_API_URL`, JWT from the auth context, JSON in/out. Non-2xx throws with FastAPI's `{ detail }`. One module per resource: `auth`, `cases`, `intake`, `audit`, `metrics`.

### F3. Auth + layout
- `AuthContext`: token and `User` from `GET /api/auth/me`.
- `ProtectedRoute`: redirects a role away from screens it can't use. **The backend enforces roles; the UI only hides.**
- Layout: sidebar (nav depends on the role, with badge counts) and header (user, role, approval limit, notifications).

### F4. Shared components (`components/shared/`)
`PriorityBadge`, `StatusBadge` (all 10 `CaseStatus` values), `CategoryBadge`, `SLATimer`, `SimulatedBadge`. Add others only when a second screen needs them.

### F5. Polling
Queues poll `GET /api/cases` (e.g. every 5 s). WebSocket push is Phase 4 and layers on top.

---

## Phase 3 screens (required)

### 1. Login · `/login` (`pages/Login.tsx`)
- Username and password → `POST /api/auth/login` → store the JWT.
- Redirect by role: officer → Resolution Desk, fraud → Investigation Workbench, manager → Console.
- Seeded users: `officer1`, `fraud1`, `manager1`.

**Done when** each role lands on its own screen and the backend rejects it on other roles' endpoints.

### 2. Intake · `/intake` (`pages/Intake.tsx`, all roles; critical for the live round)
- **Form:** `complaint_id`, `customer_id` (with search/autocomplete), `received_at`, channel dropdown (`COMPLAINT_CHANNELS`), subject, text.
- **Or paste one CSV row** in the live-round format (`complaint_id,customer_id,received_at,channel,subject,text`). Handle quoted commas.
- `received_at` accepts `YYYY-MM-DD HH:MM`, `DD-MM-YYYY HH:MM` or `DD/MM/YYYY HH:MM`.
- Submit → `POST /api/intake` → poll the returned case ID and show **processing** until it settles.
- Show the result: status, route, `hold_reason` if any, and a link to the case.
- A note that dropping a CSV into `inbox/` goes through the same path.

**Done when** the README example row submits, shows processing, and lands in the right queue with no code changes.

### 3. Case Detail · `/cases/:id` (`pages/CaseDetail.tsx`, shared, adapts to role)
Data: `GET /api/cases/{id}` returns `CaseDetail` (the case, autonomous run, current run, events, outbound).

**Header:** complaint ID, channel, received time, `PriorityBadge`, `CategoryBadge`, route, `StatusBadge`, `SLATimer` (ack and resolve), the hold reason if held, "Sensitive" with its reason, and the escalation banner for the manager.

**Evidence panel** (`components/officer/EvidencePanel`), from `current_run.evidence`:

| Category | Show |
|---|---|
| DUPLICATE_CHARGE | `matched_txn` (later charge) beside `related_txns[0]` (earlier): times, card, merchant, amount. The handler doesn't set `evidence.reversal`; "already reversed" comes from `rule_id = DUP.ALREADY_REVERSED` and `calculation` |
| FAILED_TRANSFER | `matched_txn.status`, `reversal` or "no reversal", recipient, `counterparty_bank`, `counterparty_account` |
| ATM_NOT_DISPENSED | `atm_journal`: requested, dispensed, `journal_status`, location |
| UNAUTHORISED_CARD | `matched_txn.auth_method` prominently, `merchant_country`, `card_last4` |
| SCAM_TRANSFER | Recipient, bank, account, time, amount |
| FEE_DISPUTE | `matched_txn` fee, `fee_schedule_row`, the account (product, `open_date`) |
| SERVICE_QUALITY | "No transaction involved" |

Also show:
- **Customer:** from `evidence.customer`, with "Unknown customer" when null; `decision.vulnerable` badge; accounts.
- **Match:** `match.status`, and `match.candidates` with score and `reasons`. Ambiguous or none is shown first, in amber. "Category revised" if `match.category_revised`.

**Decision panel:**
- outcome, `refund_amount_myr`, priority, reply language, route
- `policy_route` when it differs from `route` (a hold moved it)
- `rule_id` and `calculation.explanation`

**Reply:**
- `reply_text` with a self-check badge
- problems listed from `self_check.problems`
- highlight in the text any `found_txn_ids` or `found_amounts` not in `evidence.allowed_txn_ids` or `allowed_amounts`

**Agent vs human:** the autonomous run's decision beside `case.final_outcome`, `final_refund_myr` and `final_reply_text`. If a reprocess run exists, show it as the current run.

**Observability:** `extract_usage` and `draft_usage` (provider, model, tokens, `cost_myr`, `latency_ms`, cached), `redraft_count`, `prompt_version`, `policy_version`.

**Timeline:** `events` (actor, action, reason, old → new, self-check result). Outbound records are shown with `SimulatedBadge`.

### 4. Officer Resolution Desk · `/officer` (`pages/OfficerDesk.tsx`, HUMAN_APPROVAL)
Designed for speed: get the correct reply to the customer quickly.

- **Queue:** `GET /api/cases?route=HUMAN_APPROVAL`, sorted by priority, then SLA due. Lanes P1 → P2 → P3.
- **Each row:** priority, category, customer, outcome and refund, `SLATimer`, and **why it's waiting**: "Refund > RM500", "Decline needs approval", or the hold label (USERFLOW.md §2).
- **Opening a case** shows Case Detail, leading with the **editable reply**, then the decision, refund and calculation, the evidence panel and the self-check badge.
- **Approval headroom:** "Your limit: RM5,000. This refund: RM550. ✓".

**Actions** (`components/officer/ApprovalActions`), always in this order: Reject · Escalate · Edit · Approve

| Action | Endpoint | UI rule |
|---|---|---|
| Approve | `POST /approve` | Over limit or sensitive: replaced by **"Escalate to Manager"**. Disabled unless the self-check passed |
| Edit | `POST /edit-reply` | Shows the returned check result; problems are highlighted in the text; Approve stays locked until it passes. Any prior approval is cleared |
| Reject | `POST /reject` | Reason, final outcome, final refund and reply. The reply must pass the self-check |
| Send back | `POST /send-back` | Reason; the case returns as `processing` |
| Escalate | `POST /escalate` | Reason required |
| Flag sensitive | `POST /flag-sensitive` | Reason required; forces escalation |

- After an action, auto-advance to the next case.
- Disable buttons while a request is in flight (the backend also guards double clicks).

### 5. Fraud Investigation Workbench · `/fraud` (`pages/FraudWorkbench.tsx`, FRAUD_TEAM)
Long-lived cases, not a quick approve.

- **Queue:** `GET /api/cases?route=FRAUD_TEAM`, sorted by priority, then SLA.
- **Workbench leads with** (`components/fraud/`):
  - `TxnDetail` and `AuthMethod`: the suspicious transaction and its `auth_method` (3DS-OTP / Chip+PIN / None)
  - related transactions on the same account
  - `Timeline` of status progression
- The holding reply is shown read-only, with its outbound record once released.

**Actions:**
1. **Acknowledge** → `POST /acknowledge` (releases the holding reply; status `investigating`).
2. **Log investigation / recall** → `POST /investigate`.
3. **Record outcome** → `POST /record-outcome` (`FRAUD_OUTCOMES`).
4. **Escalate** (sensitive, or disputed amount over the analyst's limit) → `POST /escalate`.

### 6. Manager Console · `/manager` (`pages/ManagerConsole.tsx`)
Only role that sees everything.

| Section | Contents | Endpoint |
|---|---|---|
| **Metrics tiles** (`dashboard/`) | Throughput, auto-resolve rate, SLA compliance, override rate, self-check catches, cost and latency per complaint | `GET /api/metrics` |
| **Escalation queue** (`manager/EscalationQueue`) | Merged from both teams; what the first tier did and why. Second-tier approve / reject with a reason | `GET /api/cases?status=escalated`, `POST /second-tier-approve`, `/second-tier-reject` |
| **All cases** | Filter by queue, category, priority, status, officer; reassign. AUTO_RESOLVE read-only | `GET /api/cases`, `POST /reassign` |
| **Audit log** (`manager/AuditLog`) | Append-only, expandable rows, edit diffs, export | `GET /api/audit` |
| **Agent vs human** (`manager/OverrideRate`) | Autonomous run beside final action for every overridden case | case detail |

---

## Phase 4 extras (optional, each with a fallback)

| Extra | What | Fallback |
|---|---|---|
| WebSocket live push | `WebSocket /ws` pushes new cases and status changes | Polling keeps working if the socket drops |
| Manager charts | Recharts: category, priority and route breakdowns, SLA trend, on top of `GET /api/metrics` | Tiles work without them |
| Chatbot panel | Slide-out from Case Detail; `POST /api/chat` (SSE); explains reasoning and policy; **read-only** | Case Detail stands alone |
| SLA timers + notifications | Live countdown bars (amber under 35%, red overdue) against the labelled demo clock; new-case alerts per role | Static due times |

---

## Demo checklist (PLAN.md Phase 5)

1. Live round: paste a CSV row into Intake (and drop one into `inbox/`), then watch it flow through.
2. Case A: officer approves a refund within the limit → "sent (simulated)".
3. Case B: officer escalates an over-limit refund → manager second-tier approves → "sent (simulated)". See the data note in USERFLOW.md §11.
4. Case C: analyst acknowledges a fraud case (holding reply released) → logs investigation.
5. Show the audit log, the agent-vs-human gap, and the self-check blocking an edited reply with an invented amount.
