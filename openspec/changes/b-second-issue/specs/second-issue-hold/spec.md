## ADDED Requirements

### Requirement: A verified second issue holds the case
When `other_issues` is non-empty, the pipeline SHALL apply `hold(decision, "second_issue")` after the engine decides and **before** drafting:
- route HUMAN_APPROVAL, or FRAUD_TEAM for INVESTIGATE
- an earlier hold reason is kept

Category, matched transaction, outcome, refund, priority and reply language SHALL stay exactly as the engine decided. The reply is drafted for the held route, so it never says money "has been refunded".

#### Scenario: Auto refund with a fee complaint
- **WHEN** a failed-transfer refund of RM46.54 (AUTO_RESOLVE) comes with a verified FEE_DISPUTE issue
- **THEN** the route is HUMAN_APPROVAL, `hold_reason = second_issue`, the refund is still RM46.54, and the reply says it "will be credited" after review

#### Scenario: Fraud stays with the fraud team
- **WHEN** an INVESTIGATE case has a verified SERVICE_QUALITY issue
- **THEN** the route stays FRAUD_TEAM

#### Scenario: Earlier hold kept
- **WHEN** the engine already held the case as `ambiguous_match`
- **THEN** `hold_reason` stays `ambiguous_match`, and the other issues are still stored on the run

### Requirement: Stored and shown
The run SHALL store `other_issues` (category and quote) and `issues_usage`. The run cost SHALL include the issues call.

In the UI read API:
- `GET /api/cases/{id}` shows `other_issues`
- `waiting_reason` and the hold text for `second_issue` read "Complaint raises a second issue"
- `GET /api/cases?hold_reason=second_issue` filters them

Old runs without these fields still load, with `other_issues = []`.

#### Scenario: Officer sees the quote
- **WHEN** the detail of a held case is opened
- **THEN** `other_issues` lists `FEE_DISPUTE` with the quote "Pastu ada caj fee pulak"

### Requirement: Kill switch
`LLM_ISSUES` (env) SHALL select the issues step's model. It defaults to the value of `LLM_EXTRACT`; `off` disables the check, so no call is made and nothing is held for a second issue.

#### Scenario: Turned off on Day 2
- **WHEN** `LLM_ISSUES=off` and the server is restarted
- **THEN** no issues call is made, and every decision is exactly what it was before this change
