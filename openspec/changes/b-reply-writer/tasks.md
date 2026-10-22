## 1. Reply rules (code check)

- [x] 1.1 `backend/agent/reply_rules.py`: `check(reply, result)`: empty/length, refund amount stated (any RM format), premature refund claim (EN + MS phrases) unless REFUND + AUTO_RESOLVE, language by function words
- [x] 1.2 `combined_check(reply, result)`: Dev A's `check_reply` + `reply_rules.check`, problems merged
- [x] 1.3 Tests: each rule fails and passes; RM format variants; MS phrases; combined lists both problem sets

## 2. Code-written fallback reply

- [x] 2.1 `backend/agent/reply_templates.py`: `render(result)` EN + MS for the five purposes, greeting by full name or generic, transaction reference with date and amount, `RM1,234.56` amounts, DD-MM-YYYY next-update date for fraud and pending cases, fixed safety-advice lines for scam and unauthorised card (shared with the prompt)
- [x] 2.2 Tests: CMP-00001 auto refund, CMP-00244 pending refund, CMP-00008 decline, CMP-00005 holding reply, CMP-00002 info only, unknown customer; every pilot decision passes `combined_check`

## 3. LLM reply writer

- [x] 3.1 `prompts.py`: `DRAFT_PROMPT_VERSION`, `DRAFT_SYSTEM`, `purpose(decision)`, `facts_block(result)`, `build_draft_messages(result, complaint, feedback)`
- [x] 3.2 `backend/agent/reply_generator.py`: `draft(result, feedback=None, *, complaint)`: `fake:*` → code reply; else `LLMClient.text` with the `LLM_DRAFT` spec
- [x] 3.3 Tests (scripted adapter): facts block for CMP-00244 lists only the allowed IDs and amounts and the "will be credited" purpose; INVESTIGATE purpose is a holding reply; complaint inside delimiters; feedback included on redraft; offline config returns the code reply

## 4. Pipeline and runner

- [x] 4.1 `run_pipeline`: `draft=None` → LLM drafter with the complaint; default check → `combined_check`; drafter failure → code reply + `llm_error`; record the draft prompt version
- [x] 4.2 `runner --no-draft` → code reply drafter
- [x] 4.3 Update tests that assumed the old template (pipeline resilience, smoke); full suite passes offline

## 5. Evaluate and choose

- [x] 5.1 `backend/eval/reply_eval.py`: pilot report (check pass rates first draft / after redraft, holds, refund stated, language, length, cost, latency) + replies CSV; `--model` override
- [x] 5.2 Run DeepSeek v4 Flash and Claude Haiku 5.5 on the pilot; read 10 replies of each (EN and MS, every outcome); choose the default; record in `docs/EXTRACTOR_RESULTS.md` and `.env.example`
- [x] 5.3 Rerun the 750 test complaints with replies (`--rerun`); export and validate `submissions/<team>/predictions.csv`; check 0 `self_check_failed` holds remain unexplained
