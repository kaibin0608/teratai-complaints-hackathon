## ADDED Requirements

### Requirement: Dashboard metrics
`GET /api/metrics` SHALL return these sections, computed over every case in the database and each case's autonomous run:
- `cases`: `total`, plus counts `by_queue`, `by_route`, `by_category`, `by_priority` and `by_outcome`
- `auto_resolve_rate`: auto-resolved cases ÷ cases with a decision
- `holds`: a count per `hold_reason`, with the total of held cases
- `self_check`:
  - `first_draft_failed`: runs whose first draft failed and were redrafted
  - `held_self_check_failed`: cases held because the reply still failed
  - `human_edits_refused`: edited replies a person tried to send that the check blocked (`edit_approve_refused` events)
- `human`: counts of `approved`, `rejected`, `edited_and_approved` and `acknowledged`, plus `override_rate`
- `sla`: `as_of`, `open` (cases awaiting approval or with the fraud team), `overdue` (open cases whose `resolve_due_at` is before `as_of`) and `due_within_24h`
- `cost_myr`: `total` over every run, and `mean`, `p50`, `p95` and `max` per complaint
- `latency_ms`: `mean`, `p50`, `p95` and `max` per complaint
- `models`: the number of runs per extraction model and per drafting model
- `throughput`: `decided`, `first_at`, `last_at` and `per_hour`

`override_rate` is (rejected + edited and approved) ÷ (approved + rejected + edited and approved). It is null when no person has decided a case.

Rates are numbers between 0 and 1 rounded to 4 places. Cost figures are strings with 4 decimals, because a complaint usually costs well under one sen. Percentiles use the nearest-rank method. A rate or statistic with no data is null.

#### Scenario: Small known database
- **WHEN** the database holds 4 decided cases (2 auto-resolved, 1 approved by a person, 1 rejected), with autonomous-run costs RM0.0010, 0.0020, 0.0030 and 0.0040
- **THEN**
  - `auto_resolve_rate` is 0.5
  - `human.override_rate` is 0.5
  - `cost_myr.mean` is "0.0025"
  - `cost_myr.max` is "0.0040"

#### Scenario: Empty database
- **WHEN** no case exists
- **THEN** every count is 0, every rate and statistic is null, and the response is still 200

### Requirement: Clock for the SLA view
`GET /api/metrics` SHALL accept `as_of` (an ISO date or datetime, Malaysia time) and use it for `sla.overdue` and `sla.due_within_24h`. When it is omitted, `as_of` is now. A bad value returns 422.

The complaints are dated September 2026, so the demo can pass `as_of=2026-09-30T16:30` to see the SLA as on the live-round day.

#### Scenario: Overdue on the live-round day
- **WHEN** one case awaiting approval is due `2026-09-29T10:00` and another is due `2026-10-03T10:00`, and `GET /api/metrics?as_of=2026-09-30T16:30` is called
- **THEN** `sla.open` is 2 and `sla.overdue` is 1
