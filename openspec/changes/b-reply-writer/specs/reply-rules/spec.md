## ADDED Requirements

### Requirement: Combined self-check
The pipeline's self-check SHALL be Dev A's `check_reply` (IDs and amounts in evidence) plus `reply_rules.check(reply_text, result)`. The problems are concatenated; the reply passes only if both pass. The same combined check SHALL be available for human-edited replies.

#### Scenario: Both checks contribute
- **WHEN** a reply has an invented amount and omits the refund amount
- **THEN** the check fails with both problems listed

### Requirement: Refund amount stated
When `refund_amount_myr > 0`, the reply SHALL mention that amount (any of `RM550`, `RM550.00`, `RM 550.00`, `RM1,383.20` forms).

#### Scenario: Missing refund amount
- **WHEN** the decision refunds RM46.54 and the reply never mentions RM46.54
- **THEN** the problem "the reply does not state the refund amount RM46.54" is reported

### Requirement: No premature refund claim
Unless the decision is a REFUND with route AUTO_RESOLVE, the reply SHALL NOT claim money has already moved. Checked phrases include EN "has been refunded", "have refunded", "has been credited", "have credited", and MS "telah dikreditkan", "telah dikembalikan", "telah dibayar balik", "sudah dikreditkan".

#### Scenario: Pending refund worded as done
- **WHEN** the route is HUMAN_APPROVAL and the reply says "has been refunded"
- **THEN** the check fails with a problem naming the phrase

### Requirement: Language matches
A reply SHALL look like its `reply_language`, judged by counting common function words. EN: the, your, we, you, and, to, of, is. MS: anda, kami, dan, yang, untuk, akan, telah, ini. The language with more hits wins, and a tie fails.

#### Scenario: Wrong language
- **WHEN** `reply_language = MS` and the reply is in English
- **THEN** the problem "the reply is not in MS" is reported

### Requirement: Non-empty and bounded
A reply SHALL be non-empty after trimming and at most 1,500 characters.

#### Scenario: Empty reply
- **WHEN** the reply is whitespace only
- **THEN** the check fails with "the reply is empty"
