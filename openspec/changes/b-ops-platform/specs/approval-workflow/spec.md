## ADDED Requirements

### Requirement: Sensitivity
A case SHALL be **sensitive** when either:
- its current decision has `vulnerable = true` (customer 65+ on `received_at`); `sensitive_reason` is "Customer aged 65+"
- a first-tier user or the manager flagged it with `POST /api/cases/{id}/flag-sensitive {reason}`; `sensitive_reason` is the given reason

A flag needs a non-empty reason (422 otherwise) and can't be removed.

#### Scenario: Elderly customer
- **WHEN** a REFUND of RM120.00 for a 70-year-old customer awaits approval
- **THEN** the case is sensitive with reason "Customer aged 65+", and `officer1`'s approve returns 403 telling them to escalate

### Requirement: First-tier approve
`POST /api/cases/{id}/approve {reason?}` by an officer SHALL send the resolution when all of these hold:
- `case_state = awaiting_approval`
- `workflow` is null
- the case is not sensitive
- the current refund is at most the officer's `approval_limit_myr`
- the reply passes the self-check: the saved edited draft if there is one, otherwise the agent's reply

Sending makes `case_state = approved` and `sent = true`, writes one `resolution` outbox row (`authorised_by` = username) and an `approve` event, and sets `human_action`.

The responses when a condition fails:
- over the limit or sensitive: 403, `{"error": "escalate to a manager", "why": "...", "limit": ..., "amount": ...}`
- a draft that fails the self-check: 422 with its problems
- any other state: 409

The manager has no limit and may approve a sensitive case directly.

#### Scenario: Within the limit
- **WHEN** `officer1` approves a RM550.00 refund
- **THEN** the case is approved and sent, and the outbox row says `authorised_by = officer1`

#### Scenario: Over the limit
- **WHEN** `officer1` approves a RM2,500.00 refund
- **THEN** the response is 403 with `why = "refund RM2,500.00 is over your limit RM2,000.00"`, and nothing is sent

### Requirement: Reject
`POST /api/cases/{id}/reject {reason}` SHALL need a reason (422 otherwise). It sets `case_state = rejected` and sends nothing, for an `awaiting_approval` case with no workflow. It is allowed for an officer within their team, and for the manager.

#### Scenario: Reject without a reason
- **WHEN** `officer1` rejects with an empty reason
- **THEN** the response is 422 and the case is unchanged

### Requirement: Edit reply
`POST /api/cases/{id}/edit-reply {reply_text, reason}` SHALL:
1. run the combined self-check on `reply_text` against the current run
2. save it as the case's draft `{text, self_check, problems, by, at}`, whether or not it passed
3. append an `edit_reply` event whose detail holds `old` (the previous draft, or the agent's reply), `new`, `reason`, `self_check` and `problems`

The response is the case detail. Approve uses the draft, and stays locked (422) while the draft fails. An edit is allowed while `case_state = awaiting_approval` and the workflow is null, or, for the manager, while it is `escalated`.

#### Scenario: Invented amount
- **WHEN** an officer edits the reply to mention RM999.00
- **THEN** the draft is saved with `self_check = flagged`, the problem names RM999.00, and approve returns 422 until a passing edit is saved

### Requirement: Escalate
`POST /api/cases/{id}/escalate {reason, outcome?}` by a first-tier user SHALL:
- set `workflow = escalated`
- store `escalation = {by, at, reason, proposal}`. The proposal is `approve` (with the current draft or the agent's reply) for an approval case, or the given fraud `outcome` for a fraud case.
- append an `escalate` event

The case still waits: `sent` doesn't change, and `case_state` stays `awaiting_approval` or `with_fraud_team`. A reason is required. A case that is already escalated returns 409. Escalating within the limit is allowed.

#### Scenario: Over-limit refund escalated
- **WHEN** `officer1` escalates the RM2,500.00 refund with reason "over my limit"
- **THEN** `workflow = escalated`, `sent = false`, and the case appears in `GET /api/cases?workflow=escalated` for the manager

### Requirement: Second-tier decision
Only the manager SHALL use `POST /api/cases/{id}/second-tier-approve {reason}` and `second-tier-reject {reason}`. A reason is required, and the case must be `escalated`; otherwise the response is 409.

- **Approval case, approve:** send the proposed resolution through the gated send (`case_state = approved`, `sent = true`, outbox `authorised_by` = the manager), then `workflow = closed`.
- **Approval case, reject:** `case_state = rejected`, nothing sent, `workflow = closed`.
- **Fraud case, approve:** record the proposed outcome as final, then `workflow = closed`.
- **Fraud case, reject:** the outcome is not recorded, and `workflow` goes back to `investigating`.

Each decision appends a `second_tier_approve` or `second_tier_reject` event.

#### Scenario: Manager approves an escalation
- **WHEN** `manager1` second-tier-approves the escalated RM2,500.00 refund with reason "verified with branch"
- **THEN** the case is approved and sent, the outbox row is authorised by `manager1`, and the audit shows `escalate` by `officer1`, then `second_tier_approve` by `manager1`

#### Scenario: First tier can't clear it
- **WHEN** `officer1` calls `approve` on a case that is `escalated`
- **THEN** the response is 409

#### Scenario: Contract can't bypass it
- **WHEN** `POST /cases/{id}/actions {"action": "approve"}` is sent for an escalated case
- **THEN** the response is 409 and nothing is sent

### Requirement: Reassign
`POST /api/cases/{id}/reassign {username, reason}` SHALL be manager-only. It sets `assigned_to` to an existing user whose role matches the case's team, or a manager, and appends a `reassign` event with the old and new assignee. An unknown user or the wrong role returns 422.

#### Scenario: Wrong team
- **WHEN** the manager reassigns an approval case to `fraud1`
- **THEN** the response is 422

### Requirement: Send back
`POST /api/cases/{id}/send-back {note}` SHALL be allowed for an officer or the manager on an `awaiting_approval` case with no workflow. A note is required. It:
1. sets `workflow = reprocessing` and appends a `send_back` event
2. runs the pipeline in the background as a `reprocess` run, on the complaint text with `\n\n[Officer note: <note>]` appended
3. when the run is stored:
   - it becomes the case's `current_run_id`; `autonomous_run_id` and the autonomous run never change
   - any draft is cleared, and `workflow` goes back to null
   - the case goes to `with_fraud_team` if the new route is FRAUD_TEAM, otherwise to `awaiting_approval`. **A re-run case is never auto-resolved or sent**, because a person has already been involved.
   - an `agent_run` event records the new run

While `reprocessing`, every action returns 409. A crash in the re-run leaves the current run as it was, sets `workflow` back to null, and appends a `send_back_failed` event.

#### Scenario: Officer supplies the missing date
- **WHEN** a case held as `ambiguous_match` is sent back with note "the charge was on 15-07-2026, RM1,383.20"
- **THEN** a `reprocess` run is stored as the current run, the case awaits approval again with the new decision, and `GET /cases/{id}` (contract) and `predictions.csv` still show the autonomous decision

### Requirement: One gated send
Every message that reaches the outbox because of a person SHALL pass one store function. It checks:
1. the case is in a sendable state for this action
2. an escalated case is only sent by the second-tier approval
3. the reply passed the combined self-check
4. no message of that kind has been sent for the case

This covers contract approve and edit_approve, platform approve, second-tier approve, and acknowledge. A failed check sends nothing. A repeat (double click, retry) returns 409 and never writes a second outbox row.

#### Scenario: Double click
- **WHEN** approve is posted twice in quick succession
- **THEN** the first succeeds, the second returns 409, and the outbox holds one row
