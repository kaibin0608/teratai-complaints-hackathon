## ADDED Requirements

### Requirement: Approve, reject, edit and approve
`POST /cases/{id}/actions` SHALL accept `{action, actor, reason, reply_text}`, where `action` is `approve`, `reject` or `edit_approve`:
- `actor` is required (non-empty).
- `reason` is required for `reject` and `edit_approve`.
- `reply_text` is required for `edit_approve`.
- Unknown case → `404`.
- Case not `awaiting_approval` (auto-resolved, fraud, already acted on) → `409`.
- Missing or bad fields, or an unknown action → `422`.

On success, the updated case is returned (`200`).

#### Scenario: Approve
- **WHEN** an officer approves a case that is `awaiting_approval`
- **THEN** `case_state` becomes `approved` and `sent` true; `human_action` holds action, actor, reason, `at` (MYT `YYYY-MM-DD HH:MM:SS`) and the reply sent; one outbox message is written; the decision fields are unchanged

#### Scenario: Second action
- **WHEN** the same case is approved again
- **THEN** the answer is 409, and nothing else is sent

#### Scenario: Reject
- **WHEN** an officer rejects with a reason
- **THEN** `case_state` becomes `rejected`, `sent` stays false, and no outbox message is written

### Requirement: Self-check on edited replies
For `edit_approve`, the edited `reply_text` SHALL be checked with `combined_check` against the case's autonomous decision and evidence. If it fails, the answer SHALL be `422` listing the problems, and the case SHALL stay `awaiting_approval` with `sent = false`.

#### Scenario: Invented amount
- **WHEN** the edit adds "We have also credited RM987.65 to your account."
- **THEN** the answer is 422, the case is still `awaiting_approval` with `sent: false`, and the refusal is in the event log

### Requirement: Every action is logged
Every accepted or refused action SHALL append a `case_events` row with the actor, action, reason and self-check result. A case with a person's event can no longer be rerun by the batch runner.

#### Scenario: Audit trail
- **WHEN** an edit is refused and then the case is approved
- **THEN** the events show `edit_approve_refused` and `approve`, in that order, with the actor

### Requirement: Fraud acknowledge (outside the official contract)
`POST /cases/{id}/acknowledge {actor, reason?}` on a `with_fraud_team` case that has not been sent SHALL:
- send the agent's holding reply: outbox `holding_reply`, `sent = true`
- record `human_action` with action `acknowledge`
- keep `case_state = with_fraud_team`

Any other case → `409`. Unknown → `404`. Missing actor → `422`.

#### Scenario: Analyst acknowledges
- **WHEN** a fraud analyst acknowledges a SCAM_TRANSFER case
- **THEN** `sent` becomes true, the outbox holds one holding reply, `case_state` is still `with_fraud_team`, and the decision is unchanged

#### Scenario: Acknowledge twice
- **WHEN** the same case is acknowledged again
- **THEN** the answer is 409
