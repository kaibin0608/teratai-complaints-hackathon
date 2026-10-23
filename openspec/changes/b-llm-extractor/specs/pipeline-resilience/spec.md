## ADDED Requirements

### Requirement: Real engine and checker by default
`run_pipeline` SHALL default to Dev A's `match_and_decide` and self-check from `dev`. The stubs SHALL remain injectable for tests only.

#### Scenario: Default pipeline
- **WHEN** `run_pipeline(complaint, extract=extract)` is called without `engine` or `check`
- **THEN** the real engine and real self-check run

### Requirement: Extraction failure falls back and holds
When the extractor raises, the pipeline SHALL use keyword clues (`fake_extract`) and run the engine on them. It SHALL set `hold_reason = llm_error` (replacing any reason the engine set), route the case through `hold()`, and record the original error on the run. The case therefore still yields a prediction row and still waits for a human.

#### Scenario: Provider down during extraction
- **WHEN** the extractor raises after its retry
- **THEN** the run has a decision, `decision.hold_reason = "llm_error"`, `decision.route` is HUMAN_APPROVAL (or FRAUD_TEAM if the outcome is INVESTIGATE), `run.error` names the extraction failure, `run.extract_usage.provider = "fake"`, and `prediction_row()` succeeds

#### Scenario: Fallback clues produce no match
- **WHEN** extraction fails and the engine sets `hold_reason = no_match` on the keyword clues
- **THEN** the final `hold_reason` is still `llm_error`

### Requirement: Drafting failure falls back and holds
When the drafter raises, the pipeline SHALL use the template holding reply in `decision.reply_language`, run the self-check on it, and hold the case with `llm_error` (replacing any earlier reason). The run SHALL NOT crash.

#### Scenario: Provider down during drafting
- **WHEN** the drafter raises
- **THEN** `run.reply_text` is the template reply in the decision's language, `decision.hold_reason = "llm_error"`, and the run completes

### Requirement: Engine failure stays a failed run
When the engine raises, the pipeline SHALL record `run.error` and return a run with no decision. No fallback decision SHALL be invented. Batch export SHALL report the row as missing.

#### Scenario: Engine bug
- **WHEN** `match_and_decide` raises
- **THEN** `run.decision is None`, `run.error` starts with "engine failed", and the run is visibly marked failed
