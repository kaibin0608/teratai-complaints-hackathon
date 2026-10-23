## Why

Dev A's decision engine is merged on `dev`, so the extractor is now the one missing piece between a complaint and a scored prediction. Matched transaction (25), outcome (25) and refund (25) all depend on the clues it produces, and category (10) and language (5) come straight from it. Until it exists, the team has no real end-to-end score. The extractor runs through OpenRouter on a RM150 budget, so the LLM layer has to cache, track cost, and let the team switch models without changing code.

## What Changes

- **LLM layer (`backend/llm/`)**: one `LLMClient` that owns caching, retries, Pydantic validation and usage/cost tracking. Thin adapters handle transport only: `openrouter` (default), `openai_compatible` (any `base_url`) and `fake`. Each step picks its model with a `provider:model` setting (`LLM_EXTRACT`, `LLM_DRAFT`). An unknown provider fails at startup.
- **Per-model JSON mode**: strict `json_schema` where the model supports it, otherwise `json_object`, otherwise the prompt alone. Pydantic validation always runs afterwards. Malformed output gets one retry, then `llm_error`.
- **Cost from the provider**: `cost_myr = usage.cost × USD_TO_MYR`, using OpenRouter's response field. There is no price table.
- **Cache**: keyed on a hash of the full request (provider, model, messages, schema, generation parameters) and stored in SQLite (`llm_cache`). A rerun after a crash or an unrelated prompt change costs nothing.
- **Extraction (`backend/agent/parser.py`, `backend/llm/prompts.py`)**: a versioned prompt that puts the complaint in a delimited data block, with `received_at` and channel as context. A schema just for the LLM sits apart from `Clues`. 8–12 hand-checked examples, none taken from the pilot or holdout IDs, in a fixed order.
  - **Date rules**: an explicit calendar date fills `date_exact` (year taken from `received_at`). The raw date words always go into `date_phrase`. Relative dates are never computed by the LLM.
- **Pipeline fallback (`backend/agent/pipeline.py`)**: if extraction fails, the pipeline uses keyword clues from `fake_extract` and holds the case with `llm_error`, which overrides any hold reason the engine set. If drafting fails, it uses the template holding reply and holds the case. Every complaint gets a prediction row, and every failure is visible.
- **Pipeline wiring**: the default `engine` and `check` become Dev A's real `match_and_decide` and self-check. The stub defaults remain only for tests.
- **Clue evaluator (`backend/eval/clue_eval.py`)**: a new check scores the date window resolved by Dev A's `resolve_date` / `resolve_fee_month`. Dev A's language rule and amount tolerance are imported, not copied. `fee_month` counts as expected only when the text names a month. A new `--engine` flag reports how often the top-ranked transaction is the labelled one.
- **Shared-files PR (needs Dev A's approval)**:
  - `requirements.txt` adds `httpx`, `python-jose` and `bcrypt`.
  - `config.py` adds `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `LLM_EXTRACT`, `LLM_DRAFT`, `LLM_TIMEOUT_S` and `LLM_CACHE_PATH`.
  - `.env.example` documents them.
- **BREAKING (config)**: `LLM_PROVIDER` / `LLM_EXTRACT_MODEL` / `LLM_DRAFT_MODEL` are replaced by `LLM_EXTRACT` / `LLM_DRAFT` in `provider:model` form. Nothing reads the old variables yet.
- **Prerequisite**: rebase `feat/b-llm-client` onto `dev`.

## Capabilities

### New Capabilities
- `llm-client`: a pluggable LLM access layer covering the provider registry, per-step model selection, JSON-mode fallback, validation and retry, the request-hash cache, and usage and cost in RM.
- `complaint-extraction`: turning complaint text into validated `Clues`, covering prompt structure, few-shot examples, date rules, treating complaint text as data, and the extraction prompt and schema versions.
- `pipeline-resilience`: what the pipeline does when an LLM step fails, so every complaint still produces a held, visible run with a prediction row.
- `clue-evaluation`: measuring extraction quality per field and through the engine against the training labels, without drafting.

### Modified Capabilities
<!-- None: openspec/specs/ is empty. -->

## Impact

- **New code**: `backend/llm/{client,registry,openrouter_adapter,openai_compatible_adapter,fake_adapter,prompts,cache}.py`, `backend/agent/parser.py`, `backend/llm/fewshot.json`.
- **Changed code**: `backend/agent/pipeline.py` (fallback, real engine and checker as defaults) and `backend/eval/clue_eval.py`. `eval/` is Dev A's folder, so tell A before the PR.
- **Shared files**: `backend/config.py`, `requirements.txt`, `.env.example`, in a separate PR that Dev A approves.
- **Dependencies**: OpenRouter API (network, key in `.env` only, spending limit set on the key), `httpx`.
- **Dev A's files are not changed.** Problems found in their code (four handlers score the counterparty against `description` instead of `merchant_or_counterparty`, and the matching tests check that the labelled transaction is among the candidates, not that it ranks first) are reported to Dev A. `--engine` will measure them.
- **Budget**: about USD 35 (RM150). Training runs skip drafting, and caching plus prompt-prefix reuse keep reruns cheap.
