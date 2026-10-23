## ADDED Requirements

### Requirement: Read a case in the contract's shape
`GET /cases/{id}` SHALL return `404` for an unknown ID, and `{"complaint_id", "status": "processing"}` while working. When `status = done`, it SHALL return:
- `complaint_id`, `status`
- `category`, `matched_txn_id` (`""` when none), `outcome`, `refund_amount_myr` (string with two decimals), `priority`, `reply_language`, `route`, `reply_text`: exactly the autonomous run's `prediction_row()`
- `self_check`: `passed` or `flagged`
- `case_state`: one of auto_resolved, awaiting_approval, with_fraud_team, approved, rejected
- `sent` (boolean), `human_action` (null until a person acts)
- `hold_reason` (null or the hold), an addition the contract allows

When `status = error`, it SHALL return `{"complaint_id", "status": "error", "error": <reason>}`.

#### Scenario: Refund over RM500 waits
- **WHEN** CMP-00244 is done
- **THEN** the case has `outcome REFUND`, `refund_amount_myr "550.00"`, `route HUMAN_APPROVAL`, `case_state awaiting_approval`, `sent false`, `human_action null`, `self_check passed`

#### Scenario: Unknown ID
- **WHEN** `GET /cases/NO-SUCH-CASE-123`
- **THEN** the answer is 404

### Requirement: The agent's decision never changes
The decision fields SHALL always come from `cases.autonomous_run_id`, whatever a person does later. That includes `reply_text`: an edited reply appears only in `human_action.reply_text`.

#### Scenario: After an edit
- **WHEN** an officer approves with an edited reply
- **THEN** `reply_text` still shows the agent's draft, and `human_action.reply_text` shows the edited one

### Requirement: Health
`GET /health` SHALL return `200 {"ok": true}` while the service runs.

#### Scenario: Health check
- **WHEN** `GET /health`
- **THEN** the answer is 200
