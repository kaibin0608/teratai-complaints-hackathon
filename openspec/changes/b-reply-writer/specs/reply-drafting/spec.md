## ADDED Requirements

### Requirement: Drafter contract and model selection
`reply_generator.draft(result, feedback, complaint)` SHALL return `(reply_text, LLMUsage)` in `result.decision.reply_language`. The provider and model SHALL come from `LLM_DRAFT`. With `fake:*`, it SHALL return the code-written reply (reply-fallback) without a network call. The pipeline SHALL pass the complaint, so `contracts.Drafter` stays unchanged.

#### Scenario: Offline
- **WHEN** `LLM_DRAFT=fake:template`
- **THEN** the reply is the code-written reply, and the usage provider is `fake`

### Requirement: Facts come from code
The draft prompt SHALL give the model a facts block built in code:
- customer full name (or none)
- reply language, category, outcome and route
- the refund formatted `RM1,234.56`
- the matched transaction ID, date (DD-MM-YYYY), merchant or recipient, and amount
- a customer-safe reason written in code per rule (`reply_facts.reason`). Never the internal calculation text, which contains authentication methods, timestamps and rule details.
- the handler's `reply_guidance`
- the next-update date when required
- the exact list of transaction IDs and RM amounts the reply may mention (`evidence.allowed_txn_ids` / `allowed_amounts`)

The complaint subject and text SHALL be inside a delimited data block. The instructions SHALL forbid any other ID, amount, date or promise.

#### Scenario: ATM shortfall facts
- **WHEN** drafting for CMP-00244 (requested 1,500.00, dispensed 950.00, refund 550.00, route HUMAN_APPROVAL)
- **THEN** the facts block lists RM1,500.00, RM950.00 and RM550.00 as the only allowed amounts, TXN-0088211 as the only allowed ID, and says the refund "will be credited"

### Requirement: Wording by route and outcome
The prompt SHALL state the reply's purpose from the decision:

| Decision | The reply must |
|---|---|
| REFUND + AUTO_RESOLVE | say the refund of the amount has been made |
| REFUND + HUMAN_APPROVAL | say the refund of the amount will be credited; not claim money has moved |
| DECLINE | explain why from the calculation; no refund |
| INVESTIGATE | be a holding reply: report received, under investigation by the fraud team, next update date; no refund, no outcome |
| INFO_ONLY | apologise, say the feedback is recorded and what happens next; no money promised |

#### Scenario: Refund waiting for an officer
- **WHEN** the decision is REFUND RM550.00 with route HUMAN_APPROVAL
- **THEN** the reply states RM550.00 "will be credited" (or the MS equivalent) and contains no "has been refunded"

#### Scenario: Fraud holding reply
- **WHEN** the decision is INVESTIGATE
- **THEN** the reply promises no refund and gives the next-update date

### Requirement: Transaction reference
When there is a matched transaction, the reply SHALL quote it as its ID with date and amount, e.g. "transaction TXN-0088211 on 17-07-2026 (RM1,500.00)".

#### Scenario: Reference quoted
- **WHEN** drafting for CMP-00244
- **THEN** the facts block gives the reference "TXN-0088211 on 17-07-2026 (RM1,500.00)" and instructs the reply to quote it

### Requirement: Held cases state the decision as pending
A case with a `hold_reason` SHALL get a reply for the agent's decision, worded as pending: a refund "will be credited", never "has been refunded". The officer approves or edits it before it is sent.

#### Scenario: Ambiguous duplicate refund
- **WHEN** a DUPLICATE_CHARGE REFUND of RM79.46 is held with `ambiguous_match`
- **THEN** the reply states RM79.46 will be credited, and the rules check passes

### Requirement: Fixed safety advice for fraud categories
For SCAM_TRANSFER and UNAUTHORISED_CARD, the facts block SHALL include 1–2 fixed safety-advice sentences from code in the reply language. Examples: never share your OTP, PIN or password; block the card in the Teratai app or call the hotline. The prompt SHALL allow only these lines as advice. Other categories get no advice lines.

#### Scenario: Scam reply advice
- **WHEN** drafting a SCAM_TRANSFER holding reply in MS
- **THEN** the facts block contains the MS advice lines, and no advice beyond them is allowed

### Requirement: Greeting
The reply SHALL open with the customer's `full_name` ("Dear <name>," / "Yang dihormati <name>,"), or "Dear Customer," / "Tuan/Puan," when the customer is unknown. It SHALL sign off as Teratai Bank.

#### Scenario: Unknown customer
- **WHEN** `evidence.customer` is None
- **THEN** the greeting is "Dear Customer," (EN) or "Tuan/Puan," (MS)

### Requirement: Next-update date only where pending
For INVESTIGATE cases and any case routed HUMAN_APPROVAL, the facts SHALL include "next update by" = `decision.resolve_due_at` as DD-MM-YYYY. For AUTO_RESOLVE cases, no date SHALL be promised.

#### Scenario: Auto-resolved refund
- **WHEN** the route is AUTO_RESOLVE
- **THEN** the facts block contains no next-update date

### Requirement: Feedback on redraft
When called with `feedback` (the self-check problems), the prompt SHALL include the previous problems and ask for a corrected reply. The request differs from the first one, so it is not served from the first call's cache entry.

#### Scenario: Invented amount removed
- **WHEN** the first draft mentions RM600.00, which is not in the evidence, and the redraft is called with that problem
- **THEN** the redraft prompt lists "amount RM600.00 is not in the evidence" as something to fix
