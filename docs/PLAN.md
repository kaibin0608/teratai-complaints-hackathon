# Teratai Bank Complaints Agent — Build Plan

Solo execution plan. Two days. Backend first, frontend second.

---

## Hackathon Scoring Reminder

**Main ranking (all teams):**

| Weight | Criterion | How judged |
|---|---|---|
| 30% | Accuracy | Leaderboard score on 750 test complaints |
| 25% | Agent design & guardrails | Live round: judges type 2-3 new complaints (CSV format, received_at = 2026-09-30) |
| 25% | Business value & demo | Reply quality, tone, language, judges read 10 replies |
| 20% | Engineering | Architecture, observability, cost/speed per complaint |

Per complaint (max 100 pts):
- matched_txn_id: 25 — outcome: 25 (gated on txn) — refund_amount_myr: 25 (gated on txn) — category: 10 — priority: 10 — reply_language: 5
- Critical errors (wrongful refund, missed fraud): `final = mean × (1 − 2 × error_rate)`

**Bonus: Best Ops Platform (separate award, does not affect main ranking):**
- Role separation (officer / fraud analyst / manager see only their cases)
- Two-tier approval (first tier up to limit, escalate to manager above)
- Self-check re-runs on human edits
- Append-only audit trail
- Agent decision immutable, separate from human final action

**Live round format:**
```
complaint_id,customer_id,received_at,channel,subject,text
LIVE-07,CUS-01234,2026-09-30 10:15,App chat,,"Hi, I was charged twice..."
```
Customer + transaction already exist in data. System must accept without code changes.

**Submission:** Fork repo, build in fork, PR from fork to upstream titled `Submission: <team-name>`. PR needs predictions.csv only; code stays in fork.

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    AGENT PIPELINE (core)                      │
│                                                              │
│  1. Intake (API endpoint / CSV file drop)                   │
│  2. Understand (Claude LLM) — extract clues from text       │
│  3. Match Transaction (Code) — 75 pts depend on this        │
│  4. Apply Policy (Code) — outcome, refund, priority, route  │
│  5. Draft Reply (Claude LLM) — bilingual, evidence-based    │
│  6. Self-Check (Code) — verify reply against evidence       │
│  7. Route & Store (Code) — queue assignment                 │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    FASTAPI BACKEND                            │
│  Auth (JWT) │ Cases API │ Approval API │ Intake │ Chat (SSE)│
│                    WebSocket for real-time push               │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      SQLite DB                               │
│  users │ cases (agent_decision immutable + final_action)    │
│  case_events (append-only audit) │ chat_sessions            │
└──────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│               REACT FRONTEND (Vite + TailwindCSS)            │
│  Login │ Officer Resolution Desk │ Fraud Investigation      │
│  Manager Console │ Intake Form │ Chatbot Panel               │
└──────────────────────────────────────────────────────────────┘
```

---

## Roles (3 roles, matching bonus_platform.md spec)

| Role | Sees | Can do | Approval limit |
|---|---|---|---|
| **Complaints Officer** | HUMAN_APPROVAL queue | Approve / edit reply / reject / send back. Escalate to manager if refund > their limit | e.g. RM 5,000 |
| **Fraud Analyst** | FRAUD_TEAM queue | Acknowledge / log investigation or recall attempt / record outcome. Escalate sensitive cases to manager | e.g. RM 5,000 |
| **Manager** | Both queues + escalation queue + audit log + dashboard metrics | Everything both tiers can do + second-tier approval for escalated cases. Only role that sees both queues | No limit |

### Two-tier approval flow

```
Case routed to HUMAN_APPROVAL or FRAUD_TEAM
         │
         ▼
   First tier reviews
   (officer or fraud analyst)
         │
    ┌────┴─────┐
    │          │
 Within     Over limit
 limit      or sensitive
    │          │
    ▼          ▼
 Approve    Escalate to Manager
 (done)     (case WAITS)
               │
               ▼
          Manager reviews
          second-tier approval
               │
          ┌────┴────┐
          │         │
       Approve   Reject
       (done)    (with reason)
