# Teratai Bank Complaints Agent — Build Plan

> The team's single build plan. Goal: meet every core requirement **and** the bonus ops platform.
> Sources of truth, in order: [README.md](../README.md), [bonus_platform.md](bonus_platform.md), [build_guide.md](build_guide.md), [scoring.md](scoring.md), and the policy CSVs in `data/`. Where this plan disagrees with them, they win — fix the plan.

Backend first, frontend second. Core before bonus, but the data model supports the bonus from day one.

---

## Hackathon Scoring Reminder

**Main ranking (all teams):**

| Weight | Criterion | How judged |
|---|---|---|
| 30% | Accuracy | Leaderboard score on 750 test complaints |
| 25% | Agent design & guardrails | Live round: judges type 2-3 new complaints (CSV format, received_at = 2026-09-30). Routing, approval wait, reacts on its own, self-check catches bad replies |
| 25% | Business value & demo | Reply quality, tone, language, no invented facts; judges read 10 replies |
| 20% | Engineering | Architecture, observability (show why it decided), **cost and speed per complaint** |

Per complaint (max 100 pts):
- matched_txn_id: 25 — outcome: 25 (gated on txn) — refund_amount_myr: 25 (gated on txn, within RM0.005) — category: 10 — priority: 10 — reply_language: 5
- Critical errors (wrongful refund, missed fraud): `final = mean × (1 − 2 × error_rate)`
- `route` and `reply_text` are not auto-scored, but judges check both

**Bonus: Best Ops Platform (separate award, does not affect main ranking):**
- Human gate holds: approval cases wait, fraud cases land with fraud team, escalations wait for manager, nothing sent without a human
- Role separation (officer / fraud analyst / manager see only their cases, through interfaces fitted to their job)
- Two-tier approval (first tier up to limit, over-limit or sensitive escalates to manager and waits)
- Self-check re-runs on human edits
- Append-only audit trail; agent-vs-human gap visible
- Agent decision immutable, separate from human final action

**Live round format:**
```
complaint_id,customer_id,received_at,channel,subject,text
LIVE-07,CUS-01234,2026-09-30 10:15,App chat,,"Hi, I was charged twice..."
```
Customer + transaction already exist in data. System must accept without code changes, process on its own, and show the case record with evidence, route and reply.

**Event checkpoints (from README):**

| When | Checkpoint | What must work |
|---|---|---|
| Day 1 16:00 | Checkpoint 1 | Classify + match the right transaction for 20 training complaints |
| Day 2 12:00 | Checkpoint 2 | Full workflow (decision, reply, approval, write-back) on 50 training complaints; training score posted |
| Day 2 15:00 | Predictions due | PR `Submission: <team-name>` with `submissions/<team-name>/predictions.csv`; code freeze |
| Day 2 15:15 | Demo | 8 min including live round |

**Submission:** Fork repo, build in fork, PR from fork to upstream titled `Submission: <team-name>`. PR needs predictions.csv only; code stays in fork.

---

## Scope

| Tier | Contents |
|---|---|
| **Core (required)** | Event-driven intake (API + watched folder), LLM extraction, code matching/policy/refund, LLM reply, code self-check, case record in DB, approval queue + fraud queue with a real human gate, write-back, 750-complaint export |
| **Bonus MVP** | Sign-in with seeded users, role-filtered queues, officer resolution desk, fraud workbench, manager console with second-tier approval and reassignment, append-only audit, self-check on edits, agent-vs-human comparison |
| **Bonus extras** | Officer/analyst chatbot panel, manager charts, WebSocket live push, SLA timers, notifications |
| **Out of scope** | Real money movement, real customer messaging, production identity, cloud deployment, vector DBs, policy-editing UI |

Refunds and customer messages are **simulated**: the backend enforces the approval gate and writes an outbound record, and the UI labels it as simulated.

---

## Team Split (core, 2 developers)

Split by module so each developer owns separate files. **Dev A** owns the decision engine (code that does money and rules). **Dev B** owns the platform (LLM, DB, API, workflow).

### Step 0 — together, first ~45 min, one PR

1. Skeleton: `backend/` folders (see File Structure), `requirements.txt`, `.gitignore` (`.env`, `*.db`, caches), `pytest`
2. `backend/contracts.py`: Pydantic models `Complaint`, `Clues`, `Candidate`, `MatchResult`, `Decision`, `CheckResult`, `AgentRun`, and the signatures both sides code against:
   - `extract(complaint) -> (Clues, LLMUsage)` — Dev B
   - `match_and_decide(complaint, clues) -> EngineResult(match, decision, evidence)` — Dev A
   - `draft(result, feedback=None) -> (str, LLMUsage)` — Dev B; language is `decision.reply_language`
   - `check(reply_text, result) -> CheckResult` — Dev A; also used on human edits
3. Stubs so nobody waits: `fake_extract` (keyword logic from `starter/baseline.py`) for A; a fixed-decision `match_and_decide` for B

After Step 0 merges, A and B work independently and integrate through PRs at the milestones below.

### Ownership

