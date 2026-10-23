## ADDED Requirements

### Requirement: Accept a complaint and process it in the background
`POST /complaints` SHALL accept a JSON body with `complaint_id`, `customer_id`, `received_at`, `channel`, `subject` and `text`. It SHALL store the case with `status = processing`, start the pipeline without waiting for it, and answer `202 {"complaint_id": ..., "status": "processing"}`. Unknown extra fields SHALL be ignored.

#### Scenario: New complaint
- **WHEN** CMP-00244's six fields are posted to a fresh service
- **THEN** the answer is 202 with status `processing`, and a later `GET /cases/CMP-00244` returns `status: done`

### Requirement: Reject bad input with 4xx
Missing or empty `complaint_id`, `customer_id`, `received_at` or `text`, or a `received_at` that isn't a recognised date-time, SHALL get `422`, and nothing SHALL be stored. A malformed body SHALL never produce a `5xx`.

#### Scenario: No text
- **WHEN** a complaint without `text` is posted
- **THEN** the answer is 422, and `GET /cases/<id>` returns 404

### Requirement: Same complaint twice
Posting a `complaint_id` that already exists with the same content SHALL return `200` with the existing case's status, and SHALL NOT create a run, a case or an event. The same ID with different content SHALL return `409` and change nothing.

#### Scenario: Repost while done
- **WHEN** a done complaint is posted again unchanged
- **THEN** the answer is 200 with status `done`, and outcome, matched_txn_id and refund_amount_myr are unchanged

#### Scenario: Conflicting repost
- **WHEN** the same complaint_id is posted with different text
- **THEN** the answer is 409

### Requirement: Unknown customer never crashes
A `customer_id` that isn't in the data SHALL be accepted and processed. The engine holds it with `customer_not_found`, routed HUMAN_APPROVAL (or FRAUD_TEAM if INVESTIGATE).

#### Scenario: Unknown customer
- **WHEN** a complaint for CUS-99999 is posted
- **THEN** the answer is 202, and the case finishes `done` with `hold_reason = customer_not_found`

### Requirement: Bounded concurrency and failure handling
At most `LLM_MAX_CONCURRENCY` pipelines SHALL run at once. Further complaints wait their turn while remaining `processing`. If the pipeline raises, or returns a run without a decision, the case SHALL become `status = error` with the reason.

#### Scenario: Twenty at once
- **WHEN** 20 complaints are posted at the same moment
- **THEN** all are answered 202 at once, and all reach `done` or `error`

### Requirement: Restart recovery
On startup, every case still `processing` (for example after a crash) SHALL be queued again.

#### Scenario: Crash mid-run
- **WHEN** the service restarts with a case stuck in `processing`
- **THEN** that case is processed and reaches `done` without being posted again

### Requirement: Fail fast on bad config
Startup SHALL run `check_config()`. An unknown provider or a missing key SHALL stop the service with the error before it serves requests.

#### Scenario: Missing key
- **WHEN** `LLM_EXTRACT` uses openrouter and `OPENROUTER_API_KEY` is empty
- **THEN** the service fails to start, naming the missing variable
