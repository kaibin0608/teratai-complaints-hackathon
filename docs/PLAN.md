# Teratai Bank Complaints Agent — Build Plan

> The team's single build plan. Goal: meet every core requirement **and** the bonus ops platform.
> Sources of truth, in order: [README.md](../README.md), [api.md](api.md) (the fixed API contract), [bonus_platform.md](bonus_platform.md), [build_guide.md](build_guide.md), [scoring.md](scoring.md), and the policy CSVs in `data/`. Where this plan disagrees with them, they win — fix the plan.

Backend first, frontend second. Core before bonus, but the data model supports the bonus from day one.

**Progress:** what's done and what's left is tracked in [STATUS.md](STATUS.md).

## Explainer

**▶ [Watch the Teratai Complaints Explainer](https://claude.ai/artifact/Hk9ZvLQa1ctHfCnexmjjUQ)**: an interactive, narrated walkthrough of the brief and this plan (animated scenes, voice-over, live captions; pick any chapter or scene from the list on the page).

> Recorded before the organisers' API update (22 Oct, 17:47–19:26). Its live round (judges typing complaints), 8-minute demo, 15:15 slot and `/api/*` endpoints are out of date: this plan and [api.md](api.md) are current.

| Chapter | Covers | Length |
|---|---|---|
| 1 · The Challenge | What the hackathon asks for: the 8 output fields, 7 categories, priority/language/routing rules, scoring, live round, bonus, deliverables and deadlines | 7:41 |
| 2 · The Plan | What this plan builds and how: the 7-step pipeline, matching, policy, self-check, data model, roles, team split, milestones | 7:17 |
| 3 · Coverage Check | Does this plan cover README.md? Coverage, 5 gaps to fix, open questions | 3:29 |

**▶ [Watch the Teratai Build Tour](https://claude.ai/artifact/1mHE4FAWT4kgWFum1LvTAy)**: a narrated walkthrough of every branch merged into `dev` (snapshot of 23 Oct, `dev` at `6dc8059`): what each built, how it works, and its measured results.

| Chapter | Covers | Length |
|---|---|---|
| 1 · Dev A: Rules Engine | Step 0 contracts and stubs; Danial's 6 branches: tools and dates, handler pattern and scoring, the 7 categories, router, self-check, engine | 4:36 |
| 2 · Dev B: LLM + Data | LLM config and client, extractor, case store, batch runner and export, reply writer | 2:48 |
| 3 · API + Hardening | The organisers' update, contract API, messy-text test set, engine fixes, UI read API, where `dev` stands, what's left | 3:12 |

---

## Hackathon Scoring Reminder

**Main ranking (all teams):**

| Weight | Criterion | How judged |
|---|---|---|
| 30% | Accuracy | Leaderboard score on 750 test complaints |
| 25% | Live round | **Hidden test (15):** right after the 15:00 freeze, `scoring/api_check.py` sends 20 unseen, messily written complaints to our API at once and scores them like the leaderboard (score × 0.15); 120 s per complaint or it scores 0. **Human gate (10):** in the demo, judges send 3 complaints one at a time and tick a checklist (case appears on its own, right transaction/decision/refund/route, approval holds, fraud lands in the fraud queue, reply language, self-check visible) |
| 25% | Business value & demo | Reply quality, tone, language, no invented facts; judges read 10 replies |
| 20% | Engineering | Architecture, observability (show why it decided), **cost and speed per complaint** |

Per complaint (max 100 pts):
- matched_txn_id: 25 — outcome: 25 (gated on txn) — refund_amount_myr: 25 (gated on txn, within RM0.005) — category: 10 — priority: 10 — reply_language: 5
- Critical errors (wrongful refund, missed fraud): `final = mean × (1 − 2 × error_rate)`
- `route` and `reply_text` are not auto-scored, but judges check both. Automatic reply checks run on **every** reply and go to the judges: empty reply, wrong language, TXN-IDs or RM amounts not in the evidence, and **a refund reply that doesn't state the refund amount**

**Bonus: Best Ops Platform (separate award, does not affect main ranking):**
- Human gate holds: approval cases wait, fraud cases land with fraud team, escalations wait for manager, nothing sent without a human
- Role separation (officer / fraud analyst / manager see only their cases, through interfaces fitted to their job)
- Two-tier approval (first tier up to limit, over-limit or sensitive escalates to manager and waits)
- Self-check re-runs on human edits
- Append-only audit trail; agent-vs-human gap visible
- Agent decision immutable, separate from human final action

**Live round format:** everything goes through the fixed API in [api.md](api.md): `POST /complaints` with the six `complaints.csv` fields as JSON ([examples/live_complaint_example.json](../examples/live_complaint_example.json)), then `GET /cases/{id}` until `status = done`, and `POST /cases/{id}/actions` for the human gate. Customers and transactions already exist in the data; each complaint carries its own `received_at` (not always 30 Sep). Hidden-test complaints are written like real customers write: typos, SMS short forms, emoji, mixed English and Malay. Our calls carry no credentials. Robustness probes and per-complaint timing feed the engineering score. Self-test any time: `python scoring/api_check.py http://localhost:8000`.

**Event checkpoints (from README):**

| When | Checkpoint | What must work |
|---|---|---|
| Day 1 16:00 | Checkpoint 1 | Classify + match the right transaction for 20 training complaints |
| Day 2 12:00 | Checkpoint 2 | Full workflow (decision, reply, approval, write-back) on 50 training complaints; training score posted; **`scoring/api_check.py` passes against our API**; organisers confirm they can reach it from their laptop |
| Day 2 15:00 | Agent + API freeze | Predictions due (PR with commit hash and API URL). API must be running from now until our demo ends; the hidden test runs 15:00–15:45 |
| Day 2 15:00–16:30 | UI time | Agent is frozen; keep working on the UI and the bonus ops platform only |
| Day 2 16:30 | Demo | About 10 min: presentation, human gate (3 complaints), ops platform |

**Submission:** Fork repo, build in fork, PR from fork to upstream titled `Submission: <team-name>`. PR needs predictions.csv only; code stays in fork. **The PR description must give our freeze commit hash (last commit at 15:00) and our API URL.** Changes to the agent after 15:00 don't count.

---

## Scope

| Tier | Contents |
|---|---|
| **Core (required)** | The fixed API from [api.md](api.md) (no auth; reachable from the organisers' laptop), LLM extraction robust to messy text, code matching/policy/refund, LLM reply, code self-check, case record in DB, approval queue + fraud queue with a real human gate (`case_state`, `sent`, `POST /cases/{id}/actions` with a typed actor name), outbox, 750-complaint export, a simple UI showing queues, a case and the approval step |
| **Bonus MVP** | Sign-in with seeded users (auth and roles are bonus only; the core needs neither), role-filtered queues, officer resolution desk, fraud workbench, manager console with second-tier approval and reassignment, append-only audit, self-check on edits, agent-vs-human comparison |
| **Bonus extras** | Officer/analyst chatbot panel, manager charts, WebSocket live push, SLA timers, notifications |
| **Out of scope** | Real money movement, real customer messaging, production identity, cloud hosting (venue Wi-Fi or a tunnel is enough), vector DBs, policy-editing UI, API keys or rate limits on our API |

Refunds and customer messages are **simulated**: the backend enforces the approval gate and writes an outbound record (the outbox), and the UI labels it as simulated.

**Watched folder:** the README no longer asks for one; the live round uses `POST /complaints` only. Keep `inbox/` as an optional convenience that calls the same intake function.

---

## Team Split (2 backend developers + 1 UI developer)

Split by module so each developer owns separate files. **Dev A** owns the decision engine (code that does money and rules). **Dev B** owns the platform (LLM, DB, API, workflow). **Dev C** owns the React UI. Dev C joined after the backend split was set (coverage-check gap 1: the README asks for teams of 3–5, and the plan had only two roles).

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

| | Dev A — decision engine | Dev B — platform and LLM | Dev C — UI |
|---|---|---|---|
| Owns | `agent/tools.py`, `date_resolver.py`, `transaction_matcher.py`, `categories/*`, `router.py` (route, priority, language, hold, SLA), `self_check.py`, `eval/` | `llm/*` (interface, adapters, prompts, cache, cost), `agent/parser.py`, `reply_generator.py`, `pipeline.py`, `db/`, `api/` (the [api.md](api.md) contract first; bonus `/api/*` routes and `auth/` later), `batch/` (runner, export, validation), serving the API on the venue network | `frontend/` (React + TypeScript). Builds only against [UI_API.md](UI_API.md); missing backend fields go to Dev B instead of being worked around |
| Order | 1. Tools + date resolver<br>2. ATM handler (sets the pattern)<br>3. Unauthorised card, scam<br>4. Failed transfer, duplicate<br>5. Fee<br>6. Service quality<br>7. Self-check + routing/hold | 1. LLM interface + first adapter + extraction prompt<br>2. Pipeline + DB persistence<br>3. Reply drafting + redraft loop<br>4. Batch runner + export<br>5. **Contract API** (`/complaints`, `/cases/{id}`, `/cases/{id}/actions`, `/health`) passing `api_check.py`<br>6. Reachability (host `0.0.0.0` or tunnel) + messy-text prompt hardening<br>7. Bonus routes, auth, second adapter | 1. **Core UI first** (coverage-check gap 3): queues, case page with evidence and self-check, Approve / Edit & approve / Reject, fraud Acknowledge, dashboard, audit log<br>2. Login page + role screens: Officer Resolution Desk, Fraud Investigation Workbench, Manager Console<br>3. Charts and extras if time allows |
| Tests | Each handler scored on `labels_train.csv` without LLM calls; boundary tests (RM500, 10 min, birthdays, fee anniversaries) | `scoring/api_check.py` (contract, scores, robustness and human-in-the-loop probes); gate tests (send without approval, edited reply with invented amount → 422, 409 when not awaiting approval, repeat intake, double click); export validation | The human-gate checklist through the UI: a posted complaint appears on its own, approval holds until clicked, fraud lands in the fraud queue, the self-check refusal is visible; the three bonus demo flows |

**Shared files** (`contracts.py`, `config.py`, `requirements.txt`) change only in a dedicated PR the other developer approves.

A carries the most points (matching = 75 of 100). After Checkpoint 2, B helps A with error analysis on the weakest category.

### Integration milestones

| When | Goal | Merges |
|---|---|---|
| Day 1 ~12:00 | First real end-to-end path: real extraction → ATM handler → stored case | A: ATM handler. B: extractor + pipeline + DB |
| **Day 1 16:00 — Checkpoint 1** | 20 training complaints classified + matched | A: all matchers. B: runner with `--no-draft` |
| Day 1 evening | Full pipeline with draft + self-check; first 750 test run | Both |
| **Day 2 12:00 — Checkpoint 2** | Approval + write-back via the contract API on 50 training complaints; score posted; `api_check.py` passes; API reachable from another laptop | B: contract API. A: self-check on edits |
| Day 2 12:00–15:00 | Accuracy and messy-text robustness; final 750 export; **15:00 freeze** of agent + API | Both |
| Day 2 15:00–16:30 | Simple case/queue UI calling the same API, then bonus screens | Dev C, with Dev B on backend fixes |

Until Checkpoint 2 the core can be demoed through FastAPI `/docs`. The UI can keep changing after 15:00; the agent and API cannot.

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
│  1. Intake (POST /complaints; inbox/ optional)              │
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
│  Contract API (docs/api.md, no auth): /complaints,          │
│    /cases/{id}, /cases/{id}/actions, /health                │
│  Bonus /api/*: auth │ queues │ two-tier │ audit │ metrics   │
│  Outbound (simulated outbox) │ Chat + WebSocket (bonus)      │
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

**Bonus only.** For the main ranking, a typed `actor` name on `POST /cases/{id}/actions` is enough (README FAQ): no logins, no roles. Everything in this section is for the Best Ops Platform award.

| Role | Sees | Can do | Approval limit |
|---|---|---|---|
| **Complaints Officer** | HUMAN_APPROVAL queue | Approve / edit reply then approve / reject / send back. Escalate to manager if refund > their limit or case is sensitive | **RM2,000** (built) |
| **Fraud Analyst** | FRAUD_TEAM queue | Acknowledge / log investigation or recall attempt / record outcome. Escalate sensitive or high-value cases to manager | **RM5,000** (built) |
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

**Limits as built (b-ops-platform, decided by Dev B 2026-10-23):** officers RM2,000, fraud analyst RM5,000, manager none. No refund in the data is over RM5,000 (the largest is RM4,687.10), so a RM5,000 officer limit would never be reached; 128 of 466 approval refunds are over RM2,000, so the over-limit escalation shows up on its own. 126 of 520 fraud cases have a disputed transaction over RM5,000. 65+ customers are always sensitive (146 of 1,115 approval and 78 of 520 fraud cases).

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
refund_sen            integer sen; exported and served as a 2-decimal string ("550.00")
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
self_check            passed / flagged (API values) + offending IDs/amounts in run_json
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

content_hash          sha256 of the six fields: same ID + same hash = same complaint (POST again → existing case);
                      same ID + different hash → conflict (409), nothing changes

-- Contract state (docs/api.md; what GET /cases/{id} serves)
status                processing / done / error  (+ error text)
case_state            auto_resolved / awaiting_approval / with_fraud_team / approved / rejected
sent                  true once a reply reached the outbox
human_action          NULL until a human acts; then {action, actor, reason, at, reply_text}

-- Bonus platform state (added with the ops platform; never served in place of case_state)
workflow_status       escalated / sent_back / investigating / closed
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
actor                 typed name from the API (or "agent"); username once the bonus auth exists
action                ingest / agent_run / approve / edit_approve / reject / send_back /
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

**Contract mapping:** route → state when the agent decides: `AUTO_RESOLVE` → `auto_resolved`, `sent = true`; `HUMAN_APPROVAL` → `awaiting_approval`, `sent = false`; `FRAUD_TEAM` → `with_fraud_team`, `sent = false` (the holding reply goes out when an analyst acknowledges; bonus). `approve` / `edit_approve` → `approved`, `sent = true`; `reject` → `rejected`, nothing sent. Already built in the case store (`backend/db/`, OpenSpec change `b-batch-runner`).

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
- Few-shot examples from training data (EN + MS + mixed + call-centre note), **plus messy rewrites** (typos, SMS short forms like "sy x dpt duit", emoji, mixed language): the hidden test is written this way, and an agent tuned to `complaints.csv` wording will struggle. Build a small messy eval set by rewriting training complaints and score extraction on it
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
- **A refund reply must state the refund amount** (organisers check this automatically on every reply); the self-check fails a REFUND reply that doesn't mention it
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
- The batch runner and `POST /complaints` call the **same** agent function, so the live round tests the system that produced the leaderboard
- Score against training labels with `--details`, analyze errors by category; prioritise wrongful refunds, missed fraud, then matching failures
- **Target: Checkpoint 1 by 16:00 — 20 training complaints classified + matched**
- **First full 750 test run as soon as matching is stable (Day 1 evening).** Re-run only changed complaints later; never leave the 750 run for the last hour

### Phase 2: FastAPI Backend + DB + Core Workflow (Day 1, 16:00–17:30 + Day 2, 09:00–10:00 → Checkpoint 2)

Checkpoint 2 (Day 2 12:00) needs decision, reply, approval and write-back on 50 training complaints, `scoring/api_check.py` passing, and our API reachable from the organisers' laptop. All of that must work through the contract API before the UI is finished.

**2.1 The contract API (core, build first; [api.md](api.md))**: built in `backend/api/contract.py` + `backend/main.py`. `scoring/api_check.py` scores 100.0 (10 complaints) / 99.7 (30), 9/9 probes pass ([EXTRACTOR_RESULTS.md](EXTRACTOR_RESULTS.md#api-the-organisers-check-b-contract-api))
- `POST /complaints`: body = the six complaint fields. Return `202` with `{"complaint_id", "status": "processing"}` and run the agent in the background (bounded worker pool; the hidden test posts 20 at once and allows 120 s each)
  - Missing/empty `complaint_id`, `customer_id`, `received_at` or `text` → `400`/`422`, never `5xx`
  - Same ID again → existing case's status (`200`), no second case, no new decision; same ID with different content → `409`
  - Unknown `customer_id` → accept and flag the case (held, `customer_not_found`), never crash
- `GET /cases/{id}`: `404` if unknown; `{"status": "processing"}` while working; when `done`, every field: the 8 decision fields (as in predictions.csv; `matched_txn_id` is `""` when none, `refund_amount_myr` a 2-decimal string), `self_check` (`passed`/`flagged`), `case_state`, `sent`, `human_action`. `status: error` carries an `error` field
- `POST /cases/{id}/actions`: `{"action": "approve" | "reject" | "edit_approve", "actor", "reason", "reply_text"}`
  - `404` unknown case; `409` unless `case_state = awaiting_approval`; `422` for a missing actor, an unknown action, a missing reason on reject/edit_approve, or an edited reply that fails the self-check (nothing is sent)
  - `approve`/`edit_approve` → `approved`, `sent = true`, reply to the outbox; `reject` → `rejected`, nothing sent. `human_action` records action, actor, reason, time and the reply that went out. The agent's decision fields never change
  - Our UI's Approve/Reject buttons call this same endpoint, so the demo and the live round use one path
- `GET /health` → `200`
- Extra (not in api.md): `POST /cases/{id}/acknowledge {actor, reason}` lets a fraud analyst release the agent's holding reply (`sent = true`, case stays `with_fraud_team`). The bonus `/api/cases/{id}/acknowledge` should call the same store function
- The API server keeps its own database (`API_DB_PATH`, default `backend/api.db`), separate from the batch database behind predictions.csv, so probes and demo clicks never touch submission data
- No credentials on these routes: the organisers' script sends none
- **Serving:** `uvicorn backend.main:app --host 0.0.0.0 --port 8000` on the venue Wi-Fi, or an ngrok / Cloudflare tunnel. Running from 15:00 until our demo ends. One named person owns keeping it up; LLM keys stay on our side
- Self-test: `python scoring/api_check.py http://localhost:8000` (add `--n 30` for more complaints)

**2.2 DB Schema + Auth (auth is bonus)**
- SQLite: `agent_runs`, `cases`, `case_events`, `outbound_messages` (built); `users`, `llm_cache` later (schema above)
- Seed users (bonus):
  - `officer1`, `officer2` — Complaints Officer, approval_limit_myr = 2000 (two, so reassign can be shown)
  - `fraud1` — Fraud Analyst, approval_limit_myr = 5000
  - `manager1` — Manager, no limit
  - all share the demo password `teratai123` (bcrypt-hashed; `backend/db/seed.py`)
- Simple auth (bonus): seeded users + `role` column, JWT on login, role checks enforced **in the backend** on every `/api/*` route (hiding links is not enough). Never on the contract routes

**2.3 Bonus platform endpoints (`/api/*`, authenticated)**

**Built:** the four read routes (b-ops-read-api), then login, roles and every action below (b-ops-platform), documented for the UI in [UI_API.md](UI_API.md). Reads work without a token while `AUTH_REQUIRED` is off (the manager's view); with a token they're filtered by role. Actions always need a token. The contract routes stay open but refuse (409) a case that is escalated, re-running or closed on the platform.

These serve the role screens. They read the same case store and record the same `human_action` / `case_events`; first-tier approve and reject go through the same function as `POST /cases/{id}/actions`.
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

**2.4 Intake + Write-back**
- `POST /complaints` is the intake: persists the case first, then runs the pipeline in the background; clients poll `GET /cases/{id}`
- Optional: watched folder `inbox/` and a CSV-paste form call the same intake function
- Unknown `customer_id` is accepted and stored, never dropped: no transaction lookup, held with `customer_not_found` (HUMAN_APPROVAL, or FRAUD_TEAM if INVESTIGATE); same complaint ID + identical content returns the existing case; same ID + different content is rejected
- AUTO_RESOLVE cases: self-check pass → outbound record (`authorised_by = auto`) → `sent` → `closed`
- Every human-gated send goes through one backend function that checks: right role, approved (and second-tier approved if escalated), current reply passed self-check, not already sent. Protects against double clicks and retries
- Pipeline or delivery failure leaves a visible `failed` state with retry

### Phase 3: Frontend (Day 2; the UI may keep changing until 16:30)

**Core minimum (for the main ranking and the human gate):** one page that shows the three queues (auto-resolved, awaiting approval, fraud team), one case (complaint, matched transaction, evidence, decision, reply, self-check result) and Approve / Edit & Approve / Reject buttons calling `POST /cases/{id}/actions`. A simple web page, Streamlit or Gradio is enough: judges score clarity, not polish (README FAQ). Build this before the role screens.

**Bonus: three distinct interfaces, not one generic queue.**

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

**3.6 Intake Form** *(optional; the live round posts to the API directly)*
- Input: complaint_id, customer_id, received_at, channel, subject, text, or paste one JSON/CSV row
- Calls `POST /complaints` → shows processing state → result appears in the correct queue
- Useful for rehearsing; judges' complaints arrive through the API and must appear in the UI on their own

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

### Phase 5: Integration + Submission (Day 2, 13:00–15:00, then demo at 16:30)

- Run `scoring/api_check.py` against the served URL (from another laptop on the same network if possible); fix contract or probe failures first

- Re-run changed test complaints; export predictions.csv from autonomous runs
- Validate export: exactly 750 unique test IDs, correct header, valid enums, two-decimal amounts, non-empty replies. Missing or failed predictions are surfaced, never filled with invented answers
- Score training set, final error analysis
- End-to-end demo test:
  1. HUMAN_APPROVAL within limit → officer approves (or edits, triggering self-check) → sent
  2. HUMAN_APPROVAL over limit → officer escalates → manager approves → sent
  3. FRAUD_TEAM → analyst acknowledges → holding reply sent → investigation logged
- Live round rehearsal: post `examples/live_complaint_example.json` and a few messy rewrites to the running API; watch each case appear in the UI on its own; approve one through the UI
- Show audit log + agent-vs-human gap across all three
- **15:00 freeze** of agent + API: PR from fork with predictions.csv, **freeze commit hash** and **API URL** in the description
- Keep the API running and reachable 15:00 → end of our demo (hidden test 15:00–15:45); don't redeploy the agent after the freeze
- 15:00–16:30: UI and bonus work only

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
│   ├── schema.py              # agent_runs, cases, case_events, outbound_messages (users later; llm_cache lives in backend/.cache)
│   ├── store.py               # CaseStore: runs, case state, human actions (role-filtered queries later)
│   └── seed.py                # Demo users (officer, fraud, manager)
├── auth/
│   ├── router.py              # /api/auth/*
│   ├── jwt.py                 # Token create/verify
│   └── dependencies.py        # get_current_user, require_role
├── api/
│   ├── contract.py            # docs/api.md: /complaints, /cases/{id}, /cases/{id}/actions, /health (+ /acknowledge); built
│   ├── cases.py               # Bonus: role-filtered /api/* CRUD + actions
│   ├── watcher.py             # Optional: inbox/ folder watcher → same intake path (not built)
│   ├── outbound.py            # Gated simulated send
│   ├── audit.py               # Audit log queries
│   ├── metrics.py             # KPIs + chart data (manager)
│   ├── export.py              # predictions.csv export + validation
│   ├── chat.py                # SSE chatbot (bonus)
│   └── websocket.py           # Real-time push (bonus)
├── llm/
│   ├── client.py              # LLMClient interface, cache, usage/cost tracking
│   ├── registry.py            # provider:model per step, startup checks
│   ├── openai_compatible_adapter.py  # OpenRouter or any /chat/completions endpoint
│   ├── fake_adapter.py        # offline, tests
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
- **Contract (`api_check.py` probes):** `/health` 200; unknown case 404; missing text 4xx; unknown customer no 5xx; same complaint twice → no change, no duplicate; awaiting-approval case shows `sent: false`; edited reply with an invented amount → 422 and nothing sent; approve → `approved`, `sent: true`, actor recorded, decision unchanged; 20 concurrent complaints all `done` within 120 s
- **Messy text:** extraction and end-to-end score on rewritten training complaints (typos, SMS short forms, emoji, mixed language)

---

## Demo Script (about 10 minutes, from 16:30)

**1. Show the system (1 min)**
- Architecture overview (LLM does language, code does money), three role logins

**2. Human gate: judges send 3 complaints through our API (4 min, 10 points)**
- Each case appears in the UI on its own; show the matched transaction, evidence, decision, route, reply and self-check result
- A case needing approval waits (`case_state: awaiting_approval`, `sent: false`) until someone approves it in our UI
- A fraud case lands in the fraud queue

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
| Organisers can't reach our API | Test from a second laptop at Checkpoint 2; tunnel as a backup; one owner keeps it running from 15:00 |
| Hidden test is messier than training | Messy few-shots and a rewritten eval set; matching and policy stay in code |
| 20 concurrent complaints exceed 120 s | Bounded worker pool, LLM cache, timeouts with one retry; measure with `api_check.py` |
| Scoring edge cases | Run scorer after every change, analyze wrongs |
| Frontend not ready | Pipeline + batch runner + API still deliver leaderboard and Checkpoint 2 |
| Secrets leak (public repo) | Keys only in env vars; `.env` gitignored |
| A complaint raises two issues; the second is dropped | LLM issues check plus code quote verification holds the case for an officer (`b-second-issue`). See [Complaints with two issues](#complaints-with-two-issues) |

---

## Complaints with two issues

Proposed by Dev A on 2026-10-23; it needs Dev B's agreement before any code is written.

> **Status (agreed by Dev A and Dev B, 2026-10-23):** the problem below stands. **The phrase-list fix was replaced** by an LLM issues check that runs alongside extraction, with code verifying every quote (OpenSpec change `b-second-issue`, `backend/agent/issues.py`). The reason: on 6 ordinary single-issue sentences in real customer style, the phrase list wrongly flagged 5. "kena caj 2 kali", "kad ATM" and "used my card twice" all use another category's words without raising that problem; our data didn't show this because it's written cleanly. The hold, the hold reason `second_issue`, the natural-overlap rule and the demo answer are kept from this plan. Results are in [EXTRACTOR_RESULTS.md](EXTRACTOR_RESULTS.md#second-issue-check-b-second-issue).

### The problem

The extractor gives each complaint one category, so a second issue in the same message is dropped. When the main issue auto-resolves, no one ever reads the second. Nothing in the extraction prompt covers this.

Six mixed complaints, run through the real LLM extractor and the engine. Every main issue was handled correctly, with a confident match and the right transaction:

| Test | Second issue | Main category | Route | Does a person see the second issue? |
|---|---|---|---|---|
| Failed transfer + fee | "pastu ada caj fee pulak" | FAILED_TRANSFER, refund RM46.54 | AUTO_RESOLVE | **No** |
| Duplicate + service | "staff kurang ajar and tak nak tolong" | DUPLICATE_CHARGE, refund RM149.87 | AUTO_RESOLVE | **No** |
| ATM + service | "call hotline 3 kali xde org angkat" | ATM_NOT_DISPENSED, refund RM600 | HUMAN_APPROVAL | Yes, because the refund is over RM500 |
| Fee + service | "app korang asyik logout" | FEE_DISPUTE, decline | HUMAN_APPROVAL | Yes, because declines are held |
| Unauthorised + ATM | "atm pun tak keluar duit" | UNAUTHORISED_CARD, investigate | FRAUD_TEAM | Yes, by the fraud team |
| Scam + unauthorised | "card transaction yg bukan saya buat" | SCAM_TRANSFER, investigate | FRAUD_TEAM | Yes, by the fraud team |

The leaderboard score is not affected: each complaint has one label, and route is not scored. The risk is a judge testing this live.

### The fix: a second-issue check in code

After the engine decides, check whether the complaint body also carries a clear sign of a different category. If it does, hold the case for a person. Category, transaction, outcome, refund, priority and language stay exactly as the agent decided; only `route` and `hold_reason` change.

1. Extraction and the engine run as today.
2. In `finalize_decision` (`router.py`), call `find_second_issues(updated.category, complaint.text)`. Put the call after the existing hold step and before the customer-not-found check.
3. It scans the body, not the subject, for phrases that belong to another category:

   | Category | Phrases |
   |---|---|
   | SCAM | scam, tipu, penipu, scammer |
   | ATM | `atm` as a whole word |
   | DUPLICATE | twice, dua kali, 2 kali, double |
   | UNAUTHORISED | bukan saya, did not make, didn't make, not me, tak buat, tidak membuat |
   | FEE | fee(s), caj, yuran, service charge |
   | FAILED | duitnow, ibg, or "transfer" followed by fail / gagal / tak sampai / did not arrive |
   | SERVICE | hotline, call centre, staff, kakitangan, rude, kurang ajar, logout, log out, queue, beratur, no one answered, tak angkat, xde org |

4. Normal overlaps are ignored. A scam story often says "transfer" or "failed", and an unauthorised complaint can say "tipu". These cases go to FRAUD_TEAM anyway.
5. If anything is found, call `hold(decision, "second_issue")`. The existing `hold()` keeps an earlier hold reason, keeps INVESTIGATE on FRAUD_TEAM and sends everything else to HUMAN_APPROVAL.
6. Because the route is now HUMAN_APPROVAL, the reply uses the "will be credited after review" wording, and nothing is sent until an officer approves.
7. The officer sees "Complaint raises a second issue", reads the text, and uses Edit & approve to acknowledge it. The self-check re-runs on the edited reply.

```python
# backend/agent/second_issue.py  (Dev A)
CUES: dict[str, list[re.Pattern]] = {...}           # the table above
NATURAL_OVERLAP = {"SCAM_TRANSFER": {"FAILED_TRANSFER", "UNAUTHORISED_CARD"},
                   "UNAUTHORISED_CARD": {"SCAM_TRANSFER"}}

def find_second_issues(category: str, text: str) -> list[str]:
    t = text.lower()
    skip = NATURAL_OVERLAP.get(category, set()) | {category}
    return [c for c, pats in CUES.items() if c not in skip and any(p.search(t) for p in pats)]
```

### Evidence

We tried the phrase list on real data with a scratch script; nothing is committed yet.

| Set | Complaints | Flagged | Meaning |
|---|---|---|---|
| Mixed tests | 6 | 5 | All caught. Scam + unauthorised is skipped on purpose; it already goes to FRAUD_TEAM |
| Training (one label each) | 1,750 | 0 | No false flags |
| Test set (current predictions) | 750 | 0 | `predictions.csv` does not change |

Two adjustments took the false flags from 46 to 0:

- **"branch" and "cawangan" were dropped.** ATM locations read like "Miri Branch ATM", which caused 28 false flags.
- **The subject line is not scanned.** Duplicate complaints use the subject "Caj berganda", which matches "caj" and caused 18 false flags.

### Changes by file

| File | Change | Owner |
|---|---|---|
| `backend/agent/second_issue.py` (new) | `find_second_issues()` with the phrase list and the overlap rules | A |
| `backend/agent/router.py` | One call in `finalize_decision` (step 2) | A |
| `backend/contracts.py` | Add `"second_issue"` to `HoldReason` | Shared: a small separate commit that B approves |
| `backend/db/queries.py` | `HOLD_TEXT["second_issue"] = "Complaint raises a second issue"` | B |

Nothing else changes:

- `hold_reason` is a plain TEXT column, and the `/api/cases` filter reads its values from `HoldReason`.
- Without the `HOLD_TEXT` line the UI shows no reason text, but nothing breaks.
- The extraction prompt doesn't change, so the LLM cache stays valid and nothing is re-extracted.

### Steps (about 1.5 h, merged before the 15:00 freeze)

If it is not green by 14:00, drop it and use the demo answer below.

- [ ] 1. B agrees to the task, including the `contracts.py` and `queries.py` lines
- [ ] 2. A: branch `feat/a-second-issue`; add `second_issue.py` and the `router.py` call
- [ ] 3. Shared commit on that branch: add `"second_issue"` to `HoldReason` (B approves)
- [ ] 4. A: unit tests and a full `pytest` run
- [ ] 5. A: regression gate (table below), all from the LLM cache at no cost
- [ ] 6. Merge to `dev` with `--no-ff`; tick it in `STATUS.md`
- [ ] 7. B: add the `HOLD_TEXT` line, restart the server, run `api_check`
- [ ] 8. Both: post the 6 mixed complaints to the running API and check each lands in the right queue

### Tests and the regression gate

Unit tests (`backend/tests/test_second_issue.py`):

- The 5 mixed texts each return the expected second category.
- These return nothing:
  - a scam text containing "transfer" or "failed"
  - an unauthorised text containing "tipu"
  - "Miri Branch ATM" in an ATM complaint
- Router:
  - A RM46.54 refund with a second issue becomes HUMAN_APPROVAL with `second_issue`; all scored fields are unchanged.
  - An INVESTIGATE case stays on FRAUD_TEAM.
  - An earlier hold reason such as `ambiguous_match` is kept.

Do not merge unless every row passes:

| Check | Must show |
|---|---|
| `pytest` | 2,334 + new, all pass |
| Training: `runner --ids train --no-draft --db <scratch db>`, then `submit --ids train --score` | 99.94, 0 critical errors, 0 `second_issue` holds |
| Test set regenerated into a scratch file vs `submissions/Santa_Claude/predictions.csv` | 0 rows changed |
| `python scoring/api_check.py http://localhost:8000` | 100.0, 9/9 probes |
| The 6 mixed complaints posted to the API | 4 `awaiting_approval` with `sent: false`, 2 `with_fraud_team` |

### Risks and rollback

A missed second issue behaves exactly as today, and a false flag only sends a case to an officer. No money moves either way.

| Risk | Mitigation |
|---|---|
| A judge's wording isn't in the list ("customer service teruk", "app crash", "lama sangat tunggu") | Add phrases in step 2 only if training and test still show 0 flags |
| A bare "app" phrase would be too broad ("transferred via the app") | Not used; only specific phrases such as "logout" |
| Two issues in the same category (two ATM withdrawals) | Out of scope; mention it in the demo answer |
| A late merge breaks the API before the hidden test | The regression gate must pass; drop the fix if it isn't green by 14:00 |

Rollback: `git revert -m 1 <merge commit>` on `dev`, then restart the server. `predictions.csv` doesn't depend on this change.

### Demo answer for the judges

With the fix in place:

1. The money issue is handled in code: transaction, rule and refund are shown as usual.
2. The case waits in the officer queue with the reason "Complaint raises a second issue". It shows `awaiting_approval` with `sent: false`.
3. The officer uses Edit & approve to acknowledge the second issue, and the self-check re-runs.
4. If either issue is a scam or an unauthorised card, the case goes to the fraud team, who read the full text.

Without the fix: "The agent picks the issue with money or fraud risk and handles it exactly. Declines, refunds over RM500 and every fraud case already go to a person who reads the full text. The gap is a small auto-resolved refund with a second, non-money issue; the planned fix holds those cases for an officer."

### Not now

**1. An `other_issues` field in extraction (after the hackathon).** The extractor would return something like `{"category": "FAILED_TRANSFER", "other_issues": ["FEE_DISPUTE"], ...}`. The LLM understands meaning, so it would catch any wording, not just a fixed list. It is not worth the risk before the freeze:

- **Cache reset.** The cache key is a hash of the prompt, so a prompt change re-extracts all 2,500 complaints: about RM3–4 and 20–30 min.
- **Score risk.** A changed prompt can shift some main categories, amounts or dates, which can change the matched transaction or refund. That means re-scoring training, regenerating `predictions.csv`, redrafting changed replies and re-measuring everything in `EXTRACTOR_RESULTS.md` before 15:00.
- **Files touched.** It touches `prompts.py` (prompt and schema), all 12 `fewshot.json` examples, and the `Clues` model in `contracts.py`, which forbids unknown fields.

**2. The reply mentions the second issue (optional, B, only if time is left after the fix).** In `build_draft_messages`, when `find_second_issues()` finds something, add a fact such as `ALSO RAISED: the fee charge. Say in one sentence it has been passed to the team concerned; promise nothing.` Only flagged complaints change their draft request. None of the 750 are flagged, so the cache holds and nothing is redrafted.

| Option | Catches | Score risk | Time | When |
|---|---|---|---|---|
| Phrase-list check (this plan) | Common wording | None | About 1.5 h | Before 15:00 |
| + reply mentions the second issue | Same cases, better reply | None | About 30 min | Before 15:00, if there's time |
| LLM `other_issues` field | Any wording | Yes | About half a day | After the hackathon |

---

## Success Metrics

| Metric | Target | Baseline |
|---|---|---|
| Training score | >85 | 31.9 |
| Critical error rate | <1% | — |
| Speed per complaint | <10 seconds | — |
| Cost per complaint | Measured and shown on dashboard | — |
| Live round: hidden test | 20/20 `done` within 120 s; score close to training score | — |
| Live round: human gate | All checklist items pass on 3 complaints | — |
| `api_check.py` probes | All pass | — |
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
| `with_fraud_team`: should a holding reply go out automatically (`sent` may be either)? | No automatic holding reply in the core: `sent = false` (as the case store does); the bonus fraud workbench sends it on acknowledge |
