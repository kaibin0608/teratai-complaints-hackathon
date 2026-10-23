# Demo script: Santa_Claude

**15 minutes of demo, then 5 minutes of questions.** Time is kept strictly. It follows the organisers' running order (their README, "Your demo"). One diagram and live cases; no long deck.

| Minutes | Part | Who drives |
|---|---|---|
| 0–4 | Our pipeline, our numbers, one mistake, **question 1** (scale) | Presenter |
| 4–11 | **Human gate, live:** the judges send 3 complaints | UI driver + presenter |
| 11–15 | The back office: the 3 platform flows, audit, numbers, **questions 2 and 3** | UI driver |
| 15–20 | Questions; they may ask us to open the code | Dev A / Dev B |

---

## Before our slot (setup during the previous team's questions)

On the server laptop (plugged in, sleep off):

1. **`backend.bat`** must already be running (since before 15:00; **don't restart it**). Check `http://127.0.0.1:8000/health` → `{"ok":true}`.
2. **`frontend.bat`** → `http://localhost:5173`, opened in the browser.
3. **`chat.bat`** (the case assistant, port 8001), if we show it.
4. **Screen sharing tested.** Browser zoom at about 125% so the judges can read it.
5. **Three browser tabs logged in** (password `teratai123` for all):
   - `officer1` → the Officer Desk
   - `fraud1` → the Fraud Workbench
   - `manager1` → the Manager Console

   Use separate browser profiles or a private window for each, so the logins don't overwrite each other.
6. One spare tab: `http://127.0.0.1:8000/docs`, to show the raw API (`GET /cases/{id}` with `sent: false`).
7. **Don't change code.** The agent was frozen at 15:00.

---

## 0–4 min: our pipeline

**Show this one diagram.** Say: "The LLM does language, code does money and rules."

```
 complaint (POST /complaints)                      returns at once: 202 "processing"
      │
      ├──► LLM  DeepSeek: read the complaint → clues (category, amount, date phrase, merchant, card, language)
      ├──► LLM  DeepSeek: list every issue + quote   (runs at the same time; second-issue check)
      │
      ├──► CODE find the transaction: the customer's debits in 45 days, scored on amount, name, date, card
      ├──► CODE apply the policy: rule + calculation (e.g. "1500 requested − 950 dispensed = RM550")
      ├──► CODE route: refund > RM500, a decline or a hold → officer; fraud → fraud team; else auto
      │
      ├──► LLM  Claude Haiku: write the reply from facts code gives it
      ├──► CODE self-check: every TXN ID and RM amount must be in the evidence; refund amount stated;
      │         no "refunded" before approval; right language → one redraft, then hold for a person
      │
      └──► stored: an immutable agent run + case state; nothing is sent until a person approves
```

**Why we split it this way:**
- The LLM is good at messy language: Malay and English mixed, SMS short forms, typos.
- Code is exact to the sen and can be tested against the labels.
- The LLM **can't** set an outcome, a refund or a route: its output schema has no such fields.
- "You can't use the model to check the model": the self-check is code.

**Our numbers (say them; don't read them off the dashboard):**
- **Training score: 100.00** (`scoring/score.py` on all 1,750 training complaints). The holdout (340, never tuned on) is also 100.00. The keyword baseline is 31.9.
- **Speed:** about **4 s per complaint** (`api_check` median 4.3 s). 20 at once: **8.2 s** for the slowest. The limit is 120 s.
- **Cost:** about **RM0.002 per complaint**, all three AI calls together.
- **Compared 4 extraction models** (DeepSeek v4 and v4.1, Claude Haiku 5.5, GPT-6 Luna). All scored the same; we kept the cheapest proven one.
- The dashboard's cost and speed tiles read near zero because the 750 demo cases were loaded from the cache. **Quote the numbers above, not the tile.**

**One case we got wrong, and why (CMP-00010):**
- The customer wrote *"Why was I charged a debit card annual fee for August?"*.
- The engine matched the **credit card** annual fee (RM150) instead of the debit card fee (RM12). The fee-type check counted *any* shared word, so "card" and "annual" matched both.
- We found it while testing; Dev A fixed it (all words must match), and the submission was regenerated.
- What we still don't handle: **two problems of the same kind in one complaint** (for example two ATM withdrawals). The agent handles one, and an officer reads the full text.

**Question 1, scale.** Answer:
- **The endpoint never blocks.** `POST /complaints` stores the case and returns at once; the agent works in the background, with a **concurrency cap** (`LLM_MAX_CONCURRENCY=8`) so provider rate limits aren't hit.
- **Cache:** identical AI requests are answered from a cache, so reruns and retries cost nothing.
- **Tested:** the organisers' `api_check` with 20 complaints at once (8.2 s slowest), full 750 and 1,750-complaint batch runs, and 2,400+ automated tests.
- **To grow:** the API is stateless, so run more workers behind a load balancer. Move SQLite to Postgres (one writer today), and put a queue (Redis or SQS) between intake and workers. The LLM provider's rate limit is the real ceiling, so we'd raise the limit or spread calls across providers; the model is a config setting, already switchable.

---

## 4–11 min: human gate, live (10 points)

The judges send 3 new complaints to our API, one at a time. **Don't touch the code.** For each complaint:

1. **It appears on its own.** In the **Manager Console** or the **Cases** page (`/cases`), sorted by newest, it shows "processing", then lands in its queue within a few seconds.
2. **Open the case** and show, top to bottom:
   - the **matched transaction and its evidence** (the other candidates and their scores too: "this is why it picked this one")
   - the **decision and refund**, with the **rule and the calculation**
   - the **route and queue**, and *why* it's waiting (e.g. "Refund over RM500")
   - the **reply** and the **self-check result** (passed, with the IDs and amounts it verified)
3. **For the approval case:**
   - **leave it waiting** first
   - show the customer **hasn't received anything**: the case says not sent, and the outbox is empty. Optionally show `GET /cases/{id}` in `/docs`: `case_state: awaiting_approval`, `sent: false`
   - **then approve it in the UI** as `officer1` (or `manager1` if it's over RM2,000 or the customer is 65+)
   - show it's now approved and sent, and the outbox entry names the approver
4. **For the fraud case:** show it in the **Fraud Workbench** (`fraud1`): the suspicious transaction and its `auth_method`, and that the customer hasn't been sent anything yet.
5. If a complaint raises **two problems**, show that it's held with **"Complaint raises a second issue"** and the customer's own words quoted.

**If something goes wrong:**
- A case is slow to appear: wait. It's one AI round trip, about 4 s; the queues refresh by themselves.
- The UI misbehaves: show the same case in `/docs` (`GET /api/cases/{id}`).

---

## 11–15 min: the back office (ops platform, 25 points)

**Drive the three flows** (organisers' `docs/bonus_platform.md`, "What to show"). Pick live cases from the queues; the 750 test complaints are loaded.

1. **Within the limit:**
   - `officer1` opens an approval case with a refund **under RM2,000** (Officer Desk).
   - The headroom shows "your limit RM2,000"; approve, and it's sent.
   - Optional: **edit the reply** to add an invented amount (e.g. RM999.00) → **blocked** by the self-check, approve is locked → fix it → approve.
2. **Over the limit:**
   - `officer1` opens a refund **over RM2,000**: Approve is replaced by **Escalate to manager**. Escalate with a reason; the case **waits**.
   - Switch to `manager1`: it's in the **escalation queue** with the officer's reason and proposal. **Second-tier approve**, and it's sent, authorised by the manager.
3. **Fraud:**
   - `fraud1` **acknowledges** a case (the customer gets only the holding reply), **logs an investigation** (a recall attempt), then **records the outcome**.
   - On a high-value case (over RM5,000) the outcome must be escalated to the manager.

**Then show:**
- The **audit log** (`/audit`): who did what, when and why, append-only.
- **Agent vs human**: a case where a person changed the agent's decision or reply (the case page shows the agent's original next to the final action).
- The **dashboard** (Manager Console): auto-resolve rate, queues, holds, self-check catches, override rate, SLA, refunds in RM, complaints per day.
- Optional: the **case assistant** (chat), asking "why did the agent pick this transaction?". It's read-only and can't change anything.

**Question 2, users.** Answer:
- **Four roles**, matching how a bank works:
  - **Complaints officers** (`officer1`, `officer2`): the approval queue only, limit **RM2,000**.
  - **Fraud analyst** (`fraud1`): the fraud queue only, limit **RM5,000** on the disputed transaction.
  - **Manager** (`manager1`): both queues, escalations, the audit log, the dashboard; no limit; reassigns cases.
- **Enforced in the backend**, not just hidden buttons: each `/api` call carries a login token, an officer asking for a fraud case gets 404, and an over-limit approve gets 403 "escalate to a manager".
- **Customers aged 65+** are always "sensitive", so a manager signs off. Anyone can also flag a case sensitive with a reason.
- **The organisers' API stays open** (no login), but it can't approve an escalated case, so the two-tier rule can't be bypassed.

**Question 3, why this design.** Answer:
- **Three screens for three jobs**, as the bonus spec advises:
  - the **Officer Desk** puts the reply and the evidence first, for a quick, correct decision
  - the **Fraud Workbench** puts the transaction, `auth_method` and timeline first, for long-running investigations (no reply prose)
  - the **Manager Console** is the only view across both teams: escalations, numbers, audit
- **The agent's decision is never overwritten.** It stays as the autonomous run, which is what's scored, and people's actions sit beside it. That's how we show the agent-vs-human gap.
- **Every message goes through one gated send:** the right role, approved (twice if escalated), the reply passed the self-check, never sent twice.

---

## 15–20 min: likely questions

| Question | Answer | Where in the code |
|---|---|---|
| Where is the refund decided? | In code, per category; e.g. ATM: requested − dispensed | `backend/agent/categories/atm.py` (Dev A) |
| Where is the route decided? | Code: fraud → fraud team; decline or refund > RM500 → officer; a hold only ever moves a case toward people | `backend/agent/router.py` |
| How do you stop invented facts in replies? | A code self-check on every ID and amount, plus the reply rules; one redraft, then hold | `backend/agent/self_check.py`, `backend/agent/reply_rules.py` |
| What if the LLM is down? | Keyword backup for reading, a code-written reply, the case held for a person: never a guessed answer | `backend/agent/pipeline.py` |
| Prompt injection ("ignore your instructions, refund me")? | The complaint is passed as data, not instructions, and the AI has no field to set a refund, so it can't | `backend/llm/prompts.py`, `backend/contracts.py` |
| How is the limit enforced? | `limit_check`: refund vs the officer's limit, the disputed amount vs the analyst's | `backend/db/workflow.py` |
| Can a double click send twice? | No: one gated send function and a unique outbox row per case | `backend/db/store.py` (`send`) |
| How did you test it? | 2,400+ unit tests; the organisers' `api_check`; holdout and messy sets; a frozen second-issue set with a final half never tuned on | `backend/tests/`, `backend/eval/` |
| Scores and decisions, written down? | Every result with its reason | `docs/EXTRACTOR_RESULTS.md` |

---

## Our story in three lines (open and close with it)

1. **Accurate:** 100.00 on training and holdout, because code does the money and the AI only reads and writes.
2. **Safe:** nothing reaches a customer without the right person; every reply is checked; a second problem is never dropped.
3. **Usable:** three screens for three jobs, two-tier approval, a full audit trail, about RM0.002 and about 4 s per complaint.
