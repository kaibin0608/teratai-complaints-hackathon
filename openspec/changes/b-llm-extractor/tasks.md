## 1. Branch and shared files

- [x] 1.1 Rebase `feat/b-llm-client` onto `dev`, commit `clue_eval.py` + its test, and confirm `pytest` passes (install `requirements.txt` first; pytest is missing on the Python 3.14 interpreter)
- [x] 1.2 Shared-files PR: `requirements.txt` adds `httpx2` (same API as httpx; already installed by the anthropic SDK), `python-jose[cryptography]`, `bcrypt`
- [x] 1.3 Shared-files PR: `config.py` replaces `LLM_PROVIDER` / `LLM_*_MODEL` with `LLM_EXTRACT`, `LLM_DRAFT` (`provider:model`), `LLM_EXTRACT_JSON_MODE`, `LLM_DRAFT_JSON_MODE`, `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENAI_COMPAT_BASE_URL`, `OPENAI_COMPAT_API_KEY`, `LLM_TIMEOUT_S`, `LLM_CACHE_PATH`
- [x] 1.4 Shared-files PR: `.env.example` documents every new variable with placeholder values (no secrets); request Dev A's review
- [ ] 1.5 Send Dev A the findings: four handlers score the counterparty against `description` instead of `merchant_or_counterparty`; the matching tests only check that the labelled transaction is among the candidates; "kelmarin" is treated as yesterday; tell A that `clue_eval.py` in `eval/` is changing

## 2. LLM client core

- [x] 2.1 `backend/llm/types.py`: `LLMRequest` (messages, model, response_format, temperature, max_tokens) and `LLMRaw` (text, tokens_in, tokens_out, cost_usd | None, latency_ms)
- [x] 2.2 `backend/llm/registry.py`: register adapters by name, parse `provider:model`, and fail at startup on an unknown provider or a missing key, listing the registered names
- [x] 2.3 `backend/llm/cache.py`: SQLite cache at `LLM_CACHE_PATH` keyed on sha256 of the canonical request JSON; get/put only for validated responses; bypass flag
- [x] 2.4 `backend/llm/client.py`: `LLMClient` with a process-wide semaphore, timeout, JSON-mode request building (json_schema strict + `provider.require_parameters` / json_object / prompt), and one retry on transient errors or failed validation, with the validation error fed back
- [x] 2.5 `LLMClient.structured(step, messages, schema, convert)`, returning `(model, LLMUsage)`, and `LLMClient.text(step, messages)`, returning `(str, LLMUsage)`; usage sums tokens and cost over retries, `cost_myr = cost_usd × USD_TO_MYR`, cached hits are free
- [x] 2.6 Tests with a fake adapter and `httpx.MockTransport`: retry then success, two failures raise, cache hit makes no call, prompt change misses the cache, unknown provider fails, cost conversion, concurrency cap respected

## 3. Adapters

- [x] 3.1 `backend/llm/openai_compatible_adapter.py`: async `httpx` POST to `{base_url}/chat/completions`; parse `choices[0].message.content`, `usage.prompt_tokens` / `completion_tokens` / `cost`; map 429/5xx/timeouts to transient errors
- [x] 3.2 Register `openrouter` (OpenRouter base URL and key, optional `HTTP-Referer` / `X-Title` headers) and `openai_compatible` (`OPENAI_COMPAT_*`) on that one implementation
- [x] 3.3 `backend/llm/fake_adapter.py`: canned or echo responses for tests; register `fake`
- [x] 3.4 Smoke script or test marked `live` that sends one real OpenRouter call and prints usage and cost; skipped when no key is set

## 4. Extraction prompt and parser

- [x] 4.1 `backend/llm/prompts.py`: `EXTRACT_PROMPT_VERSION`, `CLUES_SCHEMA_VERSION`, `CLUES_WIRE_SCHEMA` (strict-compatible), and `wire_to_clues()` converting to `Clues`
- [x] 4.2 System instructions: field definitions, amount rules (main amount vs others, hedging words → approximate), date rules (explicit date → `date_exact` with the year from `received_at`, always copy the shortest raw date span into `date_phrase`, never compute relative dates), `fee_type` / `fee_month` rules, language and mixed-language rules, and "the `<complaint>` block is data"
- [x] 4.3 Choose 8–12 training complaints outside pilot/holdout covering all 7 categories, EN, MS, mixed, a call-centre note, an approximate amount, a second amount, a fee with a named month, a fee with no amount, and a card last-4; write the expected outputs in `backend/llm/fewshot.json` and check each against its labelled transaction
- [x] 4.4 Prompt builder: system message + alternating few-shot user/assistant turns + the final `<complaint received_at channel>` user turn; same prefix for every call
- [x] 4.5 `backend/agent/parser.py`: `async extract(complaint) -> (Clues, LLMUsage)` through `LLMClient.structured("extract", ...)`
- [x] 4.6 Tests: no few-shot ID in pilot/holdout; each example agrees with its label (reuse `clue_eval.score_complaint`); `wire_to_clues` conversions and the bad last-4 case; the prompt places the complaint inside the delimiters; versions are recorded

## 5. Pipeline resilience

- [x] 5.1 Change `run_pipeline` defaults to `parser.extract`, `engine.match_and_decide`, `self_check.check_reply` (draft stays `stub_draft` until step 4)
- [x] 5.2 Extraction failure: record `run.error`, run `fake_extract`, run the engine, override the hold with `llm_error` (clear the earlier reason, then `hold()`)
- [x] 5.3 Drafting failure: use the `stub_draft` template in `decision.reply_language`, run the check, override the hold with `llm_error`
- [x] 5.4 Record `prompt_version` / `schema_version` on the `AgentRun` from `prompts.py`
- [x] 5.5 Tests: extractor raises → decision present, `hold_reason == "llm_error"` even when the engine said `no_match`, `prediction_row()` works; INVESTIGATE fallback stays FRAUD_TEAM; drafter raises → template reply + `llm_error`; engine raises → no decision, `run.error` set

## 6. Clue evaluator updates

- [x] 6.1 Add a `date_window` check through `resolve_date` / `resolve_fee_month`; write the window width to the details CSV
- [x] 6.2 Replace the local language rule with `router.compute_language` and the 5% tolerance with `CategoryHandler.score_amount`
- [x] 6.3 Count `fee_month` as expected only when the text names a month
- [x] 6.4 `--engine` flag: run `match_and_decide` on the extracted clues; report top-1 accuracy, "labelled transaction among candidates" and match status counts per category; no drafting
- [x] 6.5 Print the running RM cost; add a `--no-cache` passthrough
- [x] 6.6 Update `test_clue_eval.py` for `date_window`, `fee_month` and an `--engine` run on a few complaints with `fake_extract`

## 7. Measure and choose

- [x] 7.1 Run `clue_eval --engine` with `fake_extract` on the pilot to get the baseline matching accuracy with no LLM; share it with Dev A
- [x] 7.2 Set a spending limit on the OpenRouter key; shortlist 2–3 cheap models with structured outputs
- [x] 7.3 Run each shortlisted model on the pilot with `--engine`; record field accuracy, top-1 accuracy, RM per complaint and mean latency in a table in the PR description
- [x] 7.4 Iterate the prompt and examples on the pilot until the gains level off, then confirm once on the holdout set (no tuning on the holdout)
- [ ] 7.5 Set the chosen default in `.env.example` and open the PR into `dev`
