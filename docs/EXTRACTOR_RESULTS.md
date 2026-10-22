# Extractor evaluation results

How well the LLM extractor (`backend/agent/parser.py`) turns complaint text into clues, and how often Dev A's engine then picks the right transaction. Measured against `data/labels_train.csv`.

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

Rules: tune on the pilot (or on the 1,348 training complaints that are in neither set). Only check on the holdout, never tune against it.
