## Why

Every prediction still carries the same template reply ("Thank you ... we are reviewing"). Replies are judged three ways:
- judges read 10 replies per team (part of the 25% for replies and demo)
- the organisers auto-check all of them: empty, wrong language, transaction IDs or RM amounts not in the evidence, and whether a refund reply states the refund amount
- every `GET /cases/{id}` in the live round returns `reply_text`

The template already fails the refund-amount check on every auto-resolved refund. A reply writer has to exist before the organisers' API is built.

## What Changes

- **LLM reply writer (`backend/agent/reply_generator.py`)**: drafts the customer reply in `decision.reply_language` from facts that code assembles:
  - customer name, the decision, the refund, the matched transaction, the calculation, the allowed amounts and IDs
  - the handler's reply guidance, and a "next update by" date for fraud and pending cases
  - the complaint text, as delimited data

  The model and provider come from `LLM_DRAFT`; `fake:*` uses the code template.
- **Wording rules decided with Dev B**:
  - Only an AUTO_RESOLVE refund may say the money "has been refunded". A refund waiting for an officer says it "will be credited".
  - INVESTIGATE cases get a holding reply only (no refund promise, no decision).
  - The greeting uses the customer's full name ("Dear …," / "Yang dihormati …,"), falling back to "Dear Customer," / "Tuan/Puan," when the customer is unknown.
  - Fraud and pending cases give a next-update date from the SLA due date. Resolved replies don't.
- **Reply rules in code (`backend/agent/reply_rules.py`)**, run with Dev A's evidence check as one self-check:
  - not empty, and not too long
  - a refund reply states the refund amount
  - no "refunded / telah dikreditkan" claim unless the case is an AUTO_RESOLVE refund
  - the language matches `reply_language`

  A failure feeds the one redraft, then holds the case (`self_check_failed`), as today.
- **Code-written fallback (`backend/agent/reply_templates.py`)**: when the LLM is down or `LLM_DRAFT=fake:*`, a deterministic reply in EN or MS that states the real facts (outcome, amount, transaction, next step) and passes the same rules. It replaces the generic stub template in the pipeline.
- **Pipeline**: the LLM drafter becomes the default, with the complaint passed in. `--no-draft` keeps the code template. No change to `contracts.py`.
- **Reply evaluation (`backend/eval/reply_eval.py`)**: drafts replies for the pilot and reports:
  - self-check and rule pass rates, and redraft and hold rates
  - refund-amount and language checks
  - cost and latency

  It writes the replies to a CSV to read. Used to compare DeepSeek v4 Flash with Claude Haiku 5.5 and pick the default.
- **Rerun the 750 test complaints with replies** and regenerate `submissions/<team>/predictions.csv`. Extraction comes from the cache, so only drafting is paid.

## Capabilities

### New Capabilities
- `reply-drafting`: the LLM reply writer: facts given to the model, wording rules by route and outcome, greeting, next-update date, model selection.
- `reply-rules`: code checks on any reply, LLM-drafted or human-edited, beyond the evidence check.
- `reply-fallback`: the deterministic code reply used when no LLM reply is available.
- `reply-evaluation`: measuring replies on the pilot and comparing models.

### Modified Capabilities
<!-- None archived yet. The pipeline-resilience requirement "drafting failure uses the template reply" now uses the code-written reply; captured in reply-fallback. -->

## Impact

- **New code**: `backend/agent/{reply_generator,reply_rules,reply_templates}.py`, `backend/eval/reply_eval.py`, plus tests; prompt additions in `backend/llm/prompts.py`.
- **Changed**: `backend/agent/pipeline.py` (default drafter, combined self-check, new fallback), `backend/batch/runner.py` (`--no-draft` → code template).
- **Not changed**: `contracts.py` and Dev A's files. Handler `reply_guidance` and `check_reply` are reused as they are.
- **Cost**: the pilot comparison costs ~RM0.20. Drafting the 750 test complaints costs ~RM1–3, depending on the model.
- **Latency**: adds one LLM call per complaint (plus at most one redraft). The live round allows 120 s per complaint.
