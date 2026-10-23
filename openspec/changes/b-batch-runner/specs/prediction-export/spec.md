## ADDED Requirements

### Requirement: Export from autonomous runs only
`python -m backend.batch.submit` SHALL write one row per case from the run in `cases.autonomous_run_id`, using `AgentRun.prediction_row()`, with columns exactly `PREDICTION_COLUMNS`. It SHALL never read human edits, final actions or reprocess runs. The default output is `submissions/<TEAM_NAME>/predictions.csv` for `--ids test`.

#### Scenario: Human edit doesn't leak
- **WHEN** a case's reply was later edited by a human
- **THEN** the exported `reply_text` is the autonomous run's reply

### Requirement: Validation
Before writing, the export SHALL check:
- every row: category, outcome, priority, reply_language and route are valid values; `refund_amount_myr` has exactly two decimals and is not negative; `matched_txn_id` is empty or matches `TXN-\d{7}`; `reply_text` is not empty
- the file: complaint IDs are unique, and the set equals the requested IDs (exactly the 750 IDs in data/test_ids.csv for `--ids test`)

#### Scenario: Valid test export
- **WHEN** all 750 test complaints have a done case and the export runs with `--ids test`
- **THEN** it writes 750 rows plus the header and reports "valid"

#### Scenario: Invalid value
- **WHEN** a stored run has an empty reply_text
- **THEN** the report names that complaint_id and the failed check

### Requirement: Gaps are reported, never filled
Complaints with no case, a case in `error`, or a run without a decision SHALL be listed by ID and reason. The export SHALL NOT invent rows for them. By default it writes the valid rows and exits with a non-zero status when anything is missing or invalid. `--strict` writes nothing in that case.

#### Scenario: Missing complaints
- **WHEN** 3 of the 750 test complaints have no stored decision
- **THEN** the report lists the 3 IDs with their reasons, the file has 747 rows, and the exit status is non-zero

### Requirement: Score training exports
With `--score`, after exporting training IDs, the export SHALL run `scoring/score.py` on the written file against `data/labels_train.csv` and print its result. With `--details`, it SHALL also write the scorer's per-complaint details.

#### Scenario: Training score
- **WHEN** `submit --ids train --out <file> --score` runs after a full training batch
- **THEN** the official score and critical-error rate are printed