```

---

## Data Model

### `cases` table
```
complaint_id          PK
customer_id
received_at
channel
subject
text

-- Agent decision (IMMUTABLE — what leaderboard scores)
agent_category
agent_matched_txn_id
agent_outcome
agent_refund_amount_myr
agent_priority
agent_reply_language
agent_route
agent_reply_text
agent_evidence         JSON — evidence pack used
agent_self_check       pass / flag
agent_confidence       high / medium / low
agent_reasoning        JSON — why it decided what it decided

-- Human final action (what actually happened)
status                 pending / approved / edited / rejected / sent_back /
                       escalated / investigating / closed
final_reply_text       NULL until human acts
final_outcome          NULL until human acts
assigned_to            user who owns it
escalated_to           manager username if escalated
sla_due_at             computed from sla_policy.csv
created_at
updated_at
```

### `case_events` table (append-only audit log)
```
id                    PK auto-increment
complaint_id          FK
actor                 username
action                approve / edit / reject / send_back / escalate /
                      acknowledge / investigate / record_outcome / second_tier_approve
field                 which field changed (e.g. reply_text, outcome)
old_value
new_value
reason                required on every action
self_check_result     pass / flag (re-run on edits)
created_at
```

### `users` table
```
username              PK
password_hash
full_name
role                  officer / fraud / manager
approval_limit_myr    e.g. 5000.00 (NULL for manager = no limit)
```

**Integrity rule:** `agent_*` fields never change after pipeline writes them. `final_*` fields and `status` change via `case_events`. The gap between agent and final is auditable and demo-worthy.

---

## Build Order — Backend First

### Phase 1: Agent Pipeline (Day 1, 09:00–16:00)

75 of 100 points per complaint depend on transaction matching. Nothing else matters if this is wrong.

**1.1 Project skeleton (30 min)**
- Backend folder structure, `.env` template, `requirements.txt`
- Wrap `starter/data.py` — load all CSVs, build indexed lookups

**1.2 Complaint Parser — LLM step (1.5 hrs)**
- Claude extracts structured JSON from complaint text:
  ```json
  {
    "category_hint": "DUPLICATE_CHARGE",
    "language": "MS",
    "amount_mentioned": 46.66,
    "amount_approximate": false,
    "merchant_name": "GoRide",
    "date_phrase": "hari Selasa lepas",
    "card_last4": null,
    "recipient_name": null,
    "counterparty_bank": null,
    "fee_type": null
  }
  ```
- Few-shot examples from training data (EN + MS + mixed)
- Date phrase stays as raw text — code resolves it next

**1.3 Date Resolver — Code (1 hr)**
- Relative dates anchored to `received_at`:
  - "yesterday" / "semalam" → day before received
  - "last Tuesday" / "hari Selasa lepas" → most recent Tuesday before received
  - "last week" / "minggu lepas" → 7-day window
  - "last month" / "bulan lepas" → calendar month before received_at (e.g., received Aug 15 → Jul 1–31)
  - Named month ("July" / "bulan Julai") → that calendar month in the most recent year within 45-day window
  - FEE_DISPUTE specifically: complaint_policy.csv says "the month the customer names" — resolve to that calendar month, not a rolling window
  - Exact dates pass through
- Output: (start_date, end_date) range

**1.4 Transaction Matcher — Code, THE CRITICAL PATH (2.5 hrs)**

Matching answers "which transaction is the customer talking about?" — it finds the transaction ID. Policy (step 1.5) answers "what should happen to it?" A complaint can refer to a completed transfer and still need a matched ID — the outcome is DECLINE, but the match is correct.

- Filter: customer's debits, within 45-day window (`MATCH_WINDOW_DAYS` from params)
- Multi-signal scoring: amount match (exact or ±5%), merchant/counterparty substring, date in range, card_last4, channel family
- Category-specific matching (find the transaction, don't decide outcome here):
  - **DUPLICATE_CHARGE:** find the disputed later card charge by amount, merchant, date. Then look for an earlier charge on **the same card** with same merchant and same amount. matched_txn_id = the later charge
  - **FAILED_TRANSFER:** match DuitNow/IBG transfer debit by recipient, amount, date — regardless of status or reversal. Match even if completed or reversed
  - **ATM_NOT_DISPENSED:** match ATM Withdrawal by amount, date, location — regardless of journal result. Match even if fully dispensed
  - **UNAUTHORISED_CARD:** match Card POS/e-Commerce debit by amount, merchant, date, card
  - **SCAM_TRANSFER:** match DuitNow/IBG transfer out by recipient, amount, date
  - **FEE_DISPUTE:** match Fee channel debit by fee type and month the customer mentions
  - **SERVICE_QUALITY:** no transaction, matched_txn_id = empty
- Confidence: if 1 candidate, high. If 0 or multiple, flag and pick best or none

**1.5 Policy Engine — Code (1 hr)**

Policy answers "what should happen?" given the matched transaction and its evidence. Reads `complaint_policy.csv` + `policy_parameters.csv`.

- Per category decision rules:
  - **DUPLICATE_CHARGE:** check same card, same merchant, same amount, within 10 min, neither reversed → REFUND later charge. If conditions don't hold (different cards, >10 min apart, already reversed) → DECLINE
  - **FAILED_TRANSFER:** check status and reversal. Failed + no reversal → REFUND. Has reversal → DECLINE (tell customer when returned). Status Completed → DECLINE (money reached recipient)
  - **ATM_NOT_DISPENSED:** check atm_journal. If dispensed < requested → REFUND the shortfall (requested - dispensed). If fully dispensed → DECLINE
  - **UNAUTHORISED_CARD:** check auth_method. None (no strong auth) → REFUND. 3DS-OTP or Chip+PIN → INVESTIGATE (fraud team, no refund now)
  - **SCAM_TRANSFER:** always INVESTIGATE (fraud team for recall attempt, no refund now)
  - **FEE_DISPUTE:** compute correct fee and refund any overcharge:
    1. Look up correct fee from `fee_schedule.csv`: match fee description prefix to `fee_name`, account `product` to fee's `product`
    2. Apply waivers to get `amount_due`:
       - Basic Savings monthly service charge: `amount_due = 0` (never chargeable)
       - Debit card annual fee: `amount_due = 0` if customer age >= 60 **on the charge date** (NOT received_at)
       - Credit card annual fee (Classic RM150 / Platinum RM250): `amount_due = 0` if charge date < first anniversary of account `open_date`
       - No waiver: `amount_due` = fee_schedule amount
    3. `refund = charged - amount_due`. If refund > 0 → REFUND that amount (includes both waiver and overcharge cases). Else DECLINE
    - Overcharge example: Current Account charged RM20 monthly, schedule = RM10 → refund RM10
    - Waiver example: CC Classic RM150, opened 6 months ago → first-year waiver → refund RM150
    - Correct example: Savings Plus RM2 monthly, no waiver → DECLINE
  - SERVICE_QUALITY: INFO_ONLY
- Priority: base from policy + bump one level if customer age >= 65 on received_at. P1 stays P1
- Reply language: complaint language. Mixed/call-centre → customer's `preferred_language`
- Route: INVESTIGATE → FRAUD_TEAM. DECLINE → HUMAN_APPROVAL. REFUND > RM500 → HUMAN_APPROVAL (boundary: RM500.00 exactly = AUTO_RESOLVE). INFO_ONLY → AUTO_RESOLVE. Else AUTO_RESOLVE

**1.6 Reply Generator — LLM step (1 hr)**
- Input: decision, evidence pack, reply_language, category
- Prompt enforces: professional bank tone, reference transaction if applicable, state decision clearly, no invented facts, correct language
- Template per category for consistency

**1.7 Self-Check — Code (30 min)**
- Reuse `starter/check_reply.py` logic
- Extract TXN-IDs (regex `TXN-\d{7}`) and amounts (regex `RM\s?[\d,]+\.?\d*`)
- Every ID and amount must exist in customer's evidence window
- Fail → redraft once with "Remove these invented facts: ..." → fail again → flag for human
- **Same check re-runs when human edits reply** (bonus requirement)

**1.8 Batch Runner + Score (1 hr)**
- Async parallel processing of all complaints
- Rate limiting for Claude API
- Cache LLM extraction results (don't re-call on retry)
- Write `submissions/<team>/predictions.csv`
- Score against training labels, analyze errors
- **Target: Checkpoint 1 by 16:00 — 20 training complaints classified + matched**

### Phase 2: FastAPI Backend + DB (Day 1, 16:00–17:30 + Day 2, 09:00–10:00)

**2.1 DB Schema + Auth**
- SQLite: `cases`, `case_events`, `users` tables (schema above)
- Seed users:
  - `officer1` — Complaints Officer, approval_limit_myr = 5000
  - `fraud1` — Fraud Analyst, approval_limit_myr = 5000
  - `manager1` — Manager, no limit
- JWT auth: login, token verify, role-based access middleware

**2.2 Core API Endpoints**
- `POST /api/auth/login` — returns JWT with role
- `GET /api/auth/me` — current user + role + approval_limit
- `GET /api/cases` — list with filters (category, priority, status, route). **Role-filtered:** officer sees HUMAN_APPROVAL only, fraud sees FRAUD_TEAM only, manager sees all
- `GET /api/cases/{id}` — full detail: agent decision + evidence + audit trail
- `POST /api/cases/{id}/approve` — first-tier approve (checks approval_limit, escalates if over)
- `POST /api/cases/{id}/reject` — reject with required reason, logs event
- `POST /api/cases/{id}/edit-reply` — edit reply text, **re-runs self-check**, logs diff
- `POST /api/cases/{id}/send-back` — send back to agent for re-processing
- `POST /api/cases/{id}/escalate` — escalate to manager, logs reason
- `POST /api/cases/{id}/second-tier-approve` — manager only, clears escalated case
- **Fraud-specific:**
  - `POST /api/cases/{id}/acknowledge` — fraud analyst acknowledges case
  - `POST /api/cases/{id}/investigate` — log investigation/recall attempt
  - `POST /api/cases/{id}/record-outcome` — confirmed fraud / not fraud / recall succeeded / failed
- `GET /api/audit` — audit log with filters (actor, action, date range)
- `GET /api/dashboard/stats` — KPIs (manager only)
- `GET /api/dashboard/charts` — chart data (manager only)

**2.3 Intake + Real-time**
- `POST /api/intake` — accepts CSV-format complaint (same format as live round), triggers pipeline in background
- `WebSocket /ws` — push new cases, status changes to connected dashboards
- Background task: pipeline runs async, stores result in DB, pushes via WS

**2.4 Chat API**
- `POST /api/chat` — SSE stream, officer/analyst asks about a case
- Context-aware: receives case_id, loads evidence + decision + audit
- Claude explains reasoning, answers policy questions

### Phase 3: React Frontend (Day 2, 10:00–13:00)

Three distinct interfaces, not one generic queue.

**3.1 Foundation**
- Vite + TypeScript + TailwindCSS + shadcn/ui
- JWT auth flow, protected routes, role context
- Layout: sidebar (role-aware nav with badge counts), header (user info, notifications)

**3.2 Login Page**
- Real auth → JWT → role-based redirect
- Officer → Resolution Desk, Fraud → Investigation Workbench, Manager → Console

**3.3 Officer Resolution Desk** *(HUMAN_APPROVAL queue)*
Designed for speed — get correct reply to customer quickly.
- Queue sorted by priority then SLA deadline
- Case view leads with:
  - **Drafted reply_text** (editable inline)
  - Decision + refund amount
  - Evidence panel: matched transaction, verification status
  - Self-check status badge
- Actions: **Approve / Edit & Approve / Reject (with reason) / Send Back**
- Approval headroom shown: "Your limit: RM5,000. This refund: RM550. ✓"
- Over limit: Approve button replaced with **"Escalate to Manager"**
- **Self-check re-runs on edit** — blocks send if invented facts detected
- After action → auto-advance to next case

**3.4 Fraud Investigation Workbench** *(FRAUD_TEAM queue)*
Long-lived cases, not quick approve. Customer only gets holding reply.
- Leads with:
  - Suspicious transaction + `auth_method` (3DS-OTP / Chip+PIN / None — the deciding fact)
  - Related transactions on same account
  - Case timeline (status progression)
- Actions: **Acknowledge → Log Investigation/Recall → Record Outcome**
- Outcome options: confirmed fraud / not fraud / recall succeeded / recall failed
- Escalate sensitive or high-value to manager

**3.5 Manager Console** *(both queues + escalations + audit + metrics)*
Only role that sees everything.
- **Dashboard:** KPI tiles (throughput, SLA compliance, override rate), category/priority charts
- **Escalation queue:** merged from both teams. Shows what first tier did + why escalated. Approve / reject with reason
- **All cases table:** filterable by queue, category, priority, status, officer
- **Audit log:** append-only, expandable rows, diffs for edits, export button

**3.6 Intake Form** *(all roles, critical for live round)*
- Input: complaint text, channel dropdown, customer_id (with search/autocomplete)
- Accepts same CSV format as live round
- POST triggers pipeline → result appears in correct queue via WebSocket
- No code changes needed to accept live-round complaints

**3.7 Chatbot Panel** *(all roles, slide-out from case detail)*
- SSE streaming for real-time response
- Context: knows which case, loads evidence + decision + audit
- Explains AI reasoning, answers policy questions, compares similar cases

### Phase 4: Integration + Polish (Day 2, 13:00–15:00)

- Run full 750 test set → generate predictions.csv
- Score, analyze errors, fix accuracy issues
- End-to-end demo test:
  1. HUMAN_APPROVAL within limit → officer approves → sent
  2. HUMAN_APPROVAL over limit → officer escalates → manager approves → sent
  3. FRAUD_TEAM → analyst acknowledges → investigates → holding reply only
- Live round rehearsal: paste CSV complaint → watch it flow through
- Show audit log + agent-vs-human gap across all three
- Code freeze 15:00, PR from fork

---

## Category-Specific AI Agents

```
          New complaint
               │
               ▼
     ┌─────────────────┐
     │ COMPLAINT ROUTER │ (LLM classifies category)
     └────────┬────────┘
              │ dispatches to specialized agent
    ┌─────┬──┴──┬─────┬─────┬─────┬─────┐
    ▼     ▼     ▼     ▼     ▼     ▼     ▼
  Dup.  Failed  ATM  Unauth Scam  Fee  Service
  Agent  Agent Agent Agent Agent Agent  Agent
    │     │     │     │     │     │     │
    └─────┴─────┴─────┴─────┴─────┴─────┘
              │
              ▼
     Policy Engine → Route → Store → Notify
