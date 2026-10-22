## ADDED Requirements

### Requirement: Provider registry with per-step model selection
The system SHALL resolve each LLM step's provider and model from a `provider:model` setting (`LLM_EXTRACT`, `LLM_DRAFT`). Providers SHALL be looked up by name in a registry containing at least `openrouter`, `openai_compatible` and `fake`. Adding a provider SHALL require only a new adapter registered by name, with no change to callers.

#### Scenario: Different models per step
- **WHEN** `LLM_EXTRACT=openrouter:model-a` and `LLM_DRAFT=openrouter:model-b`
- **THEN** extraction calls are sent to `model-a`, drafting calls to `model-b`, and each call's `LLMUsage` records the provider and model actually used

#### Scenario: Unknown provider fails at startup
- **WHEN** `LLM_EXTRACT=nosuch:model-x` and the application or batch runner starts
- **THEN** startup fails with an error naming the unknown provider and listing the registered ones, before any complaint is processed

#### Scenario: Missing API key fails at startup
- **WHEN** a step uses `openrouter` and `OPENROUTER_API_KEY` is unset
- **THEN** startup fails with an error naming the missing variable

### Requirement: Structured output with JSON-mode fallback
When a call needs structured output, the client SHALL request it in the strongest mode the model supports: strict `json_schema`, then `json_object`, then prompt-only. The response SHALL always be parsed and validated against the target Pydantic model, whatever mode was used.

#### Scenario: Model supports strict schemas
- **WHEN** the configured model is marked as supporting `json_schema`
- **THEN** the request carries `response_format.type = json_schema` with `strict: true` and asks to route only to providers that support every requested parameter

#### Scenario: Model without schema support
- **WHEN** the configured model is marked `prompt` mode
- **THEN** the request carries no `response_format`, the schema is described in the prompt, and the reply is still validated with Pydantic

### Requirement: Validation retry and failure
The client SHALL retry once when the response is not valid JSON or fails validation, and when the provider returns a transient error (timeout, HTTP 429 or 5xx). The retry SHALL include the validation error. If the retry also fails, the client SHALL raise an error that the pipeline maps to `llm_error`. Retries SHALL be counted in `LLMUsage.retries`.

#### Scenario: First response invalid, second valid
- **WHEN** the first response has an unknown field and the second response is valid
- **THEN** the call returns the validated object with `retries = 1`

#### Scenario: Both responses invalid
- **WHEN** both the first response and the retry fail validation
- **THEN** the client raises an LLM error, and no partially valid object is returned

### Requirement: Request-hash cache
The client SHALL cache successful, validated responses under a hash of the full request: provider, model, messages, response format or schema, and generation parameters. A cache hit SHALL return the stored response without a network call and SHALL be marked `cached = true`, with zero cost and the original token counts. Failed or invalid responses SHALL NOT be cached. The cache SHALL survive process restarts.

#### Scenario: Rerun hits the cache
- **WHEN** the same complaint is extracted twice with an unchanged prompt and model
- **THEN** the second call makes no network request and returns `cached = true`, `cost_myr = 0`

#### Scenario: Prompt change misses the cache
- **WHEN** the few-shot examples or instructions change
- **THEN** the request hash changes and the next call goes to the provider

#### Scenario: Cache bypass
- **WHEN** the cache is disabled by configuration or a `--no-cache` flag
- **THEN** every call goes to the provider and nothing is read from the cache

### Requirement: Usage and cost tracking in RM
Every call SHALL return an `LLMUsage` with provider, model, tokens in and out, latency in milliseconds, retries, `cached`, and `cost_myr`. `cost_myr` SHALL come from the provider's reported cost (OpenRouter `usage.cost`, in USD) multiplied by `USD_TO_MYR`, summed over retries. If the provider reports no cost, `cost_myr` SHALL be 0 and the gap SHALL be logged, never estimated silently.

#### Scenario: OpenRouter reports cost
- **WHEN** a response includes `usage.cost = 0.0004` and `USD_TO_MYR = 4.20`
- **THEN** `cost_myr` is `0.00168` (kept unrounded until display)

#### Scenario: Retry cost included
- **WHEN** a call needs one retry and both attempts report a cost
- **THEN** `cost_myr` is the sum of both attempts, and the token counts are the sum of both attempts

### Requirement: Bounded concurrency and timeouts
The client SHALL cap concurrent provider requests at `LLM_MAX_CONCURRENCY`, process-wide, and SHALL apply a per-request timeout of `LLM_TIMEOUT_S`.

#### Scenario: Batch with more tasks than the limit
- **WHEN** 100 extractions are started together and `LLM_MAX_CONCURRENCY = 8`
- **THEN** no more than 8 provider requests are in flight at any moment
