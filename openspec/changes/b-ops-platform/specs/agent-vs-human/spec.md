## ADDED Requirements

### Requirement: Final action beside the agent's decision
`GET /api/cases/{id}` SHALL add:
- `autonomous`: the autonomous run's decision fields (`outcome`, `refund_amount_myr`, `route`, `matched_txn_id`) and `reply_text`
- `final`: what people did and what reached the customer, or null while nobody has acted. Its fields are:
  - `action`, `by`, `at`
  - `outcome` (the outcome sent, `REJECTED`, or the fraud outcome)
  - `refund_amount_myr` (from the resolution outbox row, or `"0.00"`)
  - `reply_text` (the sent reply or null)
  - `sent`
- `differs`: `{decision, refund, reply}` booleans, each true when the final value differs from the autonomous one

  A reject, or a send back that changed the decision, counts as `decision` differing. An edited reply counts as `reply`.

#### Scenario: Edited and approved
- **WHEN** an officer edits the reply and approves it
- **THEN** `final.reply_text` is the edited text, `differs.reply` is true, and `differs.decision` is false

#### Scenario: Escalated and rejected
- **WHEN** the manager second-tier-rejects an escalated refund
- **THEN** `final.outcome = REJECTED`, `final.sent = false` and `differs.decision` is true

### Requirement: Overridden filter
`GET /api/cases?overridden=true` SHALL list the cases where people changed the agent's decision or reply: rejected, edited, or sent back with a changed decision. `overridden=false` lists the rest.

#### Scenario: Override list
- **WHEN** one case was approved as-is and another was edited then approved
- **THEN** `overridden=true` lists only the edited one
