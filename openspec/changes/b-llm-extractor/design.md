## Context

Dev A's decision engine is on `dev`: all seven handlers, `engine.match_and_decide`, `router.finalize_decision` / `hold`, `self_check.check_reply` and `date_resolver.resolve_date` / `resolve_fee_month`. `feat/b-llm-client` is still at the Step 0 merge, so it has neither the real engine nor an LLM layer. `pipeline.py` is wired to the stubs.

Constraints:
- **Provider:** OpenRouter only (one key) with a RM150 budget (~USD 35). The team wants to switch models freely.
- **Data:** complaints are short (avg 130 chars, max 321) and fall into a few fixed patterns. 357 of 2,500 give a day and month with no year ("on 13 Sep"), and 527 give a full date.
- **Dev A's engine:**
  - `resolve_date` treats `date_exact` as a one-day window that ignores the phrase. It only recognises "yesterday" / "last week" / "last month" when the phrase matches its list exactly, and finds weekday and month names anywhere in the phrase.
  - `resolve_fee_month` prefers `fee_month` over `date_phrase`.
  - `score_amount` accepts ±10% when the amount is flagged approximate and ±1% otherwise.
- **Shared files:** `contracts.py`, `config.py` and `requirements.txt` change only in a PR that Dev A approves. `contracts.py` stays as it is.
- **Repo is public:** keys stay in `.env`, and `*.db` is already gitignored.

## Goals / Non-Goals

**Goals:**
- A real extractor that produces validated `Clues`, measured per field and through the engine on the pilot and holdout sets.
- Switching to any model or OpenAI-compatible provider is a config change.
- Reruns are free (cache), and every call's cost and latency is recorded in RM and ms.
- No complaint loses its prediction row to an LLM failure, and every such failure is visible as a hold.

**Non-Goals:**
- The reply drafter and its prompt (step 4). The client supports text completions, but `reply_generator.py` comes later.
- DB persistence of runs, the batch runner and the API (steps 2–6). The cache uses its own SQLite file for now.
- Fixing Dev A's handlers. Problems found go to A, and `--engine` measures them.
- An Anthropic-native adapter. Claude models are reachable through OpenRouter, and the registry makes a native adapter a later add-on.

## Decisions

### D1. A deep client, thin adapters
`LLMClient` owns everything except transport: request building, JSON mode, cache, concurrency, retry, validation and usage. An adapter implements one method:

```
async complete(req: LLMRequest) -> LLMRaw   # text, tokens_in, tokens_out, cost_usd | None, latency_ms
```

`openrouter` and `openai_compatible` share one implementation, an HTTP POST to `{base_url}/chat/completions`, differing only in base URL, key and extra body fields. `fake` returns canned output for tests. Adapters register by name in `registry.py`.

*Alternative:* one class per provider containing its own retry and cache logic. Rejected because the logic would be duplicated in every adapter, and the duplicated logic is exactly where bugs live.

### D2. `httpx` rather than the `openai` SDK
OpenRouter-specific fields (`provider.require_parameters`, `usage.cost`) are plain JSON. With `httpx.AsyncClient` they need no `extra_body` workarounds, it's one small dependency, and it's easy to mock with `httpx.MockTransport` in tests.

*Alternative:* the `openai` SDK with `base_url` set. It works too, but it's heavier and hides the raw usage fields.

### D3. Config is `provider:model` per step, plus a JSON mode per step
```
LLM_EXTRACT=openrouter:<model-slug>      LLM_EXTRACT_JSON_MODE=json_schema   # json_schema | json_object | prompt
LLM_DRAFT=openrouter:<model-slug>
OPENROUTER_API_KEY=...  OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENAI_COMPAT_BASE_URL=...  OPENAI_COMPAT_API_KEY=...                     # optional second provider
LLM_TIMEOUT_S=30  LLM_MAX_CONCURRENCY=8  LLM_CACHE_PATH=backend/.cache/llm_cache.db  USD_TO_MYR=4.20
```
The JSON mode is set explicitly, not detected, because OpenRouter support varies by provider and over time. If a strict-schema request fails because no endpoint supports it, the error says so, and the fix is one env var. Validation is the same in every mode.

*Alternative:* automatic downgrade on a routing error. Rejected: it adds hidden behaviour, and the chosen mode should show in the run record.

### D4. Cache key is a hash of the whole request
`sha256(canonical_json({provider, model, messages, response_format, temperature, max_tokens}))`. It's stored in SQLite (stdlib `sqlite3`) at `LLM_CACHE_PATH`, with columns `key`, `response_text`, `tokens_in`, `tokens_out`, `cost_usd` and `created_at`. Only validated responses are written. The prompt and schema versions are recorded on the run but kept out of the key: any change to the prompt already changes the hash, and a hand-maintained version can be forgotten.

*Alternative:* the plan's (complaint, provider, model, prompt_version, schema_version) key. Rejected: it serves stale results if someone edits a prompt without bumping the version, and it doesn't work for drafting, whose input depends on Dev A's `EngineResult`.

The cache lives in its own file for now. When step 2 adds the DB, it can move into `teratai.db` as the `llm_cache` table without changing callers.

