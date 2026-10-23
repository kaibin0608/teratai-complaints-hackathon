## ADDED Requirements

### Requirement: List every issue
`detect_issues(complaint)` SHALL make one LLM call (step `issues`, prompt `issues-v1`). It returns, under a strict JSON schema, `{"issues": [{"category", "quote"}]}`:
- `category` is one of the 7 categories
- `quote` is the customer's own words for that issue

The prompt SHALL define an issue as **a separate problem the customer wants the bank to fix or answer**. It SHALL say that background, the story of how the problem happened, its consequences, and how the customer contacted the bank are not issues. The complaint text SHALL be delimited as data, as in extraction.

#### Scenario: Two issues
- **WHEN** the complaint is "Transfer RM46.54 gagal tapi duit dah tolak. Pastu ada caj fee pulak."
- **THEN** the issues include FAILED_TRANSFER and FEE_DISPUTE, and the fee quote is "Pastu ada caj fee pulak"

#### Scenario: Mention is not a complaint
- **WHEN** the complaint is "ATM tak keluar duit RM300. Sy dah call hotline untuk report."
- **THEN** the only issue is ATM_NOT_DISPENSED

### Requirement: Few-shot examples outside the evaluation set
The prompt SHALL carry few-shot examples covering tricky single-issue wordings and real two-issue complaints. Tricky single-issue wordings include:
- "caj" meaning charged
- "kad ATM" meaning a debit card
- one card used twice
- a hotline call that only reports the problem

No example SHALL come from the evaluation set or copy its wording.

#### Scenario: Examples are independent
- **WHEN** the few-shot file and the evaluation set are compared
- **THEN** no complaint text is shared, and no example quote appears in any evaluation complaint

### Requirement: Code verifies the answer
`other_issues(issues, decision_category, text)` SHALL keep an issue only when all of these hold:
- its category differs from the decision's category
- it isn't a natural overlap: SCAM_TRANSFER with FAILED_TRANSFER or UNAUTHORISED_CARD, and UNAUTHORISED_CARD with SCAM_TRANSFER
- its quote, after lower-casing and collapsing whitespace, is at least 8 characters and appears in the complaint (subject or body)

Duplicates by category are merged.

#### Scenario: Invented quote is dropped
- **WHEN** the LLM returns FEE_DISPUTE with the quote "annual fee is wrong", and those words aren't in the complaint
- **THEN** no other issue is kept

#### Scenario: Natural overlap is ignored
- **WHEN** a SCAM_TRANSFER decision comes with an issue FAILED_TRANSFER quoting "transfer failed"
- **THEN** no other issue is kept

### Requirement: Fails safe
If the issues call raises, times out (`LLM_TIMEOUT_S`) or returns output that fails validation after the client's retry, `detect_issues` SHALL return no issues and the error is noted on the run. The run SHALL NOT be held as `llm_error` because of it. With a `fake:*` provider, or `LLM_ISSUES=off`, no call is made and no issues are returned.

#### Scenario: Provider down
- **WHEN** the issues call raises
- **THEN** the run has `other_issues = []`, its decision is exactly what it would be without the check, and `error` mentions the issues check

### Requirement: Runs alongside extraction
The pipeline SHALL start the issues call together with extraction (`asyncio.gather`), so the check adds no serial latency. The extraction prompt, schema and cache keys SHALL NOT change.

#### Scenario: Extraction cache unaffected
- **WHEN** the test set is re-run after this change
- **THEN** every extraction is a cache hit
