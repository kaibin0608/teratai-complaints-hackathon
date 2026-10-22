# Dev B: Platform and LLM

Dev B builds everything around Dev A's decision engine: the LLM calls, the pipeline that ties the steps together, the database, the API, and the batch run that produces `predictions.csv`. The LLM handles language (reading complaints, writing replies). Dev A's code handles money and rules.

Source of truth: [PLAN.md](PLAN.md), sections "Team Split", "Build Order" and "File Structure".

## The interfaces

Dev B implements two of the four interfaces in [`backend/contracts.py`](../backend/contracts.py) and calls the other two.

| Interface | Owner | What it does |
|---|---|---|
| `Extractor`: complaint → `(Clues, LLMUsage)` | **B** | The LLM reads the complaint and returns raw clues |
| `Engine`: complaint + clues → `EngineResult` | A | Matching and policy, in code |
| `Drafter`: result + feedback → `(reply, LLMUsage)` | **B** | The LLM writes the reply in `decision.reply_language` |
| `Checker`: reply + result → `CheckResult` | A | Checks every transaction ID and amount in the reply against the evidence |

[`backend/agent/pipeline.py`](../backend/agent/pipeline.py) runs extract → engine → draft → check → one redraft → hold. It uses the stubs in [`backend/agent/stubs.py`](../backend/agent/stubs.py) by default, so Dev B can build without waiting for Dev A.

`contracts.py`, `config.py` and `requirements.txt` are shared files. They change only in a dedicated PR that Dev A approves.

## Build order

1. **LLM interface, first adapter and extraction prompt**
   - One `LLMClient` that implements `Extractor` and `Drafter`. The provider and model for each step come from `LLM_PROVIDER`, `LLM_EXTRACT_MODEL` and `LLM_DRAFT_MODEL`. An unknown provider fails at startup.
   - The output must validate against `Clues`, which rejects unknown fields. If it fails: retry once, then fail the run with `llm_error`.
   - Put the complaint text in a delimited block so it is treated as data, not instructions. Add few-shot examples covering English, Malay, mixed language and a call-centre note. Keep date phrases as raw text; Dev A's code resolves them.
   - Cache on a hash of (complaint, provider, model, prompt_version, schema_version). Record tokens, cost in RM, latency and retries.
2. **Pipeline and DB persistence**
3. **Intake API and watched folder**
4. **Reply drafting and the redraft loop**
5. **Case, approval and fraud endpoints, and gated sending**
6. **Batch runner and export**
7. **Second LLM adapter**: run both adapters on the 50-complaint pilot and pick the default by accuracy, cost and latency.

## Milestones that involve Dev B

| When | Dev B delivers |
|---|---|
| Day 1, about 12:00 | Real extractor, pipeline and DB, giving the first end-to-end path with Dev A's ATM handler |
| **Day 1, 16:00 (Checkpoint 1)** | Runner works with `--no-draft`; 20 training complaints classified and matched |
| Day 1 evening | Full pipeline with drafting and self-check; first 750-complaint test run |
| **Day 2, 12:00 (Checkpoint 2)** | Workflow API does approval and write-back on 50 training complaints |
| After Checkpoint 2 | Help Dev A with error analysis on the weakest category; React UI split by role screen |

---

## Every file Dev B owns, and why

Files marked **done** already exist from Step 0. Everything else still needs to be built.

### 1. LLM layer: `backend/llm/`

| File | What it does | Why we need it |
|---|---|---|
| `client.py` | One `LLMClient` interface that all code calls, plus a cache and usage/cost tracking | Switching between Claude and OpenAI becomes a config change, not a code change. The cache stops 750 complaints from being paid for twice when a run is retried. The usage numbers feed the manager's cost and latency metrics. |
| `anthropic_adapter.py` | Calls Claude | The first real provider. |
| `openai_adapter.py` | Calls OpenAI | The plan says to compare two providers on the 50-complaint pilot and pick one by accuracy, cost and latency. It's also a fallback if one API goes down on demo day. |
| `prompts.py` | The extraction and drafting prompts, each with a version number | The version is part of the cache key. Changing a prompt then reruns only the affected calls, and every run records which prompt produced it, for the audit trail. |

### 2. Agent steps: `backend/agent/`

| File | What it does | Why we need it |
|---|---|---|
| `parser.py` | The LLM turns complaint text into `Clues`: category, language, amounts, merchant, date phrase, card last 4, fee type | Complaints come in English, Malay or mixed, with phrases like "lebih kurang RM1,400". Keywords can't handle that, which is why the keyword baseline only scores 31.9. Dev A's matcher (75 of the 100 points) is only as good as these clues. Category (10) and language (5) also start here. |
| `reply_generator.py` | The LLM writes the customer reply from Dev A's decision | Every prediction needs a `reply_text`. The rule is that the LLM writes the words and the code decides the facts. It must never say "refunded" when the refund still needs approval, and fraud cases get a holding reply only. |
| `pipeline.py` (**done**) | Runs extract → match and decide → draft → self-check → one redraft → hold | The single path every complaint takes, whether it comes from the batch run, the API or the live round, so there's no second version of the logic to drift. A failure becomes a visible failed run instead of a guessed answer. |

