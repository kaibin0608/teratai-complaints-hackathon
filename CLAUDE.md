# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Teratai Bank Complaints Agent Hackathon. Build an AI agent that reads bank complaints (English/Malay/mixed), finds the matching transaction, applies policy, decides refund, drafts reply, and routes the case. All data is synthetic. Payment-rail names (DuitNow, IBG, JomPAY) are for realism only.

## Commands

```bash
# View evidence pack for one complaint
python starter/evidence_pack.py CMP-00244

# Run keyword baseline (writes submissions/baseline/predictions.csv)
python starter/baseline.py

# Score predictions against training labels (31.9 is baseline to beat)
python scoring/score.py submissions/baseline/predictions.csv data/labels_train.csv

# Score with per-complaint detail
python scoring/score.py submissions/<team>/predictions.csv data/labels_train.csv --details details.csv

# Verify a drafted reply against evidence
python starter/check_reply.py CMP-00244 "We have refunded RM550.00 for transaction TXN-0088211."
```

Python 3.10+ required. Starter kit uses standard library only (no pip install needed).

## Architecture

### Data layer (`starter/data.py`)
- `load()` returns a `DB` object with all CSVs parsed into dicts keyed by ID
- `db.complaints`, `db.customers`, `db.accounts` — dict by primary key
- `db.txns_by_customer` — defaultdict(list), transactions pre-grouped by customer_id with `amount` (float) and `time` (datetime) added
- `db.reversal_of` — maps original txn_id to its reversal transaction row
- `db.atm_journal` — keyed by txn_id
- `db.fee_schedule` — list of dicts
- `db.policy` — keyed by category
- `db.params` — flat dict of policy parameters (thresholds, limits)
- Helper: `age_on(dob, date)` computes age; `received(complaint)` parses received_at

### Scoring (`scoring/score.py`)
Per complaint max 100 points: matched_txn_id (25), outcome (25, gated on txn), refund_amount_myr (25, gated on txn), category (10), priority (10), reply_language (5). Outcome and refund score zero if transaction is wrong. Critical errors (wrongful refund, missed fraud) penalize: `final = mean × (1 − 2 × critical_error_rate)`.

### Reply checker (`starter/check_reply.py`)
Extracts TXN-IDs and RM amounts from reply text via regex, verifies each exists in the customer's evidence window. Must be run as code, not by LLM. **Also re-runs when humans edit replies (bonus platform requirement).**

### Evidence pack (`starter/evidence_pack.py`)
Builds a text summary for one complaint: complaint text, customer info (age, vulnerability flag), accounts, and all debits within the match window annotated with reversals, ATM journal, auth methods.

## Key design principle

**LLM does language** (understanding complaint text, writing reply). **Code does money and rules** (transaction matching, policy application, refund calculation, reply verification). Decision rules and self-check must run in code, not LLM.

## The seven categories and core rules

DUPLICATE_CHARGE, FAILED_TRANSFER, ATM_NOT_DISPENSED, UNAUTHORISED_CARD, SCAM_TRANSFER, FEE_DISPUTE, SERVICE_QUALITY. Full decision rules in `data/complaint_policy.csv`, thresholds in `data/policy_parameters.csv`.

- **Priority:** P1 (scam, unauthorised), P2 (duplicate, failed transfer, ATM), P3 (fee, service). Customer aged 65+ on received_at bumps one level up.
- **Reply language:** language of complaint text. Mixed language or call-centre note → customer's `preferred_language`.
- **Routing:** INVESTIGATE → FRAUD_TEAM. DECLINE → HUMAN_APPROVAL. REFUND > RM500 → HUMAN_APPROVAL (RM500.00 exactly = AUTO_RESOLVE). INFO_ONLY → AUTO_RESOLVE.
- **FEE_DISPUTE refund logic:** `refund = charged - amount_due`. amount_due from fee_schedule.csv with waivers: Basic Savings monthly = RM0, debit card annual waived if customer 60+ on **charge date**, credit card annual waived if charge date < first anniversary of account `open_date`. If refund > 0 → REFUND, else DECLINE.

## Three platform roles (bonus ops platform)

| Role | Sees | Approval limit |
|---|---|---|
| Complaints Officer | HUMAN_APPROVAL queue | Up to their limit (e.g. RM5,000) |
| Fraud Analyst | FRAUD_TEAM queue | Up to their limit |
| Manager | Both queues + escalations + audit + metrics | No limit |

Two-tier approval: first tier clears within limit, over-limit escalates to manager and waits.

## Data integrity rule

`agent_decision` fields are immutable — what the leaderboard scores. `final_action` is what staff did. These are separate. `predictions.csv` always reflects agent's autonomous output.

## Live round

Judges provide 2-3 complaints in CSV format with `received_at = 2026-09-30`. Customer and transaction already exist in data. System must accept without code changes (API or intake form).

## Critical pitfalls

- Relative dates ("hari Selasa lepas", "last Friday") are relative to `received_at`, not today
- Amounts can be approximate ("lebih kurang RM1,400" might be RM1,383.20) — match with tolerance
- Duplicate charges must be within 10 minutes and neither already reversed
- Call-centre notes are written by staff in English third-person — reply language uses `preferred_language`
- Age 65+ (vulnerable) uses received_at date; debit fee waiver age 60+ uses charge date — different dates
- Credit card annual fee waived in first year from `open_date`
- 750 test complaints × multiple LLM calls = plan for parallelism and caching
- Self-check must re-run on human-edited replies (bonus platform requirement)

## Submission

Fork this repo. Build in fork. `submissions/<team-name>/predictions.csv` with columns: `complaint_id, category, matched_txn_id, outcome, refund_amount_myr, priority, reply_language, route, reply_text`. PR from fork to upstream titled `Submission: <team-name>` before 15:00 Day 2. PR needs predictions.csv only.
