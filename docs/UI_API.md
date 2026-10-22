# Backend API for the UI

For whoever builds the React UI. It covers everything the screens need from the backend: how to run it locally, which endpoint feeds which screen, the exact JSON, and TypeScript types to copy.

- **Read data** with the `/api/*` routes in this guide. There's no login yet. When the bonus login arrives, the same routes will take a token, and this guide will say so in the [changelog](#changelog).
- **Change data** (Approve, Edit & approve, Reject, Acknowledge) with the organisers' contract routes in [api.md](api.md). They're summarised [below](#buttons-actions).
- Interactive docs: start the server and open **http://localhost:8000/docs**. You can try every route there.

## Run the backend locally (free, no API key)

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --port 8000
```

With no `.env` file, the backend uses the offline **fake** models:
- a keyword extractor
- code-written replies

These cost nothing, need no key and give realistic decisions. If you do have a `.env` with real models, override it for your shell. PowerShell: `$env:LLM_EXTRACT="fake:keywords"; $env:LLM_DRAFT="fake:template"`. bash: `LLM_EXTRACT=fake:keywords LLM_DRAFT=fake:template uvicorn ...`.

The server keeps its cases in `backend/api.db`. Delete that file (with the server stopped) to start empty.

### Put some cases in it

The database starts empty. To fill it, use either of these:

```bash
# 50 pilot complaints (or --ids test for the 750 test complaints), written straight into the API's database
python -m backend.batch.runner --ids pilot --db backend/api.db

# or one complaint through the API, the way the judges will send them
curl -X POST localhost:8000/complaints -H "content-type: application/json" -d "{\"complaint_id\":\"DEMO-0001\",\"customer_id\":\"CUS-02394\",\"received_at\":\"2026-07-20 22:32\",\"channel\":\"Email\",\"subject\":\"ATM\",\"text\":\"The machine did not dispense all of the cash when I withdrew about RM1,500 last Friday.\"}"
```

The runner can write while the server is running; new cases show up on the next poll. Don't run it while `scoring/api_check.py` is running.

**For the demo**, fill the API database with the 750 test complaints using the real models. The answers come from the LLM cache, so it's free and quick. The dashboard then has real numbers.

## Conventions (every `/api` route)

| Thing | Format | Example |
|---|---|---|
| Money | string, 2 decimals (keeps cents exact; don't parse to float for display) | `"550.00"` |
| Cost | string in RM, 4 decimals (a complaint costs well under 1 sen) | `"0.0013"` |
| Date and time | ISO 8601, Malaysia time, **no offset**. Don't convert time zones | `"2026-07-20T22:32:00"` |
| Rates | number from 0 to 1 | `0.346` |
| Missing | `null` (for example, decision fields while the agent is still working) | |

**Errors:**
- `404`: unknown case
- `409`: the case isn't in the right state, such as a double click on Approve
- `422`: bad input. The body is `{"detail": "..."}`, or for a refused reply edit `{"detail": {"error", "problems": [...]}}`

Display dates as `DD-MM-YYYY HH:MM`, as the bank does. The raw evidence rows (`evidence.matched_txn` etc.) are the CSV rows as they are. Their `txn_time` looks like `"2026-07-17 07:20:56"`, and an extra ISO `time` field is added.

## Which endpoint feeds which screen

| Screen | Call |
|---|---|
| Queue tabs with counts (Auto-resolved, Awaiting approval, Fraud team, Approved, Rejected, Processing, Error) | `GET /api/cases?queue=...`, using `counts` for the tab badges |
| Case page (complaint, matched transaction, evidence, decision, reply, self-check, audit trail) | `GET /api/cases/{id}` |
| Approve / Edit & approve / Reject buttons | `POST /cases/{id}/actions` |
| Fraud "Acknowledge" (sends the holding reply) | `POST /cases/{id}/acknowledge` |
| Manager dashboard tiles | `GET /api/metrics?as_of=...` |
| Audit log page | `GET /api/audit` |

**Polling:** poll the list every 3–5 s. A new complaint appears with `queue: "processing"` and moves to its queue a few seconds later (`sort=recent` shows it first). Poll a case page every 2 s only while its `case.queue` is `processing`.

---

## `GET /api/cases`: the queues

| Parameter | Values | Default |
|---|---|---|
| `queue` | `processing`, `error`, `auto_resolved`, `awaiting_approval`, `with_fraud_team`, `approved`, `rejected` | all |
| `route` | `AUTO_RESOLVE`, `HUMAN_APPROVAL`, `FRAUD_TEAM` | all |
| `category` | `DUPLICATE_CHARGE`, `FAILED_TRANSFER`, `ATM_NOT_DISPENSED`, `UNAUTHORISED_CARD`, `SCAM_TRANSFER`, `FEE_DISPUTE`, `SERVICE_QUALITY` | all |
| `priority` | `P1`, `P2`, `P3` | all |
| `hold_reason` | `customer_not_found`, `ambiguous_match`, `no_match`, `category_revised`, `self_check_failed`, `unknown_auth_method`, `llm_error`, `none` (no hold) | all |
| `q` | search text: case ID, customer ID, customer name or subject (any case) | |
| `sort` | `priority` (P1 first, then the earliest SLA due date) or `recent` (latest activity first) | `priority` |
| `limit`, `offset` | page size 1–500, and the start | `50`, `0` |

- Each enum filter takes one value or a comma list: `queue=approved,rejected`.
- Different filters combine with AND.
- An unknown value returns 422.
- `counts` always covers **all** cases, whatever the filters, so the tab badges stay right.

`waiting_reason` is the line to show in the queue row, saying why the case is waiting: "Refund over RM500", "Decline needs approval", "Ambiguous match", "Fraud investigation", "Fraud investigation · Customer not found", "Agent is working on it". It is `null` for closed cases.

Example, `GET /api/cases?queue=awaiting_approval,with_fraud_team` (real output from the offline models):

```json
{
  "total": 2, "limit": 50, "offset": 0,
  "counts": {"processing": 0, "error": 0, "auto_resolved": 1, "awaiting_approval": 1,
             "with_fraud_team": 1, "approved": 0, "rejected": 1},
  "items": [
    {
      "complaint_id": "CMP-00005", "customer_id": "CUS-02802", "customer_name": "Wong Wei Ming",
      "received_at": "2026-08-25T14:06:00", "channel": "App chat", "subject": "",
      "status": "done", "queue": "with_fraud_team", "case_state": "with_fraud_team", "sent": false,
      "category": "SCAM_TRANSFER", "outcome": "INVESTIGATE", "refund_amount_myr": "0.00", "priority": "P1",
      "route": "FRAUD_TEAM", "hold_reason": null, "self_check": "passed", "vulnerable": false,
      "resolve_due_at": "2026-08-28T14:06:00", "waiting_reason": "Fraud investigation",
      "human_action": null, "updated_at": "2026-10-23T00:23:15"
    },
    {
      "complaint_id": "CMP-00244", "customer_id": "CUS-02394", "customer_name": "Aisyah binti Kassim",
      "received_at": "2026-07-20T22:32:00", "channel": "Email", "subject": "ATM did not dispense cash",
      "status": "done", "queue": "awaiting_approval", "case_state": "awaiting_approval", "sent": false,
      "category": "ATM_NOT_DISPENSED", "outcome": "REFUND", "refund_amount_myr": "550.00", "priority": "P2",
      "route": "HUMAN_APPROVAL", "hold_reason": null, "self_check": "passed", "vulnerable": false,
      "resolve_due_at": "2026-07-29T22:32:00", "waiting_reason": "Refund over RM500",
      "human_action": null, "updated_at": "2026-10-23T00:23:15"
    }
  ]
}
```

`vulnerable: true` means the customer is 65 or older. Worth a badge.

## `GET /api/cases/{id}`: one case, and why

Everything about the case, in sections. This is the "show why it decided" screen, which the judges score under Engineering.

| Section | What to show |
|---|---|
| `case` | State, `sent`, `waiting_reason`, `human_action` (who acted, when, why, the reply sent), error if the agent failed |
| `complaint` | The customer's text, channel, subject, received time |
| `customer` | Name, date of birth, preferred language, segment, and `accounts`. `null` if the customer ID is unknown |
| `clues` | What the LLM read from the text: category, language, amount, approximate or not, date phrase, card, merchant |
| `match` | `status` (`confident`, `ambiguous`, `none`, `not_applicable`) and `candidates`: each transaction considered, its score (0–1) and the reasons. The first is the chosen one |
| `decision` | Outcome, refund, priority, route, `rule_id` (for example `ATM.SHORTFALL_REFUND`), and `calculation.explanation`, as in "1500.00 requested − 950.00 dispensed = 550.00 refund". Also `hold_reason`, SLA due dates and `vulnerable` |
| `evidence` | The matched transaction row, related transactions (for example the earlier charge of a duplicate), reversal, ATM journal, fee schedule row, and the IDs and amounts a reply may mention |
| `reply` | The agent's reply text, `redraft_count`, and `self_check` (`passed`, and the `problems` if not) |
| `usage` | Cost (RM) and time (ms) of this complaint, models used, tokens, cache hits |
| `runs` | Every agent run of this case (normally one) |
| `events` | The audit trail of this case, oldest first |
| `outbound` | Messages sent to the customer: `resolution` or `holding_reply`, who authorised it, and the refund |

While the agent is still working, or if it failed, only `case`, `complaint`, `runs`, `events` and `outbound` are filled; the rest are `null`. An unknown ID returns 404.

Example, `GET /api/cases/CMP-00244` (real output, trimmed: one candidate, fewer transaction fields):

```json
{
  "case": {"complaint_id": "CMP-00244", "status": "done", "queue": "awaiting_approval",
           "case_state": "awaiting_approval", "sent": false, "error": null,
           "waiting_reason": "Refund over RM500", "human_action": null,
           "autonomous_run_id": "1a81b9ad90d1483982d22d9ce6c9816b", "current_run_id": "1a81b9ad90d1483982d22d9ce6c9816b",
           "created_at": "2026-10-23T00:23:15", "updated_at": "2026-10-23T00:23:15"},
  "complaint": {"customer_id": "CUS-02394", "received_at": "2026-07-20T22:32:00", "channel": "Email",
                "subject": "ATM did not dispense cash",
                "text": "Hello, the machine did not dispense all of the cash when I withdrew about RM1,500 last Friday, but the whole amount was deducted. Please resolve this quickly."},
  "customer": {"customer_id": "CUS-02394", "full_name": "Aisyah binti Kassim", "date_of_birth": "1994-12-20",
               "state": "Sarawak", "city": "Miri", "segment": "Retail", "preferred_language": "MS",
               "email": "aisyah.kassim77@mail.example", "customer_since": "2012-09-15",
               "accounts": [{"account_id": "ACC-003802", "customer_id": "CUS-02394", "product": "Savings Plus",
                             "open_date": "2012-11-07", "status": "Active", "card_last4": "2832"}]},
  "clues": {"category": "ATM_NOT_DISPENSED", "language": "EN", "is_mixed_language": false,
            "amount_mentioned": "1500.00", "other_amounts": [], "amount_approximate": true,
            "counterparty_name": null, "counterparty_bank": null, "atm_location": null, "date_phrase": null,
            "date_exact": null, "card_last4": null, "fee_type": null, "fee_month": null},
  "match": {"status": "confident", "txn_id": "TXN-0088211", "category": "ATM_NOT_DISPENSED", "category_revised": false,
            "candidates": [{"txn_id": "TXN-0088211", "score": 0.9,
                            "reasons": ["amount match (1.00)", "date in range", "no location filter"]}]},
  "decision": {"category": "ATM_NOT_DISPENSED", "matched_txn_id": "TXN-0088211", "outcome": "REFUND",
               "refund_amount_myr": "550.00", "priority": "P2", "reply_language": "EN",
               "route": "HUMAN_APPROVAL", "policy_route": "HUMAN_APPROVAL", "rule_id": "ATM.SHORTFALL_REFUND",
               "calculation": {"explanation": "1500.00 requested − 950.00 dispensed = 550.00 refund",
                               "inputs": {"requested": "1500.00", "dispensed": "950.00", "shortfall": "550.00"}},
               "hold_reason": null, "vulnerable": false,
               "ack_due_at": "2026-07-21T22:32:00", "resolve_due_at": "2026-07-29T22:32:00"},
  "evidence": {"matched_txn": {"txn_id": "TXN-0088211", "txn_time": "2026-07-17 07:20:56", "account_id": "ACC-003802",
                               "direction": "DR", "amount_myr": "1500.00", "channel": "ATM Withdrawal",
                               "merchant_or_counterparty": "Miri Mall", "card_last4": "2832",
                               "auth_method": "Chip+PIN", "status": "Completed", "description": "ATM-MIR-02",
                               "time": "2026-07-17T07:20:56"},
               "related_txns": [], "reversal": null,
               "atm_journal": {"txn_id": "TXN-0088211", "atm_id": "ATM-MIR-02", "atm_location": "Miri Mall",
                               "requested_myr": "1500.00", "dispensed_myr": "950.00",
                               "journal_status": "PARTIAL_DISPENSE"},
               "fee_schedule_row": null,
               "allowed_txn_ids": ["TXN-0088211"], "allowed_amounts": ["1500.00", "950.00", "550.00"]},
  "reply": {"text": "Dear Aisyah binti Kassim,\n\nThank you for contacting Teratai Bank about an ATM withdrawal. We have reviewed transaction TXN-0088211 on 17-07-2026 (RM1,500.00). A refund of RM550.00 will be credited to your account once our review is complete. We will update you by 29-07-2026.\n\nYours sincerely,\nTeratai Bank Customer Care",
            "redraft_count": 0,
            "self_check": {"passed": true, "problems": [], "found_txn_ids": ["TXN-0088211"],
                           "found_amounts": ["1500.00", "550.00"]}},
  "usage": {"cost_myr": "0.0000", "latency_ms": 1, "prompt_version": "keywords+code-template",
            "schema_version": "keywords", "policy_version": "v0",
            "extract": {"provider": "fake", "model": "keywords", "tokens_in": 0, "tokens_out": 0, "cost_myr": "0.0000",
                        "latency_ms": 0, "retries": 0, "cached": false},
            "draft": [{"provider": "fake", "model": "code-template", "tokens_in": 0, "tokens_out": 0,
                       "cost_myr": "0.0000", "latency_ms": 0, "retries": 0, "cached": false}]},
  "runs": [{"run_id": "1a81b9ad90d1483982d22d9ce6c9816b", "run_kind": "autonomous", "created_at": "2026-10-23T00:23:15",
            "route": "HUMAN_APPROVAL", "outcome": "REFUND", "hold_reason": null, "cost_myr": "0.0000", "latency_ms": 1}],
  "events": [
    {"id": 1, "complaint_id": "CMP-00244", "actor": "agent", "action": "ingest", "run_id": null, "detail": null,
     "created_at": "2026-10-23T00:23:15"},
    {"id": 2, "complaint_id": "CMP-00244", "actor": "agent", "action": "agent_run",
     "run_id": "1a81b9ad90d1483982d22d9ce6c9816b",
     "detail": {"route": "HUMAN_APPROVAL", "hold_reason": null, "error": null, "previous_run_id": null},
     "created_at": "2026-10-23T00:23:15"},
    {"id": 10, "complaint_id": "CMP-00244", "actor": "Aina (officer)", "action": "edit_approve_refused",
     "run_id": "1a81b9ad90d1483982d22d9ce6c9816b",
     "detail": {"reason": "friendlier",
                "problems": ["transaction TXN-0000001 is not in the evidence", "amount RM999.00 is not in the evidence",
                             "the reply does not state the refund amount RM550.00"],
                "reply_text": "We will refund RM999.00 for TXN-0000001."},
     "created_at": "2026-10-23T00:23:15"}
  ],
  "outbound": []
}
```

With real models, `usage` shows `openrouter` models, real token counts and costs like `"0.0013"`. A run served from the LLM cache costs `"0.0000"` and has `cached: true`.

## Buttons (actions)

These are the contract routes in [api.md](api.md). They return the contract's short case view; re-fetch `GET /api/cases/{id}` afterwards to redraw the page. `actor` is the name the person types, since there's no login yet. Make it a text box, or remember it in the browser.

| Queue (`case.queue`) | Buttons | Request |
|---|---|---|
| `awaiting_approval` | **Approve** | `POST /cases/{id}/actions` `{"action": "approve", "actor": "Aina"}` |
| | **Edit & approve**: textarea pre-filled with `reply.text`, plus a reason | `{"action": "edit_approve", "actor": "Aina", "reason": "...", "reply_text": "..."}` |
| | **Reject**: reason required | `{"action": "reject", "actor": "Aina", "reason": "..."}` |
| `with_fraud_team` and `sent` is false | **Acknowledge**: sends the agent's holding reply; the case stays with the fraud team | `POST /cases/{id}/acknowledge` `{"actor": "Farid", "reason": "..."}` |
| everything else | none (read-only) | |

What can go wrong:
- **Edit & approve with a reply that fails the self-check:** `422`, and nothing is sent. Show the `problems` list next to the textarea. This is a demo moment: "the system blocked an invented amount".

  ```json
  {"detail": {"error": "edited reply fails the self-check; nothing was sent",
              "problems": ["transaction TXN-0000001 is not in the evidence", "amount RM999.00 is not in the evidence",
                           "the reply does not state the refund amount RM550.00"]}}
  ```
- **Missing actor or reason:** `422 {"detail": "reason is required for reject"}`.
- **Already acted on (double click, or another person was faster):** `409`. Re-fetch and show the new state.

## `GET /api/metrics`: the dashboard

| Parameter | Meaning |
|---|---|
| `as_of` | The clock for the SLA tiles (`2026-09-30T16:30` or `2026-09-30`). Default: now |

**Use `as_of=2026-09-30T16:30` in the demo.** The complaints are from July–September 2026, so against today's clock every open case looks overdue. The live round is dated 30 September.

Real output from the offline run:

```json
{
  "cases": {"total": 4,
            "by_queue": {"processing": 0, "error": 0, "auto_resolved": 1, "awaiting_approval": 1,
                         "with_fraud_team": 1, "approved": 0, "rejected": 1},
            "by_route": {"AUTO_RESOLVE": 1, "HUMAN_APPROVAL": 2, "FRAUD_TEAM": 1},
            "by_category": {"DUPLICATE_CHARGE": 0, "FAILED_TRANSFER": 2, "ATM_NOT_DISPENSED": 1, "UNAUTHORISED_CARD": 0,
                            "SCAM_TRANSFER": 1, "FEE_DISPUTE": 0, "SERVICE_QUALITY": 0},
            "by_priority": {"P1": 1, "P2": 3, "P3": 0},
            "by_outcome": {"REFUND": 2, "DECLINE": 1, "INVESTIGATE": 1, "INFO_ONLY": 0}},
  "auto_resolve_rate": 0.25,
  "holds": {"total": 0, "by_reason": {"customer_not_found": 0, "ambiguous_match": 0, "no_match": 0,
                                      "category_revised": 0, "self_check_failed": 0, "unknown_auth_method": 0,
                                      "llm_error": 0}},
  "self_check": {"first_draft_failed": 0, "held_self_check_failed": 0, "human_edits_refused": 1},
  "human": {"approved": 0, "rejected": 1, "edited_and_approved": 0, "acknowledged": 0, "override_rate": 1.0},
  "sla": {"as_of": "2026-09-30T16:30:00", "open": 2, "overdue": 2, "due_within_24h": 0},
  "cost_myr": {"total": "0.0000", "mean": "0.0000", "p50": "0.0000", "p95": "0.0000", "max": "0.0000"},
  "latency_ms": {"mean": 1, "p50": 1, "p95": 1, "max": 1},
  "models": {"extract": {"fake:keywords": 4}, "draft": {"fake:code-template": 4}},
  "throughput": {"decided": 4, "first_at": "2026-10-23T00:23:15", "last_at": "2026-10-23T00:23:15", "per_hour": null}
}
```

For scale, the 2,500 complaints we ran with real models give an auto-resolve rate of 0.346, a mean cost of RM0.0008 per complaint, and latency p50 3.1 s / p95 8.1 s.

| Tile | Field |
|---|---|
| Auto-resolve rate | `auto_resolve_rate` |
| Waiting for people | `sla.open`, with `sla.overdue` in red and `sla.due_within_24h` in amber |
| Self-check catches | `self_check.first_draft_failed` + `held_self_check_failed` + `human_edits_refused` |
| Override rate (how often people changed the agent's decision) | `human.override_rate`: (rejected + edited) ÷ (approved + rejected + edited) |
| Cost per complaint | `cost_myr.mean` (with `p95`), total spend `cost_myr.total` |
| Speed per complaint | `latency_ms.p50` and `p95`, shown in seconds |
| Charts (optional) | `cases.by_category`, `by_priority`, `by_route`, `holds.by_reason` |

Any rate or statistic is `null` when there's no data yet. Show "–".

## `GET /api/audit`: who did what

| Parameter | Meaning |
|---|---|
| `actor` | exact name, for example `Aina (officer)` |
| `action` | one value or a comma list: `ingest`, `agent_run`, `approve`, `reject`, `edit_approve`, `edit_approve_refused`, `acknowledge` |
| `complaint_id` | one case |
| `since`, `until` | ISO date or datetime, inclusive; a bare date in `until` means the end of that day |
| `people_only` | `true` leaves out the agent's own events |
| `limit`, `offset` | 1–1000, default 100 |

The result is newest first (example trimmed). `facets.actors` and `facets.actions` list every value in the log, for the filter drop-downs. `detail` depends on the action:
- `approve`, `reject`, `edit_approve`: `{reason, self_check}`
- `edit_approve_refused`: `{reason, problems, reply_text}`
- `acknowledge`: `{reason}`
- `agent_run`: `{route, hold_reason, error, previous_run_id}`

```json
{
  "total": 2, "limit": 100, "offset": 0,
  "facets": {"actors": ["Aina (officer)", "agent"],
             "actions": ["agent_run", "edit_approve_refused", "ingest", "reject"]},
  "items": [
    {"id": 10, "complaint_id": "CMP-00244", "actor": "Aina (officer)", "action": "edit_approve_refused",
     "run_id": "1a81b9ad90d1483982d22d9ce6c9816b",
     "detail": {"reason": "friendlier", "problems": ["amount RM999.00 is not in the evidence"],
                "reply_text": "We will refund RM999.00 for TXN-0000001."},
     "created_at": "2026-10-23T00:23:15"},
    {"id": 9, "complaint_id": "CMP-00007", "actor": "Aina (officer)", "action": "reject",
     "run_id": "41b1ed49f965431fb99ac00c33ac6fee",
     "detail": {"reason": "Transfer did fail; refund manually", "self_check": null},
     "created_at": "2026-10-23T00:23:15"}
  ]
}
```

---

## TypeScript types

```ts
export type Money = string;          // "550.00"
export type Cost = string;           // "0.0013" (RM)
export type IsoTime = string;        // "2026-07-20T22:32:00", Malaysia time, no offset

export type Queue = "processing" | "error" | "auto_resolved" | "awaiting_approval" | "with_fraud_team"
  | "approved" | "rejected";
export type Category = "DUPLICATE_CHARGE" | "FAILED_TRANSFER" | "ATM_NOT_DISPENSED" | "UNAUTHORISED_CARD"
  | "SCAM_TRANSFER" | "FEE_DISPUTE" | "SERVICE_QUALITY";
export type Outcome = "REFUND" | "DECLINE" | "INVESTIGATE" | "INFO_ONLY";
export type Route = "AUTO_RESOLVE" | "HUMAN_APPROVAL" | "FRAUD_TEAM";
export type Priority = "P1" | "P2" | "P3";
export type HoldReason = "customer_not_found" | "ambiguous_match" | "no_match" | "category_revised"
  | "self_check_failed" | "unknown_auth_method" | "llm_error";

export interface CaseListItem {
  complaint_id: string;
  customer_id: string;
  customer_name: string | null;      // null when the customer is unknown or the agent is still working
  received_at: IsoTime;
  channel: string;
  subject: string;
  status: "processing" | "done" | "error";
  queue: Queue;
  case_state: Exclude<Queue, "processing" | "error"> | null;
  sent: boolean;
  // the agent's decision; null while processing or after an error
  category: Category | null;
  outcome: Outcome | null;
  refund_amount_myr: Money | null;
  priority: Priority | null;
  route: Route | null;
  hold_reason: HoldReason | null;
  self_check: "passed" | "flagged" | null;
  vulnerable: boolean | null;
  resolve_due_at: IsoTime | null;
  waiting_reason: string | null;     // null for closed cases
  human_action: { action: string; actor: string; at: string } | null;
  updated_at: IsoTime;
}

export interface CaseList {
  total: number;
  limit: number;
  offset: number;
  counts: Record<Queue, number>;     // over all cases, ignoring filters
  items: CaseListItem[];
}

export interface Candidate { txn_id: string; score: number; reasons: string[] }

export interface LLMUsage {
  provider: string; model: string; tokens_in: number; tokens_out: number;
  cost_myr: Cost; latency_ms: number; retries: number; cached: boolean;
}

export interface AuditEvent {
  id: number;
  complaint_id: string;
  actor: string;                     // "agent" or a person's name
  action: string;
  run_id: string | null;
  detail: Record<string, unknown> | null;
  created_at: IsoTime;
}

export interface CaseDetail {
  case: {
    complaint_id: string;
    status: "processing" | "done" | "error";
    queue: Queue;
    case_state: string | null;
    sent: boolean;
    error: string | null;
    waiting_reason: string | null;
    human_action: { action: string; actor: string; reason: string; at: string; reply_text: string | null } | null;
    autonomous_run_id: string | null;
    current_run_id: string | null;
    created_at: IsoTime;
    updated_at: IsoTime;
  };
  complaint: { customer_id: string; received_at: IsoTime; channel: string; subject: string; text: string };
  // null while processing, after an error, or (customer) when the customer is unknown:
  customer: (Record<string, string> & { full_name: string; preferred_language: "EN" | "MS";
                                        accounts: Record<string, string>[] }) | null;
  clues: Record<string, unknown> | null;
  match: { status: "confident" | "ambiguous" | "none" | "not_applicable"; txn_id: string | null;
           candidates: Candidate[]; category: Category; category_revised: boolean } | null;
  decision: {
    category: Category; matched_txn_id: string | null; outcome: Outcome; refund_amount_myr: Money;
    priority: Priority; reply_language: "EN" | "MS"; route: Route; policy_route: Route; rule_id: string;
    calculation: { explanation: string; inputs: Record<string, string> };
    hold_reason: HoldReason | null; vulnerable: boolean;
    ack_due_at: IsoTime | null; resolve_due_at: IsoTime | null;
  } | null;
  evidence: {
    matched_txn: Record<string, unknown> | null;
    related_txns: Record<string, unknown>[];
    reversal: Record<string, unknown> | null;
    atm_journal: Record<string, unknown> | null;
    fee_schedule_row: Record<string, unknown> | null;
    allowed_txn_ids: string[];
    allowed_amounts: Money[];
  } | null;
  reply: { text: string; redraft_count: number;
           self_check: { passed: boolean; problems: string[]; found_txn_ids: string[]; found_amounts: Money[] } | null
         } | null;
  usage: { cost_myr: Cost; latency_ms: number; prompt_version: string; schema_version: string;
           policy_version: string; extract: LLMUsage; draft: LLMUsage[] } | null;
  runs: { run_id: string; run_kind: "autonomous" | "reprocess"; created_at: IsoTime; route: Route | null;
          outcome: Outcome | null; hold_reason: HoldReason | null; cost_myr: Cost; latency_ms: number }[];
  events: AuditEvent[];                // oldest first
  outbound: { kind: "resolution" | "holding_reply"; reply_text: string; refund_amount_myr: Money;
              authorised_by: string; status: string; created_at: IsoTime }[];
}

type Stats<T> = { mean: T | null; p50: T | null; p95: T | null; max: T | null };

export interface Metrics {
  cases: { total: number; by_queue: Record<Queue, number>; by_route: Record<Route, number>;
           by_category: Record<Category, number>; by_priority: Record<Priority, number>;
           by_outcome: Record<Outcome, number> };
  auto_resolve_rate: number | null;
  holds: { total: number; by_reason: Record<HoldReason, number> };
  self_check: { first_draft_failed: number; held_self_check_failed: number; human_edits_refused: number };
  human: { approved: number; rejected: number; edited_and_approved: number; acknowledged: number;
           override_rate: number | null };
  sla: { as_of: IsoTime; open: number; overdue: number; due_within_24h: number };
  cost_myr: { total: Cost } & Stats<Cost>;
  latency_ms: Stats<number>;
  models: { extract: Record<string, number>; draft: Record<string, number> };
  throughput: { decided: number; first_at: IsoTime | null; last_at: IsoTime | null; per_hour: number | null };
}

export interface AuditLog {
  total: number; limit: number; offset: number;
  facets: { actors: string[]; actions: string[] };
  items: AuditEvent[];               // newest first
}
```

A minimal fetch helper:

```ts
const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, { headers: { "content-type": "application/json" }, ...init });
  if (!r.ok) throw Object.assign(new Error(`${r.status}`), { status: r.status, body: await r.json() });
  return r.json();
}

// api<CaseList>("/api/cases?queue=awaiting_approval")
// api("/cases/CMP-00244/actions", { method: "POST", body: JSON.stringify({ action: "approve", actor: "Aina" }) })
```

CORS is open, so the UI can run on any address (`localhost:5173`, or a laptop on the venue Wi-Fi). Point `VITE_API_URL` at the machine running the backend. On Windows, use `http://127.0.0.1:8000` rather than `localhost` for local work: `localhost` tries IPv6 first and can add about 0.2 s to every call.

## Not there yet (bonus, later)

Login and roles (officer, fraud analyst, manager), role-filtered queues, escalate, second-tier approval, reassign, send back, the fraud investigate and record-outcome actions, live push. The read routes above won't change shape when these arrive; new fields are only added.

## Changelog

- **2026-10-23**: first version. `GET /api/cases`, `GET /api/cases/{id}`, `GET /api/metrics`, `GET /api/audit`; CORS open.
