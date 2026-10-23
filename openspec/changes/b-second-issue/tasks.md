## 1. Agree and shared files (Dev A approves)

- [x] 1.1 Agree with Dev A: this replaces the phrase-list plan; confirm the gate thresholds
- [x] 1.2 `contracts.py`: `"second_issue"` in `HoldReason`; `OtherIssue`; `AgentRun.other_issues`, `AgentRun.issues_usage` (all defaulted). `config.py` / `.env.example`: `LLM_ISSUES` (default `LLM_EXTRACT`, `off` disables). One small commit
- [x] 1.3 Test: an old stored run (without the new fields) still loads; `LLM_ISSUES=off` and `fake:*` make no call

## 2. Evaluation set first (so the prompt isn't tuned to it)

- [x] 2.1 `backend/eval/make_issues.py`: about 30 two-issue and about 30 tricky single-issue rewrites from eligible training complaints, plus Dev A's 6 mixed texts; alternate `dev` / `final`
- [x] 2.2 Generate once, read every row for label sanity, fix or drop bad rows, commit `backend/eval/issues/`
- [x] 2.3 `backend/eval/issues_eval.py`: caught / false flags / cost / p95, a flags CSV, `--split`, `--extra train|messy|test`

## 3. Detection

- [x] 3.1 `registry.py`: the `issues` step; `check_config` skips it when off
- [x] 3.2 `prompts.py`: `ISSUES_PROMPT_VERSION = "issues-v2"` (v1 + the short-trailing-issue rule, tuned on dev), the system prompt, the strict schema, `build_issues_messages`; `backend/llm/fewshot_issues.json` (about 10 fresh examples, none from the evaluation set)
- [x] 3.3 `backend/agent/issues.py`: `detect_issues(complaint)` (fail-safe, fake/off → []) and `other_issues(issues, category, text)` (category, overlap, verified quote ≥ 8 characters)
- [x] 3.4 Unit tests (offline, with a stub client):
  - the two-issue example kept
  - mention-only dropped by the prompt contract
  - an invented quote dropped
  - an overlap dropped
  - a short quote dropped
  - a provider error gives [] and no `llm_error`
  - an example-vs-evaluation-set independence check

## 4. Hold

- [x] 4.1 `pipeline.py`: `asyncio.gather(extract, detect_issues)`; after the engine, store `other_issues` and `issues_usage`, and `hold(decision, "second_issue")` before drafting
- [x] 4.2 `store.py`: `run_cost` includes `issues_usage`. `queries.py`: `HOLD_TEXT["second_issue"]`, `other_issues` in the case detail
- [x] 4.3 Tests:
  - an auto refund plus a verified issue → HUMAN_APPROVAL, scored fields unchanged, reply drafted for pending
  - INVESTIGATE stays FRAUD_TEAM
  - an earlier hold reason kept
  - no issues → the decision is identical to before
  - the API detail shows `other_issues`; the `hold_reason=second_issue` filter works

## 5. Tune on dev, then the gate

- [x] 5.1 `issues_eval --split dev` with the real model; revise the prompt or examples only against dev
- [x] 5.2 Gate:
  - `--split final` (≥ 80% caught, ≤ 1 false flag)
  - `--extra train` (≤ 1%, read each), `--extra messy` (≤ 1), `--extra test` (read each)
  - training score 99.94 unchanged on the scored fields
  - full `pytest`
- [x] 5.3 Server on a fresh API database: `api_check` (100.0, 9/9) and `--n 20` timing; post Dev A's 6 mixed complaints (the second issues held; fraud cases stay FRAUD_TEAM)
- [x] 5.4 Record everything in `docs/EXTRACTOR_RESULTS.md`, with the decisions and the reasons

## 6. Ship

- [x] 6.1 `docs/UI_API.md` (hold reason, `other_issues`, TypeScript, changelog); the PLAN.md section points here; tick in `STATUS.md`
- [x] 6.2 Regenerate `predictions.csv`; confirm only `route` / `reply_text` change, and only on flagged rows
- [x] 6.3 Optional, if time: the reply mentions the second issue (D11), with tests that unflagged requests are unchanged (cache holds)
