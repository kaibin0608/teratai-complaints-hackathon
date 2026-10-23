## ADDED Requirements

### Requirement: Case detail
`GET /api/cases/{complaint_id}` SHALL return the whole decision trail of one case, built from the autonomous run, in these sections:
- `case`: `complaint_id`, `status`, `queue`, `case_state`, `sent`, `error`, `waiting_reason`, `human_action` (the full parsed JSON or null), `autonomous_run_id`, `current_run_id`, `created_at`, `updated_at`
- `complaint`: `customer_id`, `received_at`, `channel`, `subject`, `text`
- `customer`: the customer row with `accounts`, or null when the customer is unknown
- `clues`: what the LLM read from the text
- `match`: `status`, `txn_id`, `category`, `category_revised`, and `candidates`, each with `txn_id`, `score` and `reasons`
- `decision`: every `Decision` field, including `rule_id`, `calculation` (`explanation` and `inputs`), `policy_route`, `hold_reason`, `vulnerable`, `ack_due_at` and `resolve_due_at`
- `evidence`: `matched_txn`, `related_txns`, `reversal`, `atm_journal`, `fee_schedule_row`, `allowed_txn_ids` and `allowed_amounts`
- `reply`: `text`, `redraft_count`, and `self_check` (`passed`, `problems`, `found_txn_ids`, `found_amounts`)
- `usage`: `cost_myr`, `latency_ms`, `prompt_version`, `schema_version`, `policy_version`, and the `extract` and `draft` LLM usage (provider, model, tokens, cost, latency, retries, cached)
- `runs`: every run of the case, oldest first, each with `run_id`, `run_kind`, `created_at`, `route`, `outcome`, `hold_reason`, `cost_myr` and `latency_ms`
- `events`: the case's audit trail, oldest first, with `detail` parsed from JSON
- `outbound`: the messages sent, each with `kind`, `reply_text`, `refund_amount_myr`, `authorised_by`, `status` and `created_at`

The formats follow the shared `/api` formats (money as strings, ISO datetimes).

#### Scenario: Refund awaiting approval
- **WHEN** CMP-00244 (ATM refund of RM550.00) has been processed and `GET /api/cases/CMP-00244` is called
- **THEN**
  - `decision.rule_id` and `decision.calculation.explanation` are present
  - `match.candidates` lists the matched transaction first, with its score
  - `reply.self_check.passed` is true
  - `case.waiting_reason` is "Refund over RM500"
  - `outbound` is empty
  - `events` holds `ingest` then `agent_run`

#### Scenario: After an approval
- **WHEN** an officer approves the case through `POST /cases/{id}/actions`
- **THEN** the detail shows `case.case_state = approved`, `sent = true`, an `approve` event with the actor, one `resolution` outbound message authorised by that actor, and a `decision` unchanged from before

### Requirement: Unfinished and unknown cases
`GET /api/cases/{complaint_id}` SHALL return 404 for an unknown ID. For a case that is still processing, or whose run failed, it SHALL return `case` and `complaint` (with the run's `error` when there is one), the events, and null for `customer`, `clues`, `match`, `decision`, `evidence`, `reply` and `usage`.

#### Scenario: Still processing
- **WHEN** a complaint has just been posted and the pipeline has not finished
- **THEN** the detail returns `case.queue = processing`, the complaint text, an `ingest` event and `decision = null`

#### Scenario: Unknown case
- **WHEN** `GET /api/cases/NO-SUCH-CASE` is called
- **THEN** the response is 404