| | Dev A — decision engine | Dev B — platform and LLM |
|---|---|---|
| Owns | `agent/tools.py`, `date_resolver.py`, `transaction_matcher.py`, `categories/*`, `router.py` (route, priority, language, hold, SLA), `self_check.py`, `eval/` | `llm/*` (interface, adapters, prompts, cache, cost), `agent/parser.py`, `reply_generator.py`, `pipeline.py`, `db/`, `auth/`, `api/` (intake, watched folder, cases, approval/fraud actions, gated outbound), `batch/` (runner, export, validation) |
| Order | 1. Tools + date resolver<br>2. ATM handler (sets the pattern)<br>3. Unauthorised card, scam<br>4. Failed transfer, duplicate<br>5. Fee<br>6. Service quality<br>7. Self-check + routing/hold | 1. LLM interface + first adapter + extraction prompt<br>2. Pipeline + DB persistence<br>3. Intake API + watched folder<br>4. Reply drafting + redraft loop<br>5. Case/approval/fraud endpoints + gated send<br>6. Batch runner + export<br>7. Second adapter + pilot comparison |
| Tests | Each handler scored on `labels_train.csv` without LLM calls; boundary tests (RM500, 10 min, birthdays, fee anniversaries) | Gate tests (over-limit approve, send without approval, edit clears approval, repeat intake, double click); export validation |

**Shared files** (`contracts.py`, `config.py`, `requirements.txt`) change only in a dedicated PR the other developer approves.

A carries the most points (matching = 75 of 100). After Checkpoint 2, B helps A with error analysis on the weakest category.

### Integration milestones

| When | Goal | Merges |
|---|---|---|
| Day 1 ~12:00 | First real end-to-end path: real extraction → ATM handler → stored case | A: ATM handler. B: extractor + pipeline + DB |
| **Day 1 16:00 — Checkpoint 1** | 20 training complaints classified + matched | A: all matchers. B: runner with `--no-draft` |
| Day 1 evening | Full pipeline with draft + self-check; first 750 test run | Both |
| **Day 2 12:00 — Checkpoint 2** | Approval + write-back via API on 50 training complaints; score posted | B: workflow API. A: self-check on edits |
| After Checkpoint 2 | Minimal React UI (intake, queues), then bonus | Both, split by role screen |

Until Checkpoint 2 the core can be demoed through FastAPI `/docs`; React starts afterwards.

### GitHub workflow

- Branches: `feat/a-<thing>` / `feat/b-<thing>`, a few hours of work each
- Small PRs into `dev`; the other developer reviews within ~15 min; squash-merge; rebase on `dev` before opening
- GitHub Action on every PR: `pytest` + training evaluation, score posted on the PR
- `dev` → `main` only at checkpoints; `main` is what the upstream submission PR comes from
- Never commit `.env` or the SQLite DB — the repo is public

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    AGENT PIPELINE (core)                      │
│                                                              │
│  1. Intake (API endpoint / watched folder)                  │
│  2. Understand (LLM, pluggable) — extract clues from text   │
│  3. Match Transaction (Code, category handler) — 75 pts     │
│  4. Apply Policy (Code, category handler) — outcome, refund │
│  5. Draft Reply (LLM, pluggable) — EN/MS, evidence-based    │
│  6. Self-Check (Code) — verify reply against evidence       │
│  7. Route, Hold & Store (Code) — immutable agent run + queue│
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    FASTAPI BACKEND                            │
│  Auth │ Cases API │ Approval API │ Intake │ Outbound (sim)  │
│  Metrics │ Chat (SSE, bonus) │ WebSocket (bonus)            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      SQLite DB                               │
│  agent_runs (immutable) │ cases (workflow) │ case_events    │
│  users │ outbound_messages │ llm_cache                      │
└──────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│               REACT FRONTEND (Vite + TailwindCSS)            │
│  Login │ Officer Resolution Desk │ Fraud Investigation      │
│  Manager Console │ Intake Form │ Chatbot Panel (bonus)       │
└──────────────────────────────────────────────────────────────┘
```

**Design rule:** the LLM does language (extraction, reply). Code does money and rules (matching, policy, refund, routing, self-check). The LLM never sets outcome, refund, priority or route.

---

## Roles (3 roles, matching bonus_platform.md spec)

| Role | Sees | Can do | Approval limit |
|---|---|---|---|
| **Complaints Officer** | HUMAN_APPROVAL queue | Approve / edit reply then approve / reject / send back. Escalate to manager if refund > their limit or case is sensitive | e.g. RM 5,000 |
| **Fraud Analyst** | FRAUD_TEAM queue | Acknowledge / log investigation or recall attempt / record outcome. Escalate sensitive or high-value cases to manager | e.g. RM 5,000 |
| **Manager** | Both queues + escalation queue + audit log + dashboard metrics | Everything both tiers can do + second-tier approval for escalated cases + **reassign** cases. Only role that sees both queues | No limit |

AUTO_RESOLVE cases appear read-only (audit only) for the manager.

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

**Limit basis:** officer — the refund amount. Fraud analyst — the disputed transaction amount (fraud cases carry no refund). Assumption; raise with organisers (see Open Questions).

**Sensitive flag** (forces escalation regardless of amount): customer is vulnerable (65+ on received_at), or a first-tier user flags it manually with a reason. Extend only if organisers clarify.

---

## Data Model

### `agent_runs` table (IMMUTABLE — one row per pipeline run)
```
run_id                PK
complaint_id          FK
run_kind              autonomous / reprocess (send-back creates a new reprocess run)

