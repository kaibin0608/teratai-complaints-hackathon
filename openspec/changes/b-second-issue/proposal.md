## Why

The extractor gives each complaint one category, so a second problem in the same message is silently dropped. When the main issue auto-resolves, nobody ever reads the second one. Dev A's tests (PLAN.md "Complaints with two issues") found 2 of 6 mixed complaints like that, for example a failed transfer refunded automatically while "pastu ada caj fee pulak" went unanswered. A judge could test this live.

Dev A proposed a fixed phrase list. It flags 0 of our 2,500 complaints, but our data is written cleanly. On 6 ordinary single-issue sentences in real customer style, it wrongly flagged 5:
- "kena **caj** 2 kali" (duplicate)
- "caj tahunan **kad ATM**" (fee)
- "card used **twice**, not me" (unauthorised)

A word list can't tell **mentioning** something from **complaining** about it. That's a language job, and in our design language belongs to the LLM, while code keeps the decision.

## What Changes

- **A separate LLM "issues" check** (`backend/agent/issues.py`, prompt `issues-v1`).
  - One small call per complaint lists every distinct problem the customer wants the bank to fix, each with its category and a word-for-word quote.
  - It runs **at the same time as extraction**, so it adds no waiting time.
  - The extraction prompt doesn't change, so its cache stays valid and no scored field can shift.
- **Code decides.** The pipeline keeps only issues whose category differs from the decision's category, that aren't a natural overlap (a scam story mentioning a failed transfer), and whose quote really appears in the complaint (subject or body). If any remain, it calls `hold(decision, "second_issue")`.
  - The case goes to an officer (FRAUD_TEAM stays FRAUD_TEAM).
  - Category, transaction, outcome, refund, priority and language are unchanged.
  - The reply is drafted for a pending case, because the hold happens before drafting.
- **Fails safe.** If the issues call fails, times out or returns something invalid, it counts as no second issue and the case behaves exactly as today. `fake:*` providers skip the call, so tests and fresh clones stay offline.
- **Visible to the officer.** The run stores the verified other issues with their quotes. The case detail shows them, and the queue reason reads "Complaint raises a second issue".
- **Kill switch.** `LLM_ISSUES` (default: the extraction model; `off` disables) lets the check be turned off on Day 2 without a code change.
- **Measured on data it wasn't built from.** A frozen evaluation set (`backend/eval/issues/`) holds about 30 two-issue complaints with known pairs (Dev A's 6 included) and about 30 tricky single-issue ones. It's split into a **dev** half, for tuning the prompt, and a **final** half that's only checked. It's also run on all 1,750 training complaints, the 42 messy ones and the 750 test complaints, where every flag is read.
- **Optional, if time is left:** the reply mentions the second issue in one sentence ("your concern about the fee has been passed to the team concerned").
- **Replaces** Dev A's proposed `second_issue.py` phrase list and its `router.py` call. Dev A agreed to the goal; this changes the method.

## Capabilities

### New Capabilities
- `second-issue-detection`: the LLM issues check: prompt, schema, quote verification, failure handling, kill switch.
- `second-issue-hold`: how a verified second issue holds the case, what's stored and shown, and what never changes.
- `second-issue-evaluation`: the frozen evaluation set, the dev/final split, and the merge gate.

### Modified Capabilities
<!-- None archived. The b-ops-read-api waiting reasons and hold texts gain one value additively. -->

## Impact

- **New code:**
  - `backend/agent/issues.py`
  - the prompt and schema in `backend/llm/prompts.py`
  - `backend/llm/fewshot_issues.json`
  - `backend/eval/issues_eval.py`, plus a generator, `backend/eval/make_issues.py`
  - tests
- **Changed:**
  - `backend/agent/pipeline.py`: run the check next to extraction, then hold
  - `backend/llm/registry.py`: the `issues` step
  - `backend/db/store.py`: the issues cost is included in the run cost
  - `backend/db/queries.py`: hold text, and issues in the detail
  - `docs/UI_API.md`
  - PLAN.md: the "Complaints with two issues" section now points here
- **Shared (Dev A approves):**
  - `contracts.py`: `"second_issue"` in `HoldReason`; `OtherIssue`; `AgentRun.other_issues` and `issues_usage`, both optional, so old runs still load
  - `config.py`: `LLM_ISSUES`
  - `.env.example`
- **Not changed:** the extraction prompt and its cache, Dev A's engine and router, and the scored fields. `predictions.csv` changes only in `route` and `reply_text` for flagged test complaints.
- **Cost:** about RM0.0005 per complaint; about RM1–2 to evaluate on all 2,500 once. **Latency:** the check runs in parallel with extraction, but uses the same concurrency gate (8), so 20 complaints at once queue slightly more. This is measured with `api_check --n 20`.
