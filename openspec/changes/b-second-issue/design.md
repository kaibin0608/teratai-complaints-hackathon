## Context

- **The pipeline today** (`backend/agent/pipeline.py`, Dev B): extract (one LLM call, cached) → engine (Dev A, code) → draft (LLM) → self-check → holds. `router.hold()` only pushes toward humans and keeps an earlier hold reason.
- **The extraction prompt** is `extract-v2`. Its cache key is a hash of the full request, so changing that prompt would re-extract all 2,500 complaints.
- **What Dev A found** (PLAN.md "Complaints with two issues"): 6 mixed tests, every main issue right, 2 of them auto-resolved with the second issue dropped. Dev A proposed a phrase list. On 6 realistic single-issue sentences it wrongly flagged 5 ("kena caj 2 kali", "kad ATM", "used my card twice", "the fee was taken twice", a transfer "kat atm"). It flagged 0 on our data only because our generator writes cleanly.

## Goals / Non-Goals

**Goals:**
- Catch a second, different problem in any wording.
- Rarely flag a single-issue complaint: false flags are what judges would see.
- No change to scored fields, the extraction cache or latency.
- An easy kill switch.

**Non-Goals:**
- Handling the second issue automatically (no second decision or refund).
- Two issues in the same category (two ATM withdrawals).
- Changing the extraction prompt or the `Clues` model.

## Decisions

### D1. A separate LLM call, run in parallel with extraction
`detect_issues(complaint)` gets its own small prompt and schema, and runs with `asyncio.gather(extract(c), detect_issues(c))`. It shares the client, retry, cache and cost tracking.