```

Each agent has:
- **Specialized tools** — only the data lookups it needs
- **Category-specific matching logic** — hardcoded rules, not LLM guessing
- **Own reply template** — tone and structure per complaint type

---

## Chatbot for Officers & Analysts

Context-aware assistant accessible from case detail, any role.

**What it does:**
- Explain AI reasoning: "Why REFUND? Two identical charges RM46.66 to GoRide within 2 min, neither reversed"
- Show evidence: "Customer has 3 accounts, matched txn on ACC-000123"
- Answer policy: "Refund > RM500 requires HUMAN_APPROVAL per policy_parameters.csv"
- Compare cases: "5 other DUPLICATE_CHARGE cases with GoRide this month, all auto-resolved"
- Read-only — doesn't change decisions

---

## UX Patterns from Sentinel (reference, not code)

### Queue design
- **Prioritized lanes** — P1 above P2 above P3, never blended
- **Position reason** — why each case is in queue: "Refund > RM500", "Fraud investigation"
- **Live SLA timers** — countdown bar, amber <35%, red when overdue

### Case review
- **Everything in one view** — complaint, customer, transaction, decision, evidence, reply
- **Flag-to-text highlighting** — self-check issues linked to exact words in reply
- **Evidence quality markers** — verified / missing / conflicting. Gaps first
- **Safe fallback visible** — "If nobody acts: case stays pending, flagged overdue" (policy does not authorize auto-decline — cases wait and escalate)

### Decision flow
- **Fixed button order** — Reject, Escalate, Edit, Approve (consistent muscle memory)
- **Approval blocking** — over-limit cases can't be approved, only escalated. Locked button
- **Structured rejection** — reason category required + optional note
- **Edit with diff** — before/after in audit log
- **Auto-advance** — after decision, jump to next priority case

### Audit
- **Every decision logged** — who, when, why, what changed
- **Override rate** — "Changed AI on X of Y cases" (rubber-stamping signal)

---

## Where Automation Applies

| Process | Manual today | Our agent |
|---|---|---|
| Read complaint | Officer reads | LLM extracts structured data |
| Find transaction | Officer searches | Code matches from 156k txns in <1s |
| Apply policy | Officer checks handbook | Code applies rules exactly to sen |
| Calculate refund | Officer uses calculator | Code computes from evidence |
| Write reply | Officer types | LLM drafts in correct language |
| Verify reply | Supervisor reviews | Code checks every ID and amount |
| Verify human edits | Not done | Self-check re-runs on edits |
| Route case | Officer decides | Code applies routing rules |
| Two-tier escalation | Manual handoff | Auto-escalate when over limit |
| SLA tracking | Spreadsheet | Live countdown timers |
| Audit trail | Paper forms | Append-only event log |

### Runs without human trigger
1. **Intake** — new complaint triggers pipeline automatically
2. **SLA countdown** — live timers, warning when approaching deadline
3. **Batch processing** — process all 750 in parallel
4. **Self-check** — every reply verified before it can send
5. **Escalation** — over-limit cases auto-flagged for manager

---

## Technology Stack

| Component | Choice | Why |
|---|---|---|
| LLM | Claude Sonnet (main) + Haiku (bulk) | Best for Malay + structured extraction |
| Backend | FastAPI (Python 3.10+) | Async, WebSocket, auto-docs |
| Frontend | React 18 + TypeScript + Vite | Proper SPA |
| UI Library | shadcn/ui + TailwindCSS | Professional, fast to build |
| Charts | Recharts | React-native, responsive |
| Database | SQLite | Zero setup, sufficient scale |
| Auth | JWT (python-jose) + bcrypt | Stateless, SPA-friendly |
| Real-time | WebSocket (FastAPI) | Push to dashboard |
| Chatbot | SSE | Stream responses |
| Parallelism | asyncio + BackgroundTasks | Non-blocking LLM calls |
| API client | anthropic Python SDK | Official SDK |
| Icons | Lucide React | Clean |

---

## File Structure

```
backend/
├── main.py                    # FastAPI app, CORS, WS manager
├── config.py                  # Settings, env vars
├── requirements.txt
├── db/
│   ├── schema.py              # cases, case_events, users tables
│   ├── models.py              # CRUD, role-filtered queries
│   └── seed.py                # Demo users (officer, fraud, manager)
├── auth/
│   ├── router.py              # /api/auth/*
│   ├── jwt.py                 # Token create/verify
│   └── dependencies.py        # get_current_user, require_role
├── api/
│   ├── cases.py               # Role-filtered CRUD + actions
│   ├── intake.py              # POST new complaint → pipeline
│   ├── chat.py                # SSE chatbot
│   ├── audit.py               # Audit log queries
│   ├── dashboard.py           # KPI + charts (manager)
│   └── websocket.py           # Real-time push
├── agent/
│   ├── pipeline.py            # Orchestrates full flow
│   ├── parser.py              # LLM: extract from text
│   ├── date_resolver.py       # Code: relative → absolute dates
│   ├── transaction_matcher.py # Code: find the right transaction
│   ├── policy_engine.py       # Code: apply rules, compute refund
│   ├── reply_generator.py     # LLM: draft reply
│   ├── self_check.py          # Code: verify reply (agent + human edits)
│   └── router.py              # Code: determine route
├── agents/
│   ├── duplicate_agent.py
│   ├── failed_transfer_agent.py
│   ├── atm_agent.py
│   ├── unauthorised_agent.py
│   ├── scam_agent.py
│   ├── fee_agent.py
│   └── service_agent.py
├── chatbot/
│   ├── engine.py
│   └── prompts.py
└── batch/
    ├── runner.py              # Process 750 complaints parallel
    └── submit.py              # Generate predictions.csv

