## ADDED Requirements

### Requirement: Pilot reply report
`python -m backend.eval.reply_eval [--ids pilot] [--model provider:model]` SHALL run the pipeline on the selected complaints with the given drafting model (default `LLM_DRAFT`) and report:
- combined self-check pass rate on the first draft and after the redraft
- hold rate for `self_check_failed`
- refund-stated rate on refund decisions
- language-rule pass rate
- mean reply length
- drafting cost in RM, and mean and p95 drafting latency

It SHALL write `complaint_id, outcome, route, reply_language, refund, passed, problems, reply_text` to a CSV for reading.

#### Scenario: Compare two models
- **WHEN** the report runs once with `--model openrouter:deepseek/deepseek-v4-flash` and once with `--model openrouter:anthropic/claude-haiku-5.5`
- **THEN** each prints the same metrics, and each CSV holds 50 replies for side-by-side reading

### Requirement: Extraction reused
The report SHALL reuse the configured extractor through the LLM cache, so comparing drafting models pays only for drafting.

#### Scenario: Second model run
- **WHEN** the report runs for a second drafting model on the same complaints
- **THEN** extraction usage shows cached calls only
