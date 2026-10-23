## ADDED Requirements

### Requirement: Code-written reply
`reply_templates.render(result)` SHALL produce a reply in `decision.reply_language` (EN and MS texts) from the decision and evidence only, following the same greeting and wording rules as the LLM writer:
- AUTO_RESOLVE refund: refunded RMx for TXN
- pending refund: RMx will be credited after review
- decline: the calculation explanation
- investigate: holding reply with the next-update date
- info only: apology and feedback recorded

It SHALL pass the combined self-check for every decision the engine produces.

#### Scenario: Auto-resolved refund
- **WHEN** CMP-00001 (REFUND RM46.54, AUTO_RESOLVE) is rendered
- **THEN** the reply mentions RM46.54 and its transaction ID, says it has been refunded, and passes the combined check

#### Scenario: Every pilot decision passes
- **WHEN** the code reply is rendered for each of the 50 pilot decisions
- **THEN** all 50 pass the combined self-check

### Requirement: Used whenever no LLM reply exists
The pipeline SHALL use the code-written reply when the drafter raises (still holding with `llm_error`), when `LLM_DRAFT` is `fake:*`, and when the runner is given `--no-draft`.

#### Scenario: Drafter outage
- **WHEN** the LLM drafter raises
- **THEN** the run's reply is the code-written reply and `hold_reason = llm_error`
