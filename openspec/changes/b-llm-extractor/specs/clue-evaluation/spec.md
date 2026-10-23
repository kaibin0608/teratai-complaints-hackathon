## ADDED Requirements

### Requirement: Field scoring against the labelled transaction
`backend/eval/clue_eval.py` SHALL score each extracted field against the training label and the labelled transaction as `correct`, `wrong` or `missed`. A field SHALL count as missed only when the complaint text actually contains it. A failed extraction SHALL count every expected field as missed.

#### Scenario: Perfect clues
- **WHEN** CMP-00001 is scored with clues matching its labelled transaction
- **THEN** every scored field is `correct`

#### Scenario: Extraction error
- **WHEN** the extractor raises for a complaint
- **THEN** the report counts it under extraction errors, and its expected fields are `missed`

### Requirement: Date window scoring through Dev A's resolver
The evaluator SHALL score a `date_window` field. It is correct when the window from Dev A's `resolve_date(date_phrase, date_exact, received_at)` (or `resolve_fee_month` for FEE_DISPUTE) contains the labelled transaction's date. It SHALL count as expected for every complaint that has a labelled transaction.

#### Scenario: Wrong date_exact overrides a correct phrase
- **WHEN** `date_phrase = "13 Sep"` is correct but `date_exact` is one day off
- **THEN** `date_window` is `wrong`, because the resolver uses `date_exact` as a one-day window

#### Scenario: Phrase the resolver does not recognise
- **WHEN** `date_phrase = "yesterday evening"` and the resolver falls back to the full 45-day window, which contains the transaction
- **THEN** `date_window` is `correct`, and the details CSV records how wide the window is, so wide windows can be found

### Requirement: Shared rules imported from Dev A
The evaluator SHALL take its reply-language rule and its amount tolerances from Dev A's modules (`backend.agent.router`, `backend.agent.categories.base`) instead of keeping copies.

#### Scenario: Dev A changes the tolerance
- **WHEN** Dev A changes the approximate-amount tolerance in `score_amount`
- **THEN** the evaluator's `amount_mentioned` verdicts follow without editing `clue_eval.py`

### Requirement: Fee month expected only when a month is named
`fee_month` SHALL count as expected only when the complaint text names a month (English or Malay, full or abbreviated).

#### Scenario: Relative month
- **WHEN** a FEE_DISPUTE complaint says "bulan lepas" and the extractor leaves `fee_month` null
- **THEN** `fee_month` is not scored as missed (date_window still scores the outcome)

### Requirement: Engine-level match accuracy
With `--engine`, the evaluator SHALL run `match_and_decide` on each extracted `Clues` and report, per category, how often the top-ranked transaction is the labelled one, how often the labelled transaction is only among the candidates, and the match status breakdown (confident, ambiguous, none). It SHALL make no drafting calls.

#### Scenario: Engine report on the pilot
- **WHEN** `python -m backend.eval.clue_eval --extractor backend.agent.parser:extract --engine` runs on the pilot
- **THEN** the output includes a per-category table of top-1 transaction accuracy and match status counts, and total LLM cost in RM

#### Scenario: Gold clues
- **WHEN** `--extractor` points to a fixed set of clues (or `fake_extract`)
- **THEN** the same report runs without any LLM call, so matching problems can be told apart from extraction problems