*Alternatives considered:*
- An `other_issues` field in the extraction schema: that resets the extraction cache and risks shifting the main category, amount or date (Dev A's reason to defer it).
- Dev A's phrase list: it can't tell mentioning something from complaining about it.

### D2. The LLM lists every issue; code picks the "other" ones
The prompt doesn't get the engine's decision. It lists **all** issues it sees, so it never has to guess which one is "main". Code compares against `decision.category`, the final category after any revision, drops natural overlaps (the same table as Dev A's plan), and verifies each quote.

This keeps "LLM does language, code does rules": the LLM notices topics, and code decides whether to hold.

### D3. Quotes are verified against the text
Both the quote and the complaint (subject plus body) are lower-cased and whitespace-collapsed. The quote must be a substring of the complaint and at least 8 characters long. An invented issue fails this and is dropped. The 8-character floor stops one-word quotes like "fee".

### D4. The hold is applied in the pipeline, before drafting
`run.decision = hold(run.decision, "second_issue")` comes right after the engine and before the first draft. The reply facts then follow the held route ("will be credited after review"), and the self-check and redraft run as usual.

Dev A's `router.py` isn't touched; `hold()` is reused as it is. The order versus the other holds:
- the engine's own holds come first
- `self_check_failed` and `llm_error` are applied later
- `hold()` keeps the first reason; `hold_llm_error` replaces it, as today

### D5. Failure means "no second issue"
Any exception, timeout or invalid output after the client's one retry gives an empty list, and the error is noted with `note_error`. It doesn't set `llm_failed`, so no `llm_error` hold: the check is an extra safeguard, not part of the decision. The same applies to `fake:*` providers (no call) and `LLM_ISSUES=off`.

### D6. Model and settings
- The `issues` step in `registry.STEPS`: `(config.LLM_ISSUES, "json_schema")`, with reasoning from `LLM_EXTRACT_REASONING`.
- `config.LLM_ISSUES` is read raw; empty means "follow `LLM_EXTRACT`", resolved at call time by the registry. By default it uses the same DeepSeek model, with no new key. Resolving at call time also means anything that switches extraction to `fake:*` (the test fixture) switches this step too, so tests never make paid calls.
- `max_tokens` 300; temperature 0.

`check_config` validates it unless it's `off`.

### D7. Contracts (shared, Dev A approves; one small commit)
- `HoldReason` += `"second_issue"`
- `class OtherIssue(BaseModel): category: Category; quote: str`
- `AgentRun.other_issues: list[OtherIssue] = []` and `AgentRun.issues_usage: LLMUsage | None = None`

These are additive with defaults, so stored runs load unchanged. `run_cost` adds `issues_usage`.

### D8. Prompt (`issues-v1`)
- **The system prompt:**
  - defines an issue as a separate problem the customer wants fixed or answered
  - lists what is not an issue: background, the story, consequences, how they contacted us, a word that merely names another product ("kad ATM" = debit card, "caj" = charged)
  - gives each category one line
  - says to quote the customer's exact words
- **About 10 few-shot examples** in `backend/llm/fewshot_issues.json`. They're written fresh, not taken from the evaluation set: 6 tricky single-issue ones and 4 real two-issue ones, mixing EN, MS, SMS style and call-centre notes.
- **The complaint is delimited as data**, as in extraction.

### D9. Evaluation set and splits
`make_issues.py` (using Haiku, like `make_messy.py`) takes labelled training complaints (never pilot, holdout, extraction few-shots or messy sources) and produces:
- **(a) two-issue rewrites:** the original issue plus a second issue sentence of a stated other category, in a random messy style
- **(b) tricky single-issue rewrites:** the original issue reworded to contain another category's words without raising it

Dev A's 6 mixed texts are added as two-issue rows. The IDs alternate `dev` / `final`. The set is generated once, read by a human for label sanity, and committed. `issues_eval.py` computes the report from the labels' main category (no engine needed), so it's fast and cache-friendly. An end-to-end check posts Dev A's 6 to the running API.

### D10. UI and docs
- `HOLD_TEXT["second_issue"] = "Complaint raises a second issue"`
- `case_detail` adds `other_issues`
- `UI_API.md`: the new hold reason in the table and the TypeScript `HoldReason`, the `other_issues` field, and a changelog line
- PLAN.md's section points to this change and marks the phrase list as replaced

### D11. Optional: the reply mentions the second issue
If time is left after the gate is green, `build_draft_messages` gets one extra fact for held-for-second-issue cases: "ALSO RAISED: <category in plain words>. Say in one sentence it has been passed to the team concerned; promise nothing." `reply_templates.render` adds the same sentence in EN/MS. Only flagged complaints change their draft request, so the cache holds for the rest.

## Risks / Trade-offs

- [False flags in the human gate look like mistakes] → The tricky single-issue half of the set, the ≤ 1 false-flag gate on the final split, ≤ 1% on training, and every test flag read.
- [Missed second issues] → They behave exactly as today, and the demo answer covers it.
- [Latency in the hidden test: 20 complaints × 2 calls share 8 slots] → The issues call is small (≤ 300 tokens). Measure with `api_check --n 20`. If the p95 grows beyond comfort, raise the gate's concurrency for this step or set `LLM_ISSUES=off`.
- [DeepSeek's default reasoning uses up the token budget] → The client's retry triples `max_tokens`, as for extraction. If it still happens, set reasoning low for this step (an env var) after measuring.
- [Generated evaluation set mislabelled] → A human reads it before freezing; only the `final` half counts for the gate.
- [Late merge risk before the freeze] → Time-box: not green by 14:00 on Day 2 means not merged. `LLM_ISSUES=off` gives an instant rollback without a deploy.

## Migration Plan

Additive contract fields and a new config default. Deploy: merge, restart. Rollback: `LLM_ISSUES=off` and restart, or revert the merge. Regenerate `predictions.csv` after merging; only `route` and `reply_text` can change, and only on flagged rows.

## Decisions confirmed (Dev B, 2026-10-23)

- Dev A agreed that this replaces the phrase-list plan, including the shared `contracts.py` and `config.py` lines.
- The gate thresholds stand as proposed: final split ≥ 80% caught and ≤ 1 false flag; training ≤ 1% flagged (each read); messy ≤ 1.
- D11 (the reply mentions the second issue) is wanted, if time allows after the gate is green.