-- Agent decision (what the leaderboard scores, from the autonomous run)
category
matched_txn_id
outcome
refund_amount_myr     stored as integer sen or Decimal, exported with 2 decimals
priority
reply_language
route
reply_text

-- Explainability
clues                 JSON — validated LLM extraction
candidates            JSON — scored transaction candidates + why
match_status          confident / ambiguous / none
evidence              JSON — evidence snapshot used
rule_id               which policy rule fired
calculation           JSON — e.g. requested 1500.00 − dispensed 950.00 = 550.00
self_check            pass / flag + offending IDs/amounts
redraft_count
hold_reason           NULL / customer_not_found / ambiguous_match / no_match / category_revised /
                      self_check_failed / unknown_auth_method / llm_error

-- Observability
provider, extract_model, draft_model, prompt_version, schema_version, policy_version
tokens_in, tokens_out, cost_usd, latency_ms, retries
created_at
```

### `cases` table (mutable workflow state)
```
complaint_id          PK
customer_id
received_at
channel
subject
text
autonomous_run_id     FK — the run exported to predictions.csv; never changes
current_run_id        FK — latest run (after send-back)

-- Human final action (what actually happened)
status                processing / failed / pending / escalated / approved /
                      rejected / sent_back / investigating / sent / closed
final_outcome         NULL until human acts
final_refund_myr      NULL until human acts
final_reply_text      NULL until human acts
final_self_check      pass / flag (re-run on every edit)
approved_by / approved_at   cleared if the reply or action changes after approval
sensitive             bool + sensitive_reason
assigned_to           user who owns it
escalated_to          manager username if escalated
ack_due_at            from sla_policy.csv (acknowledge_within_hours)
resolve_due_at        from sla_policy.csv (resolve_within_business_days)
created_at
updated_at
```

### `case_events` table (append-only audit log)
```
id                    PK auto-increment
complaint_id          FK
actor                 username (or "agent")
action                ingest / agent_run / approve / edit / reject / send_back /
                      escalate / reassign / acknowledge / investigate /
                      record_outcome / second_tier_approve / second_tier_reject / send
field                 which field changed (e.g. reply_text, outcome)
old_value
new_value
reason                required on every action that changes the agent's decision
self_check_result     pass / flag (re-run on edits)
created_at
```

### `outbound_messages` table (simulated delivery — proof nothing went out unapproved)
```
id                    PK
complaint_id          FK
kind                  resolution / holding_reply
reply_text
refund_myr            simulated refund executed with this message (0 for holding replies)
authorised_by         username, or "auto" for AUTO_RESOLVE
status                queued / sent / failed
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

**Integrity rule:** `agent_runs` rows never change. Human actions change `cases` and append `case_events`. `predictions.csv` is exported from `cases.autonomous_run_id` only — never from human-corrected fields or reprocess runs. The gap between agent run and final action is auditable and demo-worthy.

---

## Build Order — Backend First

### Phase 1: Agent Pipeline (Day 1, 09:00–16:00 → Checkpoint 1)

75 of 100 points per complaint depend on transaction matching. Nothing else matters if this is wrong.