frontend/
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── api/                   # Axios + JWT, auth, cases, chat
    ├── context/               # Auth, WebSocket
    ├── hooks/                 # useAuth, useCases, useWebSocket
    ├── pages/
    │   ├── Login.tsx
    │   ├── OfficerDesk.tsx    # Resolution desk
    │   ├── FraudWorkbench.tsx # Investigation workbench
    │   ├── ManagerConsole.tsx # Oversight + escalations + dashboard
    │   ├── CaseDetail.tsx     # Shared, adapts to role
    │   └── Intake.tsx         # Live round complaint form
    ├── components/
    │   ├── layout/            # Sidebar, Header, ProtectedRoute
    │   ├── dashboard/         # KPIs, charts (manager)
    │   ├── officer/           # ReplyEditor, ApprovalActions, EvidencePanel
    │   ├── fraud/             # TxnDetail, AuthMethod, Timeline, InvestigationLog
    │   ├── manager/           # EscalationQueue, AuditLog, OverrideRate
    │   ├── chat/              # ChatPanel, ChatMessage, ChatInput
    │   └── shared/            # PriorityBadge, StatusBadge, SLATimer, CategoryBadge
    └── lib/                   # utils, types
```

---

## Demo Script (8 minutes including live round)

**1. Show the system (1 min)**
- Architecture overview, three role logins

**2. Live round — judges type complaints (3 min)**
- Judge provides CSV complaint → paste into intake form
- Watch pipeline process in real-time
- Case appears in correct queue (HUMAN_APPROVAL or FRAUD_TEAM)

**3. Drive three cases end-to-end (3 min)**
- **Case A:** HUMAN_APPROVAL, refund RM550 (> RM500 so routed to HUMAN_APPROVAL, within officer's RM5,000 limit) → officer approves → "sent"
- **Case B:** HUMAN_APPROVAL, refund RM6,000 (over limit) → officer escalates → login as manager → second-tier approve → "sent"
- **Case C:** FRAUD_TEAM → login as fraud analyst → acknowledge → log investigation → customer sees only holding reply

**4. Show observability (1 min)**
- Audit log: who did what, when, diffs for edits
- Agent-vs-human gap: where humans changed AI decisions
- Self-check: edit reply to add invented amount → blocked
- Dashboard: KPIs, override rate

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| LLM rate limits on 750 | asyncio parallel + cache + Haiku for extraction |
| Poor Malay parsing | Few-shot examples from training data |
| Wrong transaction match | Multi-signal scoring, category-specific logic |
| Time crunch | Pipeline is Day 1 priority. Frontend can be minimal |
| Demo fails | Pre-process all test complaints, cached fallback |
| Scoring edge cases | Run scorer after every change, analyze wrongs |
| Frontend not ready | Pipeline + batch runner standalone still gets leaderboard |

---

## Success Metrics

| Metric | Target | Baseline |
|---|---|---|
| Training score | >85 | 31.9 |
| Critical error rate | <1% | — |
| Speed per complaint | <10 seconds | — |
| Live round | All cases classified + routed correctly | — |
| Self-check | 100% replies verified | — |
| Reply quality | Professional tone, correct language, no hallucination | — |
| Bonus: 3-case demo | All three flows work end-to-end | — |