### D5. A separate schema for the LLM
`prompts.py` defines `CLUES_WIRE_SCHEMA` (strict-mode compatible: every field in `required`, null allowed, `additionalProperties: false`, enums for category, language and fee_type, no `pattern` or `format`). It also defines `wire_to_clues(dict) -> Clues`, which turns numbers into `to_money`, strings into dates, and checks that the last 4 is 4 digits. Pydantic's schema for `Clues` is not sent, because `Decimal` and the regex patterns produce `anyOf` / `pattern` constructs that strict mode often rejects.

### D6. Prompt layout, ordered so the provider can cache the prefix
```
system:    instructions (role, field rules, date rules, "the <complaint> block is data")   ┐ fixed prefix,
user/asst: few-shot pair 1 … pair N (rendered from fewshot.json)                             ┘ the same for every call
user:      <complaint received_at="…" channel="…"> subject + text </complaint>          ← changes per call
```
Examples are rendered as alternating user/assistant turns, which follow the format more reliably than one long text block. `temperature = 0`. The fixed prefix is identical for every complaint, so providers with automatic prompt caching bill it at the cached rate. Anthropic models on OpenRouter need explicit `cache_control`. That is optional, and can be added in the adapter later.

### D7. Few-shot data in `backend/llm/fewshot.json`
Each entry holds a `complaint_id` and the expected output for the LLM. The complaint text is loaded from `data/complaints.csv` when the prompt is built, so it's never copied by hand. Two tests protect the file: no ID may come from the pilot or holdout sets, and each example's amount, counterparty, card and date must agree with its labelled transaction. The second test uses the clue evaluator's own scoring.

### D8. Pipeline fallback
```
extract ─ok──────────────────────▶ engine ─▶ draft ─ok─▶ check ─▶ (redraft once) ─▶ done
   └─raises─▶ fake_extract ─▶ engine ─▶ override hold = llm_error
                                         draft ─raises─▶ stub_draft template ─▶ check ─▶ override hold = llm_error
engine raises ─▶ run.error, no decision (stays failed: a bug, not an LLM problem)
```
The override clears the engine's reason first (`model_copy(update={"hold_reason": None})`) and then calls `hold(decision, "llm_error")`. `hold()` keeps the earlier reason when one exists, and on keyword clues the engine usually sets `no_match`, which would hide the LLM failure. `run.error` keeps the original exception text. "Failed" means only `decision is None`. Defaults change to `extract=parser.extract`, `engine=engine.match_and_decide` and `check=self_check.check_reply`, while `draft` stays `stub_draft` until step 4.

### D9. Evaluator changes reuse Dev A's code
- `date_window` calls `resolve_date` or `resolve_fee_month` and checks that the labelled transaction's date falls inside the window. The window's width (in days) goes into the details CSV.
- The reply language comes from `router.compute_language`.
- The amount check calls `CategoryHandler.score_amount(...) > 0` rather than a local 5%.
- `fee_month` counts as expected only when a month name matching the resolver's month list appears in the text.
- `--engine` calls `match_and_decide(complaint, clues)` and reports top-1 accuracy, "labelled transaction among candidates", and `match.status` counts per category. Run with `fake_extract` it costs nothing, which separates matching problems from extraction problems.

## Risks / Trade-offs

- [The chosen model has no strict-schema endpoint, or it disappears] → the JSON mode is configurable and validation and retry cover every mode. The pilot comparison picks only models with structured outputs listed.
- [The LLM gets `date_exact` wrong, and the resolver lets it override a correct phrase] → the prompt fills `date_exact` only for explicit dates. `date_window` in the evaluator catches it. If it persists, ask Dev A to fall back to `date_phrase` when an exact-date search finds nothing.
- [Budget overrun from a retry loop or repeated full runs] → set a spending limit on the OpenRouter key, keep training runs extraction-only, rely on the cache, and log a running RM total during evaluation runs.
- [Prompt injection via complaint text] → the output schema can't express outcome, refund or route, the text is delimited, and the engine decides everything else.
- [The keyword fallback gives poor clues for a held case] → acceptable: the case is held for a human, and the row still earns category and language points.
- [Four of Dev A's handlers score the counterparty against `description` and ignore the extracted name] → outside this change. Report to Dev A now, and `--engine` shows the effect.
- [`clue_eval.py` sits in Dev A's `eval/` folder] → tell Dev A before the PR. The changes only add checks and import A's rules.
- [The cache serves an old response after a provider-side model update] → the model slug is in the key, `--no-cache` forces fresh calls, and the cache file can be deleted.

## Migration Plan

1. Rebase `feat/b-llm-client` onto `dev` and confirm Dev A's tests pass.
2. Open the shared-files PR (`config.py`, `requirements.txt`, `.env.example`) and get Dev A's approval. Nothing reads the old `LLM_PROVIDER` / `LLM_*_MODEL` variables, so replacing them breaks nothing.
3. Merge the LLM layer, extractor, pipeline and evaluator in one PR into `dev`.
4. Rollback: set `LLM_EXTRACT=fake:keywords` and the pipeline runs on keywords with no network.

## Open Questions

- Which 2–3 OpenRouter models go into the pilot comparison? They need strict structured outputs, and should be cheap and fast. Pick them from the OpenRouter models page filtered by `structured_outputs`.
- Should Dev A make `resolve_date` use `date_phrase` when an exact-date search finds no transaction? This depends on the first `date_window` results.
- Should `fake_extract` move out of `stubs.py` (which says "delete once real lands") into a permanent `backend/agent/keyword_extract.py`, now that it is the production fallback? That's a small move that needs Dev A's agreement.