### 3. Database: `backend/db/`

| File | What it does | Why we need it |
|---|---|---|
| `schema.py` | SQLite tables: `agent_runs`, `cases`, `case_events`, `outbound_messages`, `users`, `llm_cache` | **`agent_runs` can't be changed after it's written.** It holds what the agent decided on its own, and that is what the leaderboard scores. `cases` holds what staff did later. Keeping the two apart is a hard rule. `case_events` is the audit log, which only ever gets new rows. `outbound_messages` proves that nothing went to a customer without approval. |
| `models.py` | Create, read, update and delete functions, plus queries filtered by role | Officers see only HUMAN_APPROVAL cases, analysts only FRAUD_TEAM cases, and managers see everything. That filter has to be applied in the backend, not just in the UI. |
| `seed.py` | Creates the demo users `officer1`, `fraud1` and `manager1` with their approval limits | The demo and the approval-limit tests need these accounts. |

### 4. Auth: `backend/auth/`

| File | What it does | Why we need it |
|---|---|---|
| `router.py` | `/api/auth/login` and `/api/auth/me` | Logging in and returning the user's role and approval limit. |
| `jwt.py` | Creates and verifies login tokens (JWT) | Without it the API has no way to know who is calling. |
| `dependencies.py` | `get_current_user` and `require_role`, run on every endpoint | Role checks have to be enforced by the server. Hiding a button doesn't stop an officer from calling the fraud endpoints directly. |

### 5. API: `backend/api/`, plus `backend/main.py`

| File | What it does | Why we need it |
|---|---|---|
| `main.py` | The FastAPI app | The entry point. Until the React UI exists, `/docs` is how the core gets demoed. |
| `intake.py` | `POST /api/intake`, taking one complaint or a CSV | **The live round:** judges hand over 2–3 complaints and the system has to accept them with no code changes. It also handles repeats: the same ID with the same content returns the existing case, the same ID with different content is rejected, and an unknown customer is stored and held, never dropped. |
| `watcher.py` | Watches the `inbox/` folder; a dropped CSV goes through the same intake path | A second way to feed in live-round files, and it shows the system processing complaints without anyone pressing a button. |
| `cases.py` | List and detail, plus approve, reject, edit reply, send back, escalate, flag as sensitive, second-tier approval, reassign, and the fraud actions (acknowledge, investigate, record outcome) | This is the bonus platform: two-tier approval, where an approval over the officer's limit escalates to the manager. Editing a reply re-runs the self-check and clears any earlier approval. |
| `outbound.py` | One gated function that "sends" a reply (simulated) | Every send passes through one check: the right role, approved (and approved again by the manager if escalated), the current reply passed the self-check, and not already sent. That last check is what makes double clicks and retries safe. |
| `audit.py` | Queries over the audit log | The manager's audit view, and proof of who did what. |
| `metrics.py` | Throughput, auto-resolve rate, SLA, override rate, self-check catches, cost and latency per complaint | The manager console tiles, and demo evidence that the system works and what it costs. |
| `export.py` | `GET /api/export/predictions`, which writes `predictions.csv` and validates it | Exports from the agent's own runs only, never from staff edits. |
| `chat.py` | *Bonus:* a read-only chatbot that explains a case | Extra bonus points. Only after the core works. |
| `websocket.py` | *Bonus:* pushes new cases to open screens live | Extra bonus points. Polling still works if the connection drops. |

### 6. Batch: `backend/batch/`

| File | What it does | Why we need it |
|---|---|---|
| `runner.py` | Processes all complaints in parallel with a concurrency limit (`--no-draft` for Checkpoint 1) | 750 test complaints with several LLM calls each would take hours one at a time. The concurrency limit keeps us under the providers' rate limits. |
| `submit.py` | Generates the final `submissions/<team>/predictions.csv` | **This file is the submission.** It's checked for exactly 750 unique IDs, valid category/outcome/route values, two-decimal amounts and no empty replies. Missing or failed rows are reported, never filled with made-up answers. |

### 7. Tests: `backend/tests/`

| Test | Why |
|---|---|
| Approving over the limit is blocked | Two-tier approval must not be bypassable. |
| Sending without approval is blocked | Nothing reaches a customer unapproved. |
| Editing a reply clears the approval | Otherwise someone could approve a reply and then change it. |
| Repeat intake | The live round may resend the same complaint. |
| Double click on send | The customer must not get the same reply twice. |
| Export validation | A malformed CSV scores zero. |

### 8. Frontend: `frontend/` (after Checkpoint 2, shared with Dev A)

Not Dev B's alone. After Checkpoint 2, both developers build the React UI, split by role screen: login, Officer Desk, Fraud Workbench, Manager Console and the intake form. The intake form matters most, because the judges use it in the live round.

---

## In short

The decision engine scores points only if Dev B's work gets clean clues into it and a valid `predictions.csv` out of it. Dev B's parser drives category and language, gives Dev A's matcher its inputs, and writes the reply text. The API, DB and auth layers are what earn the bonus points and keep the live round from breaking.
