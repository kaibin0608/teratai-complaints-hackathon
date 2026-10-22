# Evaluation results

What we measured and decided for Dev B's LLM steps, against `data/labels_train.csv`:
- the extractor (`backend/agent/parser.py`), and how often Dev A's engine then picks the right transaction
- the official training score
- the reply writer
- the 750-complaint submission file

## Decision

**Default extractor: `openrouter:deepseek/deepseek-v4-flash`, prompt `extract-v2`, schema `clues-wire-v1`, JSON mode `json_schema`** (2026-10-22).

On 340 unseen holdout complaints it picks the right transaction 99.4% of the time, against 96.8% for the free keyword extractor. It costs about RM0.0016 per complaint.

## Results

### Official score: all 1,750 training complaints (`scoring/score.py`)

The full pipeline (DeepSeek extractor + engine + template replies), run with `backend.batch.runner --ids train --no-draft` and scored with `backend.batch.submit --ids train --score`.

| | Score |
|---|---|
| **Final score** | **99.07 / 100** (keyword baseline in `starter/`: 31.9) |
| Critical errors | 0 (0.0%) |
| matched_txn_id / outcome / refund | 98.9% each |
| category / priority | 100% / 100% |
| reply_language | 98.6% |
| route (not scored) | 92.0% |
| Cost | RM1.95 for the run (RM0.00114 per complaint; pilot and holdout came from the cache) |
| Latency | 4.2 s mean, 9.0 s p95 per complaint (8 in parallel) |

Where the remaining points go:
- **20 wrong transactions, all "last week" complaints.** The date resolver's 7-day window misses the transaction. That's ~0.86 points of the 0.93 lost.
- **25 wrong reply languages:** mostly Malay scam and service complaints read as mixed. 5 points each.
- **7 extractions failed twice** with invalid JSON, even in strict-schema mode, and fell back to keywords (`llm_error`). A rerun fixed all 7. After any large run, check the runner's `llm_error` warning.
- **Route at 92%:** 180 duplicate-charge cases held as `ambiguous_match` for a human. Not scored, but judges check routing in the live round.

### Holdout: 340 complaints never used for tuning

| | Keywords (free) | DeepSeek, prompt v2 |
|---|---|---|
| Category | 98.5% | **100%** |
| Reply language | 93.8% | **99.4%** |
| Right transaction ranked first (top-1) | 96.8% | **99.4%** |
| Outcome correct | 96.5% | **99.4%** |
| Refund correct | 96.8% | **99.4%** |
| Cost | RM0 | RM0.53 |
| Mean latency per call | – | 10.7 s (8 calls in parallel) |
| Retries (all succeeded) | – | 6 (1.8%) |

Field accuracy with DeepSeek: amount 99.0%, approximate flag 100%, counterparty 96.4%, ATM location 96.7%, card last 4 100%, exact date 100%, date window 98.3%, fee type 100%, fee month 100%.

### Pilot: 50 complaints, used for tuning

| | Keywords (free) | DeepSeek, prompt v1 | DeepSeek, prompt v2 |
|---|---|---|---|
| Category | 96.0% | 100% | 100% |
| Reply language | 92.0% | 94.0% | 100% |
| Top-1 transaction | 96.0% | 100% | 100% |
| Cost | RM0 | RM0.096 | RM0.077 |
| Mean latency per call | – | 6.6 s | 6.1 s |

