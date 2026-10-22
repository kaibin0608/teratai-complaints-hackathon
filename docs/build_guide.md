# Build guide

Use any stack you like. This guide gives a reference workflow that meets the rules, and the pitfalls we expect teams to hit.

## A reference workflow

```
new complaint ──► 1. UNDERSTAND (LLM) ──► 2. FIND THE TRANSACTION (code) ──► 3. DECIDE (code)
                                                                                   │
   case record ◄── 6. ROUTE (code) ◄── 5. CHECK (code) ◄── 4. DRAFT THE REPLY (LLM) ◄┘
        │
        ├── AUTO_RESOLVE   → reply sent, case closed
        ├── HUMAN_APPROVAL → approval queue: an officer approves or edits, then it is sent
        └── FRAUD_TEAM     → fraud queue, P1; holding reply to the customer
```

1. **Understand (LLM).** From the complaint text, extract structured fields: category, language, and the clues to the transaction (amount, exact or approximate; merchant or recipient name, full or partial; date phrase; card last 4; fee type and month). Return JSON and validate it.
2. **Find the transaction (code).** Turn the date phrase into a date range, using the `received_at` date ("yesterday", "hari Sabtu lepas", "last week"). Filter the customer's debits in the 45-day window by channel family, amount (with a tolerance for "about"), name (partial, case-insensitive), date and card. For duplicates, take the later of the two identical charges. If you are left with zero or several candidates, don't guess: flag the case and say so.
3. **Decide (code).** Apply `complaint_policy.csv` with the evidence: reversals, `status`, `auth_method`, the ATM journal, the fee schedule with the customer's age and the card's open date. Work out the refund to the sen. Set priority (base, plus one level for 65+) and the route.
4. **Draft the reply (LLM).** Give it the decision and the evidence pack, and ask for a short reply in `reply_language`. It must not change the decision or invent facts.
5. **Check (code).** Every transaction ID and RM amount in the reply must exist in the evidence (`starter/check_reply.py`). If the check fails, redraft once, then flag it for a human.
6. **Route and write back.** Store a case record (decision, matched transaction, evidence, reply, check result, route, due date from `sla_policy.csv`) and put it in the right queue.

Steps 2, 3 and 5 are deterministic: you can test them against `labels_train.csv` without calling an LLM. That's where most of the points are.

## Where to use the LLM and where to use code

| Task | Use | Why |
|---|---|---|
| Reading messy English, Malay and mixed text | LLM | Language understanding |
| Turning "last Friday" into a date | Code (LLM can help extract the phrase) | Arithmetic on dates must be exact |
| Searching 156k transactions | Code | Exact, fast, cheap |
| Applying the refund rules | Code | Money must be right to the sen, and auditable |
| Writing the reply | LLM | Tone and language |
| Verifying the reply | Code | You can't use the model to check the model |

An agent that lets the LLM choose which tools to call (for example `find_transactions(customer, filters)`, `get_atm_journal(txn)`, `get_fee_schedule(product)`) is welcome. The decision rules and the self-check must still run in code.

## Pitfalls

- **Pasting the whole transactions table into a prompt.** It's slow and costly, and the model will still pick the wrong row. Give it the evidence pack for one customer, or tools.
- **Relative dates.** "Hari Selasa lepas" means the most recent Tuesday before the complaint arrived. "Last week" is fuzzy: search a range, then use the amount and name.
- **Approximate amounts.** "Lebih kurang RM1,400" can be RM1,383.20. Match with a tolerance, then confirm with the name or date.
- **Duplicates that aren't.** Two identical charges days apart are two purchases. Charges reversed already have been refunded.
- **Mixed language.** A reply to a mixed or call-centre complaint uses `preferred_language`, not your guess.
- **Age rules.** Vulnerable is 65+ on the received date. The debit fee waiver is 60+ on the charge date. These are different dates.
- **Running out of time.** 750 complaints × several LLM calls takes a while. Run them in parallel and cache results. The test complaints are available from Day 1.
- **Secrets.** Keep API keys in environment variables, never in the repo. This repo is public.
