## ADDED Requirements

### Requirement: Cases each role can see
A case's **team** SHALL be the route of its current run:
- `HUMAN_APPROVAL` → approval team
- `FRAUD_TEAM` → fraud team
- `AUTO_RESOLVE`, or no run yet → none

What each role sees:
- **Officer:** approval-team cases only.
- **Fraud analyst:** fraud-team cases only.
- **Manager:** every case, including auto-resolved, processing and error cases.

This filter applies to `GET /api/cases` (items, `total` and `counts`) and to `GET /api/cases/{id}`. A case outside the user's view returns 404 from the detail route, so its existence isn't revealed.

#### Scenario: Officer's list
- **WHEN** `officer1` lists cases in a database holding approval, fraud and auto-resolved cases
- **THEN** only the approval cases are listed, and `counts` covers only them

#### Scenario: Fraud case hidden from an officer
- **WHEN** `officer1` requests the detail of a fraud case
- **THEN** the response is 404

### Requirement: Manager-only reads
`GET /api/metrics`, `GET /api/audit` and `GET /api/users` SHALL return 403 for officers and fraud analysts.

#### Scenario: Analyst opens metrics
- **WHEN** `fraud1` calls `GET /api/metrics`
- **THEN** the response is 403

### Requirement: Actions by role
- Approval-team actions (approve, reject, edit reply, send back, flag sensitive, escalate) SHALL be allowed for officers and the manager.
- Fraud actions (acknowledge, investigate, record outcome, flag sensitive, escalate) SHALL be allowed for fraud analysts and the manager.
- Second-tier decisions and reassign SHALL be manager-only.
- Any action on a case outside the user's team SHALL return 403.

#### Scenario: Officer tries a fraud action
- **WHEN** `officer1` posts `record-outcome` on a fraud case
- **THEN** the response is 403 and nothing changes

### Requirement: Assignment
A case MAY have an `assigned_to` user. While it is set, a first-tier user other than the assignee SHALL get 403 on actions; the manager may always act. `GET /api/cases` SHALL accept:
- `assigned_to=<username>`
- `assigned_to=me`
- `assigned_to=none`

Each item SHALL carry `assigned_to`.

#### Scenario: Reassigned case
- **WHEN** the manager reassigns a case to `officer2`, and `officer1` tries to approve it
- **THEN** `officer1` gets 403, and `officer2` can approve it

### Requirement: New list and detail fields
Each item from `GET /api/cases`, and the detail's `case` section, SHALL also carry:
- `workflow`: null, `escalated`, `reprocessing`, `investigating` or `closed`
- `sensitive` (bool) and `sensitive_reason`
- `assigned_to`
- `escalation`: `{by, at, reason, proposal}` or null

`waiting_reason` SHALL be "Escalated to the manager" while escalated, "Sent back: the agent is re-running it" while reprocessing, and null once the workflow is closed.

`GET /api/cases` SHALL accept `workflow=<values>`, including `none`, and `sensitive=true|false`. Its response SHALL add `workflow_counts` (`escalated`, `reprocessing`, `investigating`, `closed`) over the cases the user can see.

Decision fields in the list and detail SHALL come from the case's **current** run. That is the autonomous run unless the case was sent back. The contract view and `predictions.csv` keep using the autonomous run.

#### Scenario: Escalation queue
- **WHEN** the manager calls `GET /api/cases?workflow=escalated`
- **THEN** the escalated cases from both teams are listed, each with its escalation reason and proposal