The v1 → v2 change: three casual Malay complaints with English fee words ("kenapa ada monthly service charge ... tolong refund ya") were read as single-language, but the labels treat them as mixed (reply in the customer's preferred language). The prompt now says English words inside Malay sentences count as mixing.

The pilot score is partly tuned to these 50 complaints. The holdout score is the honest one.

### Keyword baseline on all 1,750 training complaints

Top-1 96.5%, category 97.8%, reply language 94.3%, cost RM0. Main gaps: 39 SERVICE_QUALITY complaints read as ATM, fee disputes at 92.6% top-1.

## Remaining errors (holdout, DeepSeek v2)

| Error | Count | Effect | Cause |
|---|---|---|---|
| Wrong transaction | 2 | Lost points | Both say "last week". The date resolver reads it as the 7 days before `received_at`, and both transactions fall just outside. All 5 `date_window` misses are this. |
| "account ending 7534" put into `counterparty_name` | 6 | None today | The text gives an account ending instead of a name. `Clues` has no field for it, although the transaction carries the matching account ending. |
| Approximate amount more than 10% off ("lebih kurang RM150" for RM129.48) | 3 | None (top-1 still right) | Extraction is right; it's outside the matcher's ±10% approximate band. |
| Formal Malay flagged as mixed → wrong reply language | 2 | Lost points | Possibly a side effect of the v2 wording. Check on unused training complaints, not on the holdout. |
| ATM location "missed" | 1 | None | Evaluator false alarm ("hari Khamis **lepas**" matched "Bayan **Lepas**"). |

## Replies (b-reply-writer)

**Default: `openrouter:anthropic/claude-haiku-5.5`, `LLM_DRAFT_REASONING=none`, prompt `draft-v3`** (2026-10-22). Code supplies the facts (amounts, transaction reference, customer-safe reason, next-update date, safety advice) and the status wording. The model only words the reply. Every reply passes Dev A's evidence check plus our rules (refund amount stated, no "has been refunded" before money moves, right language, length).

Pilot, 50 complaints:

| | Code template | DeepSeek v4 Flash | Claude Haiku 5.5 |
|---|---|---|---|
| Passed checks, first draft / after redraft | 50 / 50 | 50 / 50 | 49 / 50 (v3) |
| Fell back (empty reply) | – | 0 with reasoning off; 4–10 with the default `high` | 0 |
| Refund amount stated | 18 / 18 | 18 / 18 | 18 / 18 |
| Words per reply | 61 | 98 | 109 |
| Cost per reply | RM0 | RM0.0003 | RM0.0011 |
| Drafting latency mean / p95 | – | 3.4 s / 9.0 s | 2.3 s / 3.2 s |

Reading 7 pairs side by side: Haiku is warmer and better structured, and its Malay is more natural. DeepSeek wrote "no compensation or refund will be provided" on a service complaint and invented "a gesture of goodwill". Prompt v2 and v3 fixed the issues found in both: slash sign-offs, invented reasons, times of day, a possible authentication-method leak. In the v3 pilot: 0 slash sign-offs, 0 times, 0 invented reasons, 0 authentication mentions.

## Test set: the submission file

`submissions/Santa_Claude/predictions.csv`, from `runner --ids test --rerun` and then `submit --ids test` (2026-10-22). Settings: DeepSeek v4 Flash extraction, Haiku 5.5 replies (`LLM_DRAFT_REASONING=none`), prompts `extract-v2` and `draft-v3`.

| | Result |
|---|---|
| Rows | 750 / 750, valid (unique IDs, valid values, two-decimal refunds, non-empty replies) |
| Replies | all 750 by Haiku 5.5; all pass Dev A's evidence check plus our reply rules; mean 111 words |
| Routes | HUMAN_APPROVAL 354, AUTO_RESOLVE 248, FRAUD_TEAM 148 |
| Holds | ambiguous_match 82; `self_check_failed` 0 |
| Cost of the rerun | RM0.82 (RM0.0011 per complaint; extraction from the cache) |
| Latency | 2.4 s mean, 3.1 s p95 per complaint |
| Scans on all 750 replies | 0 slash sign-offs, 0 times of day, 0 authentication details, 0 invented reasons (3 flags checked by hand: "pengesahan" = confirmation; one "applied in error" right after the real 60+ reason) |

The first test run (template replies, RM1.08 for extraction) is replaced by this one. Spend so far across all runs: about RM4.

Fixes from these runs:
- **One extraction fell back on rerun (CMP-00423).** Its earlier success came on the retry, and the cache had stored it only under the retry request. The client now also caches a retried success under the first request, so reruns repeat.
- **SQLite WAL side files** (`*.db-wal`, `*.db-shm`) added to `.gitignore`. They hold case data, and the repo is public.

## API: the organisers' check (b-contract-api)

`uvicorn backend.main:app`, run against a fresh `backend/api.db` with the `.env` models (DeepSeek extraction, Haiku replies), then `python scoring/api_check.py http://127.0.0.1:8000` (2026-10-22). It sends training complaints all at once, the way the hidden test will.

| Run | Score | Contract problems | case_state / sent match the route | Time per complaint | Probes |
|---|---|---|---|---|---|
| default, 10 complaints | **100.0** | 0 | 10 / 10 | 4.5 s median, 10.5 s slowest | 9 / 9 pass |
| `--n 30` | **99.7** | 0 | 30 / 30 | 6.2 s median, 10.4 s slowest | 9 / 9 pass |

The probes cover: health; unknown case → 404; no text → 422; unknown customer → no 5xx; same complaint twice → unchanged; approval case waits unsent; edit with an invented amount → 422 and nothing sent; approve → approved, sent, actor recorded, decision unchanged; second action → 409.

Notes:
- The 0.3 points lost at 30: two Malay scam complaints with the wrong reply language. That's the "formal Malay read as mixed" issue already listed above.
- "route WRONG" lines (not scored) are duplicate charges held as `ambiguous_match`.
- On a reused database, the unknown-customer probe answers 409: the probe reuses the ID `PROBE-UNKNOWN-CUST` with different text on each run. That's correct (same ID, different content) and still passes.

To run it for the organisers: `uvicorn backend.main:app --host 0.0.0.0 --port 8000` (venue Wi-Fi), or put a tunnel such as ngrok or Cloudflare Tunnel in front. Keep it running from the 15:00 freeze until the demo ends.

## Messy complaints (the hidden test's style)

The hidden test sends 20 complaints "written the way real customers write: typos, SMS short forms, emoji, mixed English and Malay". `backend/eval/make_messy.py` rewrote 42 labelled training complaints (6 per category, none from the pilot, holdout or few-shot examples) with Haiku, in six styles (SMS short forms, rushed typos, Manglish, angry caps and emoji, voice-to-text, casual chat). Every fact is kept, so the original labels apply. The set is fixed in `backend/eval/messy/`. Examples: "sy withdraw rm300 hari selasa lps tp mesin tak keluar duit", "cust called re atm w/d approx rm500 kuching mall atm 8 aug 2026".

`api_check.py --complaints backend/eval/messy/complaints_messy.csv --labels backend/eval/messy/labels_messy.csv --all --no-probes`, all 42 at once:

| | First run | After the retry-budget fix |
|---|---|---|
| Score | 97.1 | **99.4** |
| Transaction / outcome / refund / category / priority | 98% each | **100%** each |
| Reply language | 88% | 88% (label caveat below) |
| Critical errors | 0 | 0 |
| case_state and sent match the route | 42 / 42 | 42 / 42 |
| Time per complaint (fresh, 8 in parallel) | 33.7 s median, 66.5 s slowest | (cached rerun; not a timing test) |

- **The one total miss (MSY-00033, "cash deposit machine … sudah rosak … leh") was an extraction failure.** DeepSeek's default `high` reasoning used the whole 600-token budget, giving empty or cut-off JSON (`finish=length`) in 2 of 3 raw tries. The keyword fallback then read it as an ATM complaint. This is the same cause as the 7 training and 4 test `llm_error` fallbacks. Messy text makes the model reason longer. **Fix:** a retry now gets 3× the token budget (`RETRY_TOKEN_FACTOR`); the first request is unchanged, so cache keys stay valid.
- **The 5 reply-language "misses" are label artifacts, not agent errors.** The rewrites turned single-language originals into code-switched text ("sy dh transfer rm1466.78 … tlg bantu pls"). The agent marked them mixed and replied in the customer's preferred language, which is the training labels' own convention; the copied labels describe the clean originals.
- **Speed:** 42 fresh complaints with 8 in flight queue up (median 33.7 s). The hidden test sends 20, so expect roughly half that, inside the 120 s limit. To go faster: a higher `LLM_MAX_CONCURRENCY` for the server, and/or lower extraction reasoning (needs re-validating accuracy).
  **Decision (Dev B, 2026-10-22):** keep `LLM_MAX_CONCURRENCY = 8`. The speed is acceptable for 20 at once, and 20 simultaneous requests risk provider rate limits (HTTP 429). Revisit only if the hidden-test timing becomes a problem.

## Engine fixes (Dev A's files, found by these runs)

Measured on all 1,750 training complaints with the same cached DeepSeek clues and code replies, so the runs are free and the only difference is the engine (`runner --ids train --no-draft --db <experiment db>` + `submit --ids train --score`):

| | Before | After |
|---|---|---|
| **Final score** | 99.08 | **99.94** |
| matched_txn_id / outcome / refund | 98.9% each | **100%** each |
| route (not scored, judged in the live round) | 92.2% | **99.8%** |
| `ambiguous_match` holds | 185 | **7** |
| Critical errors | 0 | 0 |
| Messy set via the API | 99.4, route ok 37/42 | 99.4, route ok **42/42**, 9/9 probes |

What changed, and why:
1. **"last week" → 2–14 days back** (`date_resolver.py`). In the labels the transaction is always 5–12 days before `received_at` (66 complaints), and the old window (the 7 days before) missed 45. This caused 20 of the 21 wrong transactions. Example: CMP-01618 "RM3,693.71 at QUICKBUY last week" had matched a RM16.91 contactless payment and was held as `unknown_auth_method`; it now matches the right charge.
2. **"kelmarin" → 1–2 days back** (it usually means the day before yesterday, sometimes yesterday; 0 uses in training, so no score effect). Also SMS short forms for the hidden test's style: "ytd", "smlm", "last wk", "mgg lps", "minggu lps". Previously these fell to the full 45-day window.
3. **Recipient / merchant / ATM-location names scored against `merchant_or_counterparty`** (fallback `description`) in `failed_transfer.py`, `scam.py`, `unauthorised.py` and `atm.py`. They had been scored against the memo field ("Makan", "Transfer", "ATM-JOH-01"), so the name never counted. `duplicate.py` already did this.
4. **A tied duplicate pair is confident** (`duplicate.py`). Both charges of a real duplicate score the same, so the generic picker called every duplicate ambiguous and held it for a human (route HUMAN_APPROVAL instead of AUTO_RESOLVE). When the top two tie and are each other's pair (`_find_pair`), the later charge (the one policy refunds) is picked as confident.
5. **Unknown customer → `customer_not_found` wins over `no_match`** (`router.py`), since it's the root cause. The `xfail(strict)` smoke test now passes as a normal test.

Not changed: **the ±10% approximate-amount band.** 10 of 248 "about" amounts are 10–23% off (e.g. "about RM100" for RM123.25), but date and name still found every one, and matching is now 100%. Widening it can only add mix-ups.

**Submission regenerated with the fixed engine** (`runner --ids test --rerun`, then `submit --ids test`): 750/750 valid, 0 fallbacks, all replies pass the checks, RM0.08 (only changed decisions were redrafted). Against the previous file:
- route changed on 64 rows (AUTO_RESOLVE 249 → 313: duplicates no longer held); `ambiguous_match` holds 82 → 3
- **6 rows changed transaction, all "last week" / "minggu lepas" complaints.** Each new match has the exact amount and name the customer gave; each old one was a different, nearby transaction (e.g. CMP-01249 "RM2351.24 kepada Yap Boon Hock" had matched RM225.73 to someone else)
- 4 of the 6 go DECLINE → REFUND: three failed transfers with no reversal, and one ATM shortfall, all refundable under policy. They were checked by hand, since a wrongful refund is a critical error.

Dev A's own tests asserted the old behaviour ("kelmarin" = yesterday; "last week" = the 7 days before). Those two were updated with the data behind the change. `backend/tests/test_engine_fixes.py` adds 18 regression tests; all fail on the old code.

## UI read API (b-ops-read-api)

These are four read-only routes for the React UI, documented for the UI developer in [UI_API.md](UI_API.md): `/api/cases`, `/api/cases/{id}`, `/api/metrics` and `/api/audit`.

**Speed** (uvicorn on a copy of the batch database, 2,500 cases, timed with curl):

| Route | Time |
|---|---|
| `/api/cases?queue=awaiting_approval` (1,115 matches, first 50) | 42 ms |
| `/api/cases?limit=500` | 128 ms |
| `/api/cases/CMP-00244` | 5 ms |
| `/api/metrics` | 213 ms |
| `/api/audit?limit=200` | 18 ms |

Calling `localhost` from Windows curl adds about 0.2 s to every request, because it tries IPv6 first; `127.0.0.1` doesn't. The guide tells the UI to use `127.0.0.1`.

**The contract is unchanged.** `scoring/api_check.py` on a fresh API database with the real models scores **100.0**, with case state and sent correct 10/10 and **9/9 probes**, as before. The new routes then showed:
- 11 cases, auto-resolve rate 0.45
- the probe's approval (override rate 0.0), and its refused edit counted under self-check catches
- one `customer_not_found` hold
- cost per complaint RM0.0010 (p95 RM0.0014)
- latency p50 2.6 s, p95 4.6 s

The latency here is the pipeline's own time. `api_check`'s "median 6.0 s" also counts its 2-second polling and the queue.

**The 2,500-case batch database** (all training and test complaints, real models): auto-resolve rate 0.346; mean cost RM0.0008 per complaint (it's lower than the RM0.0013 median because reruns served from the LLM cache cost 0); latency p50 3.1 s, p95 8.1 s.

**Decisions:**
- **No login yet**; it will be added later on the same routes (Dev B, 2026-10-23).
- **CORS open to any origin**: the UI's address on the venue network isn't known in advance, there are no cookies, and the contract routes are already open.
- **SLA uses an `as_of` clock**: the complaints are dated July–September 2026, so against today's date every open case is overdue. The demo passes `as_of=2026-09-30T16:30`.

## How to reproduce

Needs `OPENROUTER_API_KEY` in `.env`. LLM responses are cached in `backend/.cache/llm_cache.db`, so a rerun with the same prompt and model costs nothing.

```bash
# Keyword baseline (free)
python -m backend.eval.clue_eval --engine --ids holdout

# LLM extractor; uses LLM_EXTRACT from .env
python -m backend.eval.clue_eval --extractor backend.agent.parser:extract --engine --ids pilot
python -m backend.eval.clue_eval --extractor backend.agent.parser:extract --engine --ids holdout --details holdout_details.csv
```

`--details` writes one row per field per complaint (verdict, extracted value, gold value, text), for error analysis.

```bash
# Official training score (template replies; replies aren't scored)
python -m backend.batch.runner --ids train --no-draft
python -m backend.batch.submit --ids train --score --details backend/.cache/train_details.csv

# Reply writer on the pilot, one model at a time; writes the replies to a CSV to read
python -m backend.eval.reply_eval --model openrouter:anthropic/claude-haiku-5.5

# The submission file (add --rerun after a prompt or model change)
python -m backend.batch.runner --ids test
python -m backend.batch.submit --ids test        # → submissions/<TEAM_NAME>/predictions.csv
```

After any large run, check the runner's `llm_error` warning, and rerun those IDs with `--rerun`.

Rules: tune on the pilot (or on the 1,348 training complaints that are in neither set). Only check on the holdout, never tune against it.
