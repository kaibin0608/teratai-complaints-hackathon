## ADDED Requirements

### Requirement: Audit log
`GET /api/audit` SHALL return `{total, limit, offset, facets, items}`:
- `items` are `case_events` rows, newest first, each with `id`, `complaint_id`, `actor`, `action`, `run_id`, `detail` (parsed JSON or null) and `created_at`.
- `facets` lists the distinct `actors` and `actions` in the whole log, for the UI's filter menus.

It SHALL accept these optional filters:
- `actor` (exact match), `action` (one value or a comma-separated list), `complaint_id`
- `since` and `until` (ISO date or datetime, inclusive)
- `people_only=true`, which leaves out events by `agent`
- `limit` (default 100, at most 1000) and `offset`

A bad date or an out-of-range limit returns 422.

#### Scenario: Who did what
- **WHEN** officer "Aina" approved one case and rejected another, and `GET /api/audit?actor=Aina` is called
- **THEN** `total` is 2, and the items are the `reject` and `approve` events, newest first, each with its reason in `detail`

#### Scenario: Refused edit is visible
- **WHEN** a person's edited reply was blocked by the self-check
- **THEN** `GET /api/audit?action=edit_approve_refused` returns that event, with the problems and the refused text in `detail`

#### Scenario: Only people
- **WHEN** `GET /api/audit?people_only=true` is called
- **THEN** no item has `actor = agent`
