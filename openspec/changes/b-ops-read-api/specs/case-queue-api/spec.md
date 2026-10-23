## ADDED Requirements

### Requirement: Case list
`GET /api/cases` SHALL return `{total, limit, offset, counts, items}`:
- `items` is one page of cases matching the filters.
- `total` is the number of matching cases before paging.
- `counts` gives the number of cases per queue key over **all** cases, ignoring filters, so the UI can label its tabs.

The queue keys are `processing`, `error`, `auto_resolved`, `awaiting_approval`, `with_fraud_team`, `approved` and `rejected`. A case's key is its `case_state`, or its `status` when it has no `case_state` (processing or error).

Each item SHALL carry these fields:
- identity and complaint: `complaint_id`, `customer_id`, `customer_name` (null when the customer is unknown), `received_at`, `channel`, `subject`
- state: `status`, `queue`, `case_state`, `sent`
- decision: `category`, `outcome`, `refund_amount_myr`, `priority`, `route`, `hold_reason`, `self_check`, `vulnerable`
- timing and reasons: `resolve_due_at`, `waiting_reason`, `human_action` (`{action, actor, at}` or null), `updated_at`

Decision fields come from the autonomous run and are null while there is none.

#### Scenario: Mixed database
- **WHEN** the database holds one processing case, one auto-resolved case and two cases awaiting approval, and `GET /api/cases` is called
- **THEN** `total` is 4, `counts` is `{processing: 1, auto_resolved: 1, awaiting_approval: 2}` with the other keys 0, and the processing item has `queue = processing` and null decision fields

### Requirement: Filters
`GET /api/cases` SHALL accept these optional query parameters, which combine with AND:
- `queue`, `route`, `category`, `priority`, `hold_reason`: each takes one value or a comma-separated list (OR within the list). `hold_reason=none` matches cases with no hold.
- `q`: a case-insensitive substring of `complaint_id`, `customer_id`, `customer_name` or `subject`.

An unknown value for an enumerated filter SHALL return 422.

#### Scenario: Officer queue
- **WHEN** `GET /api/cases?queue=awaiting_approval` is called
- **THEN** only cases with `case_state = awaiting_approval` are returned, and `counts` still covers every case

#### Scenario: Several values
- **WHEN** `GET /api/cases?queue=approved,rejected&priority=P1` is called
- **THEN** the items are the P1 cases that are approved or rejected

#### Scenario: Bad filter value
- **WHEN** `GET /api/cases?queue=nonsense` is called
- **THEN** the response is 422

### Requirement: Ordering and paging
With `sort=priority` (the default), items SHALL be ordered by:
1. priority: P1, P2, P3, then cases with no priority
2. `resolve_due_at` ascending, with nulls last
3. `received_at` ascending
4. `complaint_id`

With `sort=recent`, items are ordered by latest activity (the case's newest audit event), newest first. Timestamps are only accurate to the second, so the event order is the reliable clock.

`limit` defaults to 50 and is at most 500. `offset` defaults to 0. A value out of range returns 422.

#### Scenario: Urgent first
- **WHEN** the queue holds a P2 case due tomorrow, a P1 case due in three days and a P1 case due today
- **THEN** the order is the P1 due today, the P1 due in three days, then the P2

#### Scenario: Newest activity first
- **WHEN** a case was approved a moment ago and `GET /api/cases?sort=recent&limit=1` is called
- **THEN** that case is the only item

### Requirement: Waiting reason
Every item SHALL carry a short English `waiting_reason`, computed in code, that tells staff why a case is in its queue:
- `processing`: "Agent is working on it"
- `error`: "Agent error"
- `with_fraud_team`: "Fraud investigation", followed by " · " and the hold text when there is a hold
- `awaiting_approval` with a hold: the hold text. The hold texts are:
  - `customer_not_found`: "Customer not found"
  - `ambiguous_match`: "Ambiguous match"
  - `no_match`: "No matching transaction"
  - `category_revised`: "Category revised"
  - `self_check_failed`: "Self-check failed"
  - `unknown_auth_method`: "Unknown authentication method"
  - `llm_error`: "Language model unavailable"
- `awaiting_approval` without a hold: "Refund over RM<limit>" for a REFUND, using `AUTO_REFUND_LIMIT_MYR`; "Decline needs approval" for a DECLINE; otherwise "Needs approval"
- `auto_resolved`, `approved` and `rejected`: null

#### Scenario: Large refund
- **WHEN** a REFUND of RM550.00 with no hold awaits approval
- **THEN** its `waiting_reason` is "Refund over RM500"

#### Scenario: Held fraud case
- **WHEN** an INVESTIGATE case for an unknown customer is with the fraud team
- **THEN** its `waiting_reason` is "Fraud investigation · Customer not found"

### Requirement: Formats shared by every /api route
Every `/api/*` response SHALL use these formats:
- money is a string with two decimals (`"550.00"`), as in the contract API
- datetimes are ISO 8601 Malaysia time with no offset (`"2026-09-30T14:05:00"`)
- `sent` and `vulnerable` are booleans

#### Scenario: Refund formatting
- **WHEN** a case refunds RM46.54
- **THEN** its item has `refund_amount_myr = "46.54"`

### Requirement: Open, read-only and reachable from a browser
`/api/*` GET routes SHALL need no login, never change the database, and allow cross-origin requests from any origin (no credentials). The contract routes' responses SHALL stay the same.

#### Scenario: React dev server
- **WHEN** a browser page on `http://localhost:5173` calls `GET /api/cases` on the API at port 8000
- **THEN** the response carries `access-control-allow-origin: *`
