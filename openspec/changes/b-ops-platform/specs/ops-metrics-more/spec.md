## ADDED Requirements

### Requirement: More dashboard numbers
`GET /api/metrics` SHALL add these fields, keeping every existing one:
- `cases.by_channel`: a count per complaint channel
- `cases.by_language`: a count per `reply_language`
- `cases.by_workflow`: counts of `escalated`, `reprocessing`, `investigating` and `closed`
- `sla.compliance`: the share of closed cases handled within their SLA allowance, or null when none are closed; `sla.closed` is how many closed cases it covers
- `turnaround_minutes`: `mean`, `p50` and `p95` of the minutes from the agent's decision to the first person's closing action, over cases a person closed
- `trends.received_by_day`: one entry per complaint received date, oldest first: `{date, total, by_category}`
- `refunds_myr`:
  - `auto_paid`: auto-resolved refunds
  - `approved_paid`: resolutions sent by people
  - `awaiting`: refunds in open approval cases
  - `rejected`: refunds the agent proposed that people rejected

**Closed** means `auto_resolved`, `approved`, `rejected`, or a fraud case with `workflow = closed`. **Handled within the SLA allowance** means:
- auto-resolved cases always count as met
- for other cases, the time from the case's ingest event to its closing event is at most `resolve_due_at − received_at` of the decision

This measures our handling time against the allowance the policy gives, so it doesn't depend on the complaints being dated in the past.

#### Scenario: Compliance
- **WHEN** two cases are auto-resolved and one approval case was approved by an officer within minutes of arriving
- **THEN** `sla.compliance` is 1.0, and `turnaround_minutes.p50` is a small number

#### Scenario: Refund totals
- **WHEN** one RM46.54 refund auto-resolved, one RM550.00 refund was approved, and one RM709.62 refund awaits approval
- **THEN** `refunds_myr` is `{auto_paid: "46.54", approved_paid: "550.00", awaiting: "709.62", rejected: "0.00"}`

#### Scenario: Trend
- **WHEN** cases were received on 2026-09-29 (2 complaints) and 2026-09-30 (1 complaint)
- **THEN** `trends.received_by_day` is two entries, oldest first, with totals 2 and 1
