## ADDED Requirements

### Requirement: Immutable agent runs
Every pipeline run SHALL be stored as one row in `agent_runs`, holding the full `AgentRun` as JSON plus flattened decision columns: category, matched_txn_id, outcome, refund in sen, priority, reply_language, route, hold_reason, self_check, error, cost, latency and versions. The database SHALL reject any UPDATE or DELETE on `agent_runs`.

#### Scenario: Run stored
- **WHEN** a pipeline run for CMP-00244 completes and is saved
- **THEN** `agent_runs` has a row with that run_id whose JSON round-trips to an equal `AgentRun`, and whose `refund_sen` is 55000

#### Scenario: Update refused
- **WHEN** any code executes `UPDATE agent_runs SET outcome = 'DECLINE'` or `DELETE FROM agent_runs`
- **THEN** SQLite raises an error and the row is unchanged

### Requirement: One case per complaint
`cases` SHALL hold one row per complaint_id with the six complaint fields, a content hash, `autonomous_run_id`, `current_run_id`, `status` (`processing` / `done` / `error`), `case_state`, `sent`, and created/updated timestamps in MYT.

#### Scenario: First run creates the case
- **WHEN** a complaint with no case is run
- **THEN** a case row is created with `autonomous_run_id = current_run_id = run_id`

#### Scenario: Same complaint, different content
- **WHEN** a complaint is saved with an existing complaint_id but a different content hash
- **THEN** the store raises a conflict error and changes nothing

### Requirement: Case state follows the route
When a run has a decision, the case SHALL be `status = done`, with `case_state` and `sent` set from the run's route:

| route | case_state | sent |
|---|---|---|
| AUTO_RESOLVE | auto_resolved | true |
| HUMAN_APPROVAL | awaiting_approval | false |
| FRAUD_TEAM | with_fraud_team | false |

A run without a decision SHALL set `status = error` and keep the error text. An `auto_resolved` case SHALL get one `outbound_messages` row (kind `resolution`, the reply, the refund, `authorised_by = auto`).

#### Scenario: Refund over RM500 waits
- **WHEN** CMP-00244 (refund RM550.00, route HUMAN_APPROVAL) is saved
- **THEN** its case is `done`, `awaiting_approval`, `sent = false`, and has no outbound message

#### Scenario: Auto-resolved case goes to the outbox once
- **WHEN** an AUTO_RESOLVE run is saved, and then saved again with `--rerun` producing AUTO_RESOLVE again
- **THEN** the case is `auto_resolved`, `sent = true`, and the outbox holds exactly one resolution message for that complaint

#### Scenario: Failed run
- **WHEN** a run whose engine raised is saved
- **THEN** the case is `status = error`, and the error text is readable from the case

### Requirement: Append-only event log
Each saved run SHALL append a `case_events` row (`ingest` for a new case, `agent_run` for every run, with actor `agent`). The database SHALL reject UPDATE and DELETE on `case_events`.

#### Scenario: Rerun is visible in the log
- **WHEN** a complaint is run, then run again with `--rerun`
- **THEN** its events are `ingest`, `agent_run`, `agent_run`, in order, and the second event names the new run_id and the previous one

### Requirement: Reruns only before a human acts
A new autonomous run MAY replace `autonomous_run_id` (`--rerun` after a prompt, model or engine change) only while no human has acted on the case. Cases a human has acted on SHALL be skipped and reported. Earlier runs SHALL stay in `agent_runs`.

#### Scenario: Rerun after a prompt change
- **WHEN** a case has run A, then is rerun producing run B
- **THEN** `autonomous_run_id = B`, run A is still stored, and exporting uses run B