**1.1 Project skeleton (30 min)**
- Backend folder structure, `.env.example` (no secrets), `requirements.txt`; `.gitignore` the DB, caches and `.env` — the repo is public
- Wrap `starter/data.py` — load all CSVs once per process, build indexed lookups
- Lookup functions (the agent's tools): `get_customer`, `get_accounts`, `find_transactions(customer, filters)`, `get_reversal`, `get_atm_journal`, `get_fee_schedule`, `get_policy`. Never paste whole tables into a prompt
- Money as integer sen or `Decimal`; card last-4 as strings; timestamps in Malaysia time (UTC+8)
- Run baseline scorer, record 31.9 reference
- Pick a fixed 50-complaint pilot from training labels covering all categories, EN/MS/mixed, every channel, call-centre notes. Hold back a separate slice of training labels for checking changes

**1.2 LLM interface + Complaint Parser — LLM step (1.5 hrs)**
- Pluggable provider: one `LLMClient` interface implementing the `Extractor` and `Drafter` protocols in `backend/contracts.py`. Provider and model set per step via env (`LLM_PROVIDER`, `LLM_EXTRACT_MODEL`, `LLM_DRAFT_MODEL`). Unknown provider fails at startup
- Build the first adapter now; add a second adapter and compare both on the 50-case pilot (same deterministic engine), then choose the default by accuracy, cost and latency
- Extracts structured JSON from complaint text:
  ```json
  {
    "category": "DUPLICATE_CHARGE",
    "language": "MS",
    "is_mixed_language": false,
    "amount_mentioned": 46.66,
    "other_amounts": [],
    "amount_approximate": false,
    "counterparty_name": "GoRide",
    "counterparty_bank": null,
    "atm_location": null,
    "date_phrase": "hari Selasa lepas",
    "date_exact": null,
    "card_last4": null,
    "fee_type": null,
    "fee_month": null
  }
  ```
- Exact schema: `Clues` in `backend/contracts.py` (unknown fields rejected). Dates accepted as DD-MM-YYYY or YYYY-MM-DD; all times MYT; costs in RM
- Validate against a schema; malformed output → one retry → `hold_reason = llm_error`, visible as failed case
- Complaint text is data, not instructions: wrap it in a delimited block; the output schema has no fields that can set outcome/refund/route
- Few-shot examples from training data (EN + MS + mixed + call-centre note)
- Date phrase stays as raw text — code resolves it next
- Cache by hash of (complaint fields, provider, model, prompt_version, schema_version)

**1.3 Date Resolver — Code (1 hr)**
- Relative dates anchored to `received_at`:
  - "yesterday" / "semalam" → day before received
  - "last Tuesday" / "hari Selasa lepas" → most recent Tuesday before received
  - "last week" / "minggu lepas" → 7-day window
  - "last month" / "bulan lepas" → calendar month before received_at (e.g., received Aug 15 → Jul 1–31)
  - Named month ("July" / "bulan Julai") → that calendar month in the most recent year within 45-day window
  - FEE_DISPUTE specifically: complaint_policy.csv says "the month the customer names" — resolve to that calendar month, not a rolling window
  - Exact dates pass through
- Output: (start_date, end_date) range. Unparseable phrase → full 45-day window, rely on amount and name

**1.4 Transaction Matcher — Code, THE CRITICAL PATH (2.5 hrs)**

Matching answers "which transaction is the customer talking about?" — it finds the transaction ID. Policy (step 1.5) answers "what should happen to it?" A complaint can refer to a completed transfer and still need a matched ID — the outcome is DECLINE, but the match is correct.

- Filter: customer's debits, within 45-day window (`MATCH_WINDOW_DAYS` from params)
- Multi-signal scoring: amount match (exact, or tolerance for "about" — start at ±5%, tune on training labels), merchant/counterparty substring (case-insensitive, partial), date in range, card_last4, channel family
- Category-specific matching lives in the category handler (find the transaction, don't decide outcome here):
  - **DUPLICATE_CHARGE:** find the disputed later card charge by amount, merchant, date. Then look for an earlier charge on **the same card** with same merchant and same amount. matched_txn_id = the later charge
  - **FAILED_TRANSFER:** match DuitNow/IBG transfer debit by recipient, amount, date — regardless of status or reversal. Match even if completed or reversed
  - **ATM_NOT_DISPENSED:** match ATM Withdrawal by amount, date, location — regardless of journal result. Match even if fully dispensed
  - **UNAUTHORISED_CARD:** match Card POS/e-Commerce debit by amount, merchant, date, card
  - **SCAM_TRANSFER:** match DuitNow/IBG transfer out by recipient, amount, date
  - **FEE_DISPUTE:** match Fee channel debit by fee type and month the customer mentions
  - **SERVICE_QUALITY:** no transaction, matched_txn_id = empty
- **Category fallback:** if the chosen handler finds no candidate, try related handlers on the same channel family (e.g. SCAM_TRANSFER ↔ FAILED_TRANSFER, UNAUTHORISED_CARD ↔ DUPLICATE_CHARGE) and record that the category was revised
- **Unclear match (build guide: "don't guess: flag the case"):**
  - One candidate clearly ahead → `match_status = confident`
  - Several close candidates or none → `match_status = ambiguous / none`. The run records the top-scoring candidate (or empty) so the autonomous prediction is complete, and sets `hold_reason`. The case is held for a human (see 1.7 routing) — no automatic refund or message
- Training labels always have a transaction for non-SERVICE_QUALITY categories, so a `none` result is a matcher bug to investigate in evaluation

**1.5 Policy Engine — Code (1 hr)**

Policy answers "what should happen?" given the matched transaction and its evidence. Reads `complaint_policy.csv` + `policy_parameters.csv`. Each rule lives in its category handler and returns `rule_id` + `calculation` for the audit trail.

- Per category decision rules:
  - **DUPLICATE_CHARGE:** check same card, same merchant, same amount, within 10 min, neither reversed → REFUND later charge. If conditions don't hold (different cards, >10 min apart, already reversed) → DECLINE
  - **FAILED_TRANSFER:** check status and reversal. Failed + no reversal → REFUND. Has reversal → DECLINE (tell customer when returned). Status Completed → DECLINE (money reached recipient)
  - **ATM_NOT_DISPENSED:** check atm_journal. If dispensed < requested → REFUND the shortfall (requested - dispensed). If fully dispensed → DECLINE
  - **UNAUTHORISED_CARD:** check auth_method. None (no strong auth) → REFUND. 3DS-OTP or Chip+PIN → INVESTIGATE (fraud team, no refund now). Any other auth method (e.g. Contactless — not seen in training labels) → INVESTIGATE with `hold_reason = unknown_auth_method`; never refund
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
- SLA: `ack_due_at` = received_at + acknowledge hours; `resolve_due_at` = received_at + resolve business days (Mon–Fri; no public holidays unless organisers say otherwise)

**1.6 Reply Generator — LLM step (1 hr)**
- Input: decision, calculation, matched transaction, reply_language, category guidance from the handler
- Prompt enforces: professional bank tone, reference transaction if applicable, state decision clearly, no invented facts, correct language, concise
- Controlled status wording: an AUTO_RESOLVE refund may say "has been refunded"; anything awaiting approval or investigation must not claim money has moved
- FRAUD_TEAM cases get a **holding reply** (received, under investigation, next contact time) — not a resolution
- Category guidance per handler for consistency

**1.7 Self-Check, Hold & Route — Code (30 min)**
- Reuse `starter/check_reply.py` logic
- Extract TXN-IDs (regex `TXN-\d{7}`) and amounts (regex `RM\s?[\d,]+\.?\d*`), including alternate formats (`RM 1,383.20`, `RM1383.2`)
- Every ID and amount must exist in the evidence; the refund amount stated must equal the computed refund, and the TXN-ID must be the matched one
- Fail → redraft once with "Remove these invented facts: ..." → fail again → `hold_reason = self_check_failed`
- **Hold overrides only push toward humans, never away:** any `hold_reason` on a non-INVESTIGATE case routes it to HUMAN_APPROVAL with the reason shown in the queue; INVESTIGATE always stays FRAUD_TEAM
- **Same check re-runs when human edits reply** (bonus requirement)

**1.8 Batch Runner + Score (1 hr)**
- Async parallel processing with bounded concurrency and rate limiting
- Cache LLM calls (don't re-call on retry); record tokens, cost, latency, retries per run
- Write `submissions/<team>/predictions.csv` from DB autonomous runs
- Score against training labels with `--details`, analyze errors by category; prioritise wrongful refunds, missed fraud, then matching failures
- **Target: Checkpoint 1 by 16:00 — 20 training complaints classified + matched**
- **First full 750 test run as soon as matching is stable (Day 1 evening).** Re-run only changed complaints later; never leave the 750 run for the last hour

### Phase 2: FastAPI Backend + DB + Core Workflow (Day 1, 16:00–17:30 + Day 2, 09:00–10:00 → Checkpoint 2)

Checkpoint 2 (Day 2 12:00) needs decision, reply, approval and write-back on 50 training complaints. All of that must work through the API before the UI is finished.

**2.1 DB Schema + Auth**
- SQLite: `agent_runs`, `cases`, `case_events`, `outbound_messages`, `users`, `llm_cache` (schema above)
- Seed users:
  - `officer1` — Complaints Officer, approval_limit_myr = 5000
  - `fraud1` — Fraud Analyst, approval_limit_myr = 5000
  - `manager1` — Manager, no limit
- Simple auth: seeded users + `role` column, JWT on login, role checks enforced **in the backend** on every case and action endpoint (hiding links is not enough)

**2.2 Core API Endpoints**
- `POST /api/auth/login` — returns JWT with role
- `GET /api/auth/me` — current user + role + approval_limit
- `GET /api/cases` — list with filters (category, priority, status, route, hold_reason), sorted by priority then SLA due. **Role-filtered:** officer sees HUMAN_APPROVAL only, fraud sees FRAUD_TEAM only, manager sees all
- `GET /api/cases/{id}` — full detail: agent run + candidates + evidence + calculation + final action + audit trail + outbound
- `POST /api/cases/{id}/approve` — first-tier approve (checks approval_limit and sensitive flag; blocks if over → must escalate). Requires final reply self-check = pass
- `POST /api/cases/{id}/reject` — reject with required reason; officer sets final outcome and an edited reply that passes self-check before anything is sent
- `POST /api/cases/{id}/edit-reply` — edit reply text, **re-runs self-check**, logs diff, clears any prior approval
- `POST /api/cases/{id}/send-back` — send back to agent; creates a new `reprocess` run, autonomous run untouched
- `POST /api/cases/{id}/escalate` — escalate to manager, logs reason
- `POST /api/cases/{id}/flag-sensitive` — mark sensitive with reason (forces escalation)
- `POST /api/cases/{id}/second-tier-approve` / `second-tier-reject` — manager only, clears escalated case, reason required
- `POST /api/cases/{id}/reassign` — manager only
- **Fraud-specific:**
  - `POST /api/cases/{id}/acknowledge` — fraud analyst acknowledges case; **releases the holding reply** to outbound
  - `POST /api/cases/{id}/investigate` — log investigation/recall attempt
  - `POST /api/cases/{id}/record-outcome` — confirmed fraud / not fraud / recall succeeded / failed
- `GET /api/audit` — audit log with filters (actor, action, date range)
- `GET /api/metrics` — throughput, auto-resolve rate, SLA, override rate, self-check catches, cost and latency per complaint (manager only)
- `GET /api/export/predictions` — writes and validates predictions.csv from autonomous runs

**2.3 Intake + Write-back**
- `POST /api/intake` — accepts one complaint row (same fields as live round) or a CSV; persists the case first, then runs the pipeline in the background; returns case ID for polling
- Watched folder `inbox/` — dropped CSV files go through the same intake path
- Unknown `customer_id` is accepted and stored, never dropped: no transaction lookup, held with `customer_not_found` (HUMAN_APPROVAL, or FRAUD_TEAM if INVESTIGATE); same complaint ID + identical content returns the existing case; same ID + different content is rejected
- AUTO_RESOLVE cases: self-check pass → outbound record (`authorised_by = auto`) → `sent` → `closed`
- Every human-gated send goes through one backend function that checks: right role, approved (and second-tier approved if escalated), current reply passed self-check, not already sent. Protects against double clicks and retries
- Pipeline or delivery failure leaves a visible `failed` state with retry

### Phase 3: React Frontend (Day 2, 10:00–13:00)

Three distinct interfaces, not one generic queue.

**3.1 Foundation**
- Vite + TypeScript + TailwindCSS + shadcn/ui
- JWT auth flow, protected routes, role context
- Layout: sidebar (role-aware nav with badge counts), header (user info, notifications)
- Queues poll the backend; WebSocket push (bonus extra) layers on top

**3.2 Login Page**
- Real auth → JWT → role-based redirect
- Officer → Resolution Desk, Fraud → Investigation Workbench, Manager → Console

**3.3 Officer Resolution Desk** *(HUMAN_APPROVAL queue)*
Designed for speed — get correct reply to customer quickly.
- Queue sorted by priority then SLA deadline; each row shows why it is waiting ("Refund > RM500", "Decline needs approval", "Ambiguous match", "Self-check failed")
- Case view leads with:
  - **Drafted reply_text** (editable inline)
  - Decision + refund amount + calculation
  - Evidence panel: matched transaction, other candidates, verification status
  - Self-check status badge
- Actions: **Approve / Edit & Approve / Reject (with reason) / Send Back**
- Approval headroom shown: "Your limit: RM5,000. This refund: RM550. ✓"
- Over limit or sensitive: Approve button replaced with **"Escalate to Manager"**
- **Self-check re-runs on edit** — blocks send if invented facts detected
- Delivery shown from the outbound record, labelled "Simulated"
- After action → auto-advance to next case

**3.4 Fraud Investigation Workbench** *(FRAUD_TEAM queue)*
Long-lived cases, not quick approve. Customer only gets holding reply, and only after acknowledgement.
- Leads with:
  - Suspicious transaction + `auth_method` (3DS-OTP / Chip+PIN / None — the deciding fact)
  - Related transactions on same account
  - Case timeline (status progression)
- Actions: **Acknowledge (releases holding reply) → Log Investigation/Recall → Record Outcome**
- Outcome options: confirmed fraud / not fraud / recall succeeded / recall failed
- Escalate sensitive or high-value to manager

**3.5 Manager Console** *(both queues + escalations + audit + metrics)*
Only role that sees everything.
- **Metrics tiles:** throughput, auto-resolve rate, SLA compliance, override rate, self-check catches, cost and latency per complaint
- **Escalation queue:** merged from both teams. Shows what first tier did + why escalated. Approve / reject with reason
- **All cases table:** filterable by queue, category, priority, status, officer; reassign action
- **Audit log:** append-only, expandable rows, diffs for edits, export button
- **Agent vs human:** autonomous run beside final action for every overridden case

**3.6 Intake Form** *(all roles, critical for live round)*
- Input: complaint_id, customer_id (with search/autocomplete), received_at, channel dropdown, subject, text — or paste one CSV row
- Accepts same CSV format as live round
- POST triggers pipeline → shows processing state → result appears in correct queue
- No code changes needed to accept live-round complaints

### Phase 4: Bonus Extras (Day 2, after core UI works)

Only once Phase 3 passes the three-case demo. Each extra has a fallback so the core never depends on it.

**4.1 WebSocket live push** — `WebSocket /ws` pushes new cases and status changes; queues still work by polling if the socket drops

**4.2 Manager charts** — Recharts category/priority/route breakdowns and SLA trend on top of `GET /api/metrics`; tiles work without them

**4.3 Chatbot Panel** *(all roles, slide-out from case detail)*
- `POST /api/chat` — SSE stream, officer/analyst asks about a case
- Context: case_id → loads agent run, evidence, calculation, audit
- Explains AI reasoning, answers policy questions, compares similar cases
- **Read-only** — cannot change decisions or send anything; uses the same pluggable LLM client

**4.4 SLA timers + notifications** — live countdown bars and new-case alerts per role

### Phase 5: Integration + Submission (Day 2, 13:00–15:00)

- Re-run changed test complaints; export predictions.csv from autonomous runs
- Validate export: exactly 750 unique test IDs, correct header, valid enums, two-decimal amounts, non-empty replies. Missing or failed predictions are surfaced, never filled with invented answers
- Score training set, final error analysis
- End-to-end demo test:
  1. HUMAN_APPROVAL within limit → officer approves (or edits, triggering self-check) → sent
  2. HUMAN_APPROVAL over limit → officer escalates → manager approves → sent
  3. FRAUD_TEAM → analyst acknowledges → holding reply sent → investigation logged
- Live round rehearsal: paste CSV complaint and drop one in `inbox/` → watch it flow through
- Show audit log + agent-vs-human gap across all three
- Code freeze 15:00, PR from fork

---

## Category Handlers (instead of separate category agents)

One pipeline, seven deterministic category handlers. No per-category LLM agents and no separate router LLM call — the extraction call already returns the category.

```
          New complaint
               │
               ▼
     ┌──────────────────┐
     │ EXTRACT (1 LLM)  │  category + clues
     └────────┬─────────┘
              │ registry lookup
    ┌─────┬──┴──┬─────┬─────┬─────┬─────┐
    ▼     ▼     ▼     ▼     ▼     ▼     ▼
  Dup.  Failed  ATM  Unauth Scam  Fee  Service
    │     │     │     │     │     │     │      each: match() / decide() / reply_guidance
    └─────┴─────┴─────┴─────┴─────┴─────┘
              │  (no candidate → try related handler)
              ▼
     DRAFT (1 LLM) → Self-check → Route/Hold → Store → Notify
```

Each handler has:
- **Its own lookups** — calls only the tools it needs (ATM journal, reversals, fee schedule)
- **Matching logic** — hardcoded rules, not LLM guessing
- **Decision rule** — returns outcome, refund, `rule_id`, calculation
- **Reply guidance** — tone and structure per complaint type, passed to the shared draft prompt

Why not seven LLM agents: the brief requires matching and decisions in code, so per-category agents would only add prompts, calls, cost and latency (all judged). Two LLM calls per complaint keeps the 750 run cheap and cacheable, each handler is unit-testable against training labels without an LLM, and the registry makes category fallback trivial.

Optional, for agent-design points: let the extraction call use read-only tools (`find_transactions`, `get_atm_journal`) to refine clues. Handlers still make every decision.

---

## Chatbot for Officers & Analysts (bonus extra)

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
- **Position reason** — why each case is in queue: "Refund > RM500", "Fraud investigation", "Ambiguous match"
- **Live SLA timers** — countdown bar, amber <35%, red when overdue. Use a labelled demo clock (e.g. 2026-09-30) so historical data isn't all overdue

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
1. **Intake** — new complaint (API or watched folder) triggers pipeline automatically
2. **SLA countdown** — live timers, warning when approaching deadline
3. **Batch processing** — process all 750 in parallel
4. **Self-check** — every reply verified before it can send
5. **Escalation** — over-limit and sensitive cases auto-flagged for manager

---

## Technology Stack

| Component | Choice | Why |
|---|---|---|
| LLM | Pluggable `LLMClient` (Claude and OpenAI adapters); default chosen after 50-case pilot | Compare accuracy, cost, latency on the same engine |
| Backend | FastAPI (Python 3.10+) + Pydantic | Async, WebSocket, auto-docs, typed contracts |
| Frontend | React 18 + TypeScript + Vite | Proper SPA |
| UI Library | shadcn/ui + TailwindCSS | Professional, fast to build |
| Charts | Recharts (bonus extra) | React-native, responsive |
| Database | SQLite | Zero setup, sufficient scale |
| Auth | Seeded users + JWT (python-jose) + bcrypt | Simple; not production identity |
| Real-time | Polling; WebSocket (bonus extra) | Push to dashboard |
| Chatbot | SSE (bonus extra) | Stream responses |
| Parallelism | asyncio + BackgroundTasks, bounded concurrency | Non-blocking LLM calls |
| Money | `Decimal` / integer sen | Exact to the sen |
| Icons | Lucide React | Clean |

---

## File Structure

```
backend/
├── main.py                    # FastAPI app, CORS, WS manager
├── config.py                  # Settings, env vars (LLM provider/models)
├── requirements.txt
├── .env.example
├── db/
│   ├── schema.py              # agent_runs, cases, case_events, outbound_messages, users, llm_cache
│   ├── models.py              # CRUD, role-filtered queries
│   └── seed.py                # Demo users (officer, fraud, manager)
├── auth/
│   ├── router.py              # /api/auth/*
│   ├── jwt.py                 # Token create/verify
│   └── dependencies.py        # get_current_user, require_role
├── api/
│   ├── cases.py               # Role-filtered CRUD + actions
│   ├── intake.py              # POST new complaint → pipeline
│   ├── watcher.py             # inbox/ folder watcher → same intake path
│   ├── outbound.py            # Gated simulated send
│   ├── audit.py               # Audit log queries
│   ├── metrics.py             # KPIs + chart data (manager)
│   ├── export.py              # predictions.csv export + validation
│   ├── chat.py                # SSE chatbot (bonus)
│   └── websocket.py           # Real-time push (bonus)
├── llm/
│   ├── client.py              # LLMClient interface, cache, usage/cost tracking
│   ├── anthropic_adapter.py
│   ├── openai_adapter.py
│   └── prompts.py             # Versioned extraction + draft prompts
├── agent/
│   ├── pipeline.py            # Orchestrates full flow
│   ├── tools.py               # Lookup functions over starter/data.py
│   ├── parser.py              # LLM: extract from text
│   ├── date_resolver.py       # Code: relative → absolute dates
│   ├── transaction_matcher.py # Code: candidate scoring shared by handlers
│   ├── reply_generator.py     # LLM: draft reply
│   ├── self_check.py          # Code: verify reply (agent + human edits)
│   ├── router.py              # Code: route + hold overrides + SLA
│   └── categories/
│       ├── base.py            # CategoryHandler: match / decide / reply_guidance
│       ├── registry.py
│       ├── duplicate.py
│       ├── failed_transfer.py
│       ├── atm.py
│       ├── unauthorised.py
│       ├── scam.py
│       ├── fee.py
│       └── service.py
├── chatbot/                   # bonus
│   ├── engine.py
│   └── prompts.py
├── batch/
│   ├── runner.py              # Process 750 complaints parallel
│   └── submit.py              # Generate predictions.csv
└── tests/                     # Handler, boundary and gate tests

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
    │   └── shared/            # PriorityBadge, StatusBadge, SLATimer, CategoryBadge, SimulatedBadge
    └── lib/                   # utils, types
```

---

## Testing & Guardrail Checklist

- **Boundaries:** RM500.00 (AUTO_RESOLVE) vs RM500.01 (HUMAN_APPROVAL); duplicates at exactly 10 min vs 10 min 1 s; reversed duplicates; ATM fully dispensed; 65th birthday on received_at; 60th birthday on fee charge date; credit card first anniversary; mixed-language and call-centre language fallback
- **Handlers:** each category handler scored against training labels with no LLM (gold category + clues), then end-to-end
- **Gates:** approve over limit fails; officer calling a fraud endpoint fails; direct API send without approval fails; edited reply with invented TXN-ID/amount blocked; edit after approval clears approval; escalated case can't be sent on first-tier action; fraud holding reply not sent before acknowledge
- **Robustness:** repeat intake returns same case; conflicting content rejected; double-click approve sends once; restart mid-batch resumes; LLM error leaves a visible failed case
- **Export:** autonomous run only; human edits never leak into predictions.csv

---

## Demo Script (8 minutes including live round)

**1. Show the system (1 min)**
- Architecture overview (LLM does language, code does money), three role logins

**2. Live round — judges type complaints (3 min)**
- Judge provides CSV complaint → paste into intake form (or drop into `inbox/`)
- Watch pipeline process on its own
- Case appears in correct queue (HUMAN_APPROVAL or FRAUD_TEAM) with evidence, calculation and checked reply

**3. Drive three cases end-to-end (3 min)**
- **Case A:** HUMAN_APPROVAL, refund RM550 (> RM500 so routed to HUMAN_APPROVAL, within officer's RM5,000 limit) → officer approves → "sent (simulated)"
- **Case B:** HUMAN_APPROVAL, refund RM6,000 (over limit) → officer escalates → login as manager → second-tier approve → "sent (simulated)"
- **Case C:** FRAUD_TEAM → login as fraud analyst → acknowledge (holding reply released) → log investigation → customer sees only holding reply

**4. Show observability (1 min)**
- Audit log: who did what, when, diffs for edits
- Agent-vs-human gap: where humans changed AI decisions
- Self-check: edit reply to add invented amount → blocked
- Dashboard: KPIs, override rate, cost and latency per complaint

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| LLM rate limits on 750 | Bounded asyncio concurrency + cache + cheaper model for extraction |
| Poor Malay parsing | Few-shot examples from training data; compare providers on pilot |
| Wrong transaction match | Multi-signal scoring, category handlers, category fallback, hold on ambiguity |
| Wrongful refund / missed fraud | Unknown auth or ambiguous match never auto-refunds; INVESTIGATE always FRAUD_TEAM |
| Prompt injection in complaint text | Text treated as data; LLM output can't set outcome/refund/route |
| Time crunch | Pipeline is Day 1 priority. Bonus extras only after core UI works |
| Demo fails | Pre-process all test complaints, cached fallback, rehearse live intake |
| Scoring edge cases | Run scorer after every change, analyze wrongs |
| Frontend not ready | Pipeline + batch runner + API still deliver leaderboard and Checkpoint 2 |
| Secrets leak (public repo) | Keys only in env vars; `.env` gitignored |

---

## Success Metrics

| Metric | Target | Baseline |
|---|---|---|
| Training score | >85 | 31.9 |
| Critical error rate | <1% | — |
| Speed per complaint | <10 seconds | — |
| Cost per complaint | Measured and shown on dashboard | — |
| Live round | All cases classified + routed correctly, approval waits | — |
| Self-check | 100% replies verified | — |
| Reply quality | Professional tone, correct language, no hallucination | — |
| Bonus: 3-case demo | All three flows work end-to-end | — |

---

## Open Questions (raise as upstream issues early; answers apply to every team)

| Question | Current assumption |
|---|---|
| What counts as "sensitive" for escalation? | Vulnerable customer (65+) or manual flag with reason |
| Fraud analyst approval limit — measured on what amount? | Disputed transaction amount |
| UNAUTHORISED_CARD with Contactless or other auth methods | INVESTIGATE, held, never refund |
| SLA "business days" — weekends/public holidays? | Mon–Fri, no holidays |
