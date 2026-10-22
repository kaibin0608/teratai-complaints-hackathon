## Context

The pipeline drafts with `stub_draft` (a generic "we are reviewing" sentence), and checks with Dev A's `check_reply`, which only verifies that IDs and RM amounts are in the evidence. Its refund-amount branch is a `pass`. Dev A's handlers already provide `reply_guidance` per category and fill `evidence.allowed_txn_ids` / `allowed_amounts`. For example CMP-00244 allows TXN-0088211 and 1500.00 / 950.00 / 550.00, and `decision.calculation.explanation` reads "1500.00 requested − 950.00 dispensed = 550.00 refund". `decision.resolve_due_at` comes from `sla_policy.csv` (P1 3, P2 7, P3 14 business days).

The organisers check every reply automatically: empty, wrong language, IDs or amounts outside the evidence, refund amount stated. Judges read 10.

## Goals / Non-Goals

**Goals:**
- Replies that are correct to the sen, in the right language, with route-appropriate status wording, and that pass the organisers' automatic checks.
- No reply reaches the export without passing the combined code check. A failure is held, as today.
- A model switch is one env var. Two models compared on the pilot before choosing.

**Non-Goals:**
- Human edit and approve flows (API change). This change only provides the combined check they will call.
- Changing `contracts.py`, Dev A's `check_reply` or `reply_guidance`.
- Polishing the template's prose. It is a factual safety net.

## Decisions

### D1. The complaint reaches the drafter through the pipeline, not the contract
`Drafter(result, feedback)` has no complaint. `run_pipeline` gets `draft: Drafter | None = None`. With None it uses `functools.partial(reply_generator.draft, complaint=complaint)`. Injected drafters (tests, `--no-draft`) keep the two-argument shape.

*Alternative:* add `complaint` to `Drafter` in `contracts.py`. Rejected for now: a shared-file PR for something one function needs. Revisit if Dev A wants it.

### D2. Code builds a facts block; the LLM only writes prose
`prompts.build_draft_messages(result, complaint, feedback)` renders:
```
system:  role, tone (professional, warm, concise, 80–160 words), rules: use only the facts,
         mention only the listed IDs/amounts, never promise anything not in "next step",
         greeting/sign-off format, output plain text only
user:    <facts> language, greeting name, category, outcome, route, purpose (from the D3 table),
         refund "RM550.00", transaction "TXN-0088211 on 17-07-2026, Miri Mall, RM1,500.00",
         calculation, handler guidance, next update by, allowed IDs, allowed amounts </facts>
         <complaint> subject + text </complaint>          (data, not instructions)
         [on redraft] <problems> … </problems> fix these, keep everything else
```
Amounts use one format, `RM1,234.56`. Dev A's regex reads `RM\s?[\d,]+(\.\d{1,2})?` and strips commas, so it matches. Dates use DD-MM-YYYY, the project's display format. `temperature = 0.3`. No examples in the prompt: replies vary by case and a strong instruction block is enough. A prompt version `draft-v1` is recorded on the run.

### D3. Purpose sentence by outcome and route, decided in code
`purpose(decision)` returns one of five instructions (spec table). The LLM never chooses the status wording; it phrases it. Only REFUND with AUTO_RESOLVE gets "has been refunded".

### D4. Rules check in code, one combined self-check
`reply_rules.check(reply, result) -> CheckResult` covers: empty and length, refund amount stated, premature refund claim (EN and MS phrases), language. `combined_check(reply, result)` merges Dev A's `check_reply` with it, and becomes the pipeline default. Problems are short English sentences fed back to the redraft.

Language check: count function words from two small lists. It's crude, but replies are 80–160 words, so the gap is large. Ties fail.

### D5. Deterministic code reply as the fallback
`reply_templates.render(result)` produces EN/MS text per outcome from the same facts. It replaces `stub_draft` in the pipeline's failure path, in `fake:*`, and in `--no-draft`. Tests render it for the pilot decisions and require the combined check to pass. A drafter outage then still yields a correct, checkable reply, held with `llm_error`.

### D6. Model comparison
`reply_eval.py --model` overrides `LLM_DRAFT` for one run. Candidates: `openrouter:deepseek/deepseek-v4-flash` and `openrouter:anthropic/claude-haiku-5.5`. Pick by:
1. combined-check first-draft pass rate
2. reading 10 replies per model
3. latency
4. cost

The winner goes into `.env.example`, and the choice into `docs/EXTRACTOR_RESULTS.md` (renamed section "Replies").

### D7. Found during the build: customer-safe reasons and reasoning effort
- **Reasons from code.** Dev A's `calculation.explanation` is written for staff: "Charged 12.00, due 0.00", "auth_method=3DS-OTP …", "reversed on 2026-09-04 08:55:12". Given that text, the model invented reasons ("charged in error") and quoted times. `reply_facts.reason(result)` maps each `rule_id` plus `calculation.inputs` to one customer-safe sentence (for example the 60+ debit-card waiver). The prompt gets that as REASON. A test asserts that no reason contains authentication methods, times or rule IDs.
- **Reasoning effort per step.** DeepSeek v4 Flash defaults to `reasoning.effort = high`. On drafting it spent the whole `max_tokens` on hidden reasoning and returned empty replies (4–10 of 50). `LLM_EXTRACT_REASONING` / `LLM_DRAFT_REASONING` (config.py, a shared file) send `reasoning: {effort}`. An empty value sends nothing and leaves extraction cache keys unchanged. Drafting runs with `none`.

## Risks / Trade-offs

- [The model drops the refund amount or uses another format] → the rule check catches it, the redraft fixes it, and otherwise the case is held. The facts give the amount pre-formatted.
- [Malay quality: overly literal or English-flavoured] → read MS replies in the comparison. The language rule only catches the wrong language, not awkward phrasing.
- [Dev A's handlers allow amounts the reply shouldn't use (e.g. the duplicate-listed 1500.00)] → harmless: the self-check only limits to the evidence, and the prompt lists the amounts.
- [Latency: an extra LLM call] → ~3–8 s per call. The live round allows 120 s. Batch concurrency hides it.
- [Prompt injection in complaint text asking the reply to promise a refund] → wording comes from code (D3); the rules check flags refund claims; amounts outside the evidence fail.
- [The language heuristic misjudges a short reply] → the length floor comes from the prompt (80+ words). A false failure only costs one redraft or a hold.

## Migration Plan

1. Land the code with `LLM_DRAFT=fake:template` as the default. Tests stay offline.
2. Compare the two models on the pilot. Set the chosen `LLM_DRAFT` in `.env` and `.env.example`.
3. `runner --ids test --rerun`, then `submit --ids test`. Extraction is cached; only drafting is paid.

Rollback: `LLM_DRAFT=fake:template` gives code replies.

## Decisions confirmed with Dev B (2026-10-22)

- Compare DeepSeek v4 Flash and Claude Haiku 5.5 on the pilot before choosing.
- A refund waiting for an officer says "will be credited"; only AUTO_RESOLVE says "has been refunded".
- Greet by full name; generic greeting for unknown customers.
- Next-update date only for fraud and pending (HUMAN_APPROVAL) cases.
- Held cases (ambiguous_match, no_match, customer_not_found, ...) still get a reply stating the agent's decision, worded as pending. The officer approves or edits it before anything is sent.
- Scam and unauthorised-card replies may add fixed safety advice that code supplies (EN + MS, 1–2 sentences per category). The model may use only those lines.
- Replies quote the transaction reference with its date and amount ("transaction TXN-0088211 on 17-07-2026, RM1,500.00").
