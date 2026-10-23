## ADDED Requirements

### Requirement: Select complaints
`python -m backend.batch.runner --ids <set>` SHALL accept `test` (data/test_ids.csv), `train` (all of labels_train.csv), `pilot`, `holdout`, or a path to a file of IDs, plus `--limit N` to take the first N. It SHALL run the provider check (`check_config`) before processing anything.

#### Scenario: Test set
- **WHEN** the runner starts with `--ids test`
- **THEN** it processes exactly the 750 IDs in data/test_ids.csv

#### Scenario: Bad config
- **WHEN** `LLM_EXTRACT` names an unknown provider
- **THEN** the runner exits with the config error before any complaint is processed or stored

### Requirement: Concurrent processing
The runner SHALL process complaints concurrently, with at most `--concurrency` (default `LLM_MAX_CONCURRENCY`) pipelines in flight. It SHALL store each run as soon as it finishes, so a crash loses at most the runs in flight.

#### Scenario: Interrupted batch
- **WHEN** a run of 750 complaints is stopped after 300 have been stored
- **THEN** those 300 runs and cases are in the database

### Requirement: Resume and rerun
By default the runner SHALL skip complaints whose case already has a run with a decision, and retry complaints whose case is `error`. `--rerun` SHALL run every selected complaint again, creating new runs (subject to the case-store rule on human actions).

#### Scenario: Resume after a crash
- **WHEN** the same `--ids test` command is run again after an interruption
- **THEN** only complaints with no stored decision are processed, and the summary says how many were skipped

#### Scenario: Rerun after a prompt change
- **WHEN** the runner is started with `--rerun --ids pilot`
- **THEN** all 50 pilot complaints get new runs, and unchanged LLM requests are served from the cache

### Requirement: No-draft mode
With `--no-draft`, the runner SHALL use the template reply in the decision's language and make no drafting LLM calls. While no LLM drafter exists, this is also the default.

#### Scenario: Checkpoint 1 run
- **WHEN** the runner runs with `--no-draft --ids pilot`
- **THEN** every run's draft usage shows the template provider, and extraction still uses `LLM_EXTRACT`

### Requirement: Run summary
At the end, and every 50 complaints during the run, the runner SHALL report:
- processed, skipped and failed counts
- counts by route and by hold_reason
- total and per-complaint cost in RM
- mean and 95th-percentile end-to-end latency per complaint
- wall time

#### Scenario: Summary after a pilot run
- **WHEN** a 50-complaint run finishes
- **THEN** the output shows 50 processed, the route counts summing to the number of decisions, total cost in RM, and latency figures

### Requirement: End-to-end latency recorded
The runner SHALL record each run's wall-clock time from the start of the pipeline to the decision, in milliseconds, in `agent_runs.latency_ms`.

#### Scenario: Latency stored
- **WHEN** a run is saved by the runner
- **THEN** its `latency_ms` is greater than 0 and at least the sum of its LLM latencies
