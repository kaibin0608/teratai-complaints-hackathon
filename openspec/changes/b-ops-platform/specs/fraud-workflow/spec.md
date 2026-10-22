## ADDED Requirements

### Requirement: Acknowledge on the platform
`POST /api/cases/{id}/acknowledge {reason?}` by a fraud analyst or the manager SHALL use the same store function as the contract's `/cases/{id}/acknowledge`. It sends the agent's holding reply (`kind = holding_reply`, `sent = true`), keeps `case_state = with_fraud_team`, and sets `workflow = investigating`. The contract acknowledge SHALL also set `workflow = investigating`.

#### Scenario: Analyst acknowledges
- **WHEN** `fraud1` acknowledges a fraud case
- **THEN** one holding reply is in the outbox, authorised by `fraud1`, and `workflow = investigating`

### Requirement: Log investigation
`POST /api/cases/{id}/investigate {note, kind}` SHALL append an `investigate` event with the note and kind. `kind` is `investigation` (the default) or `recall_attempt`. It needs `workflow = investigating` (409 otherwise) and a non-empty note (422 otherwise). It changes no other state; it builds the case timeline.

#### Scenario: Recall attempt
- **WHEN** `fraud1` logs `{kind: "recall_attempt", note: "recall requested from receiving bank"}`
- **THEN** the case's events end with that `investigate` event

### Requirement: Record outcome
`POST /api/cases/{id}/record-outcome {outcome, reason}` SHALL need `workflow = investigating`. `outcome` is one of `confirmed_fraud`, `not_fraud`, `recall_succeeded` or `recall_failed`. The reason is required.

- **Within the limit and not sensitive:** the outcome is stored as `fraud_outcome {outcome, by, at, reason}`, `workflow = closed`, and a `record_outcome` event is appended.
- **Otherwise:** 403 telling the analyst to escalate with the outcome as the proposal. The amount checked is the matched transaction's amount, or 0 when there is none.
- **The manager:** may record directly.

No customer message is sent, and `case_state` stays `with_fraud_team`.

#### Scenario: High-value fraud
- **WHEN** `fraud1` records `confirmed_fraud` on a case whose disputed transaction is RM8,200.00
- **THEN** the response is 403; `fraud1` then escalates with `outcome = confirmed_fraud`, and the manager's second-tier approve records it and closes the case

#### Scenario: Before acknowledgement
- **WHEN** `fraud1` records an outcome on a fraud case that was never acknowledged
- **THEN** the response is 409
