# Testing the API by hand

How to call each of the 24 endpoints, and what you should see. The fields and rules are in [api.md](api.md) (the organisers' contract) and [UI_API.md](UI_API.md) (the UI and platform routes); this guide is the hands-on part.

Every command below was run against `main` at `2e86e93` on 2026-10-23 and gave the result shown.

## Three ways to test

| Way | Command | Covers | Cost |
|---|---|---|---|
| The organisers' check | `python scoring/api_check.py <url>` | the 5 contract routes, scores and 9 probes | real models |
| The test suites | `.venv/Scripts/python -m pytest backend/tests/test_api.py backend/tests/test_auth.py backend/tests/test_ops_api.py backend/tests/test_platform_api.py -q` | 23 of the 24 routes (not the plain officer `reject`) | free (offline models, throwaway database) |
| By hand | this guide, or the clickable page at `<url>/docs` | all 24 | real models |

## Before you start

**Use a test server, not the live one.** Every action you take is saved for good in the server's database, and the cases show up in the demo queues and the dashboard. Start a second server on port 8001 with its own database:

```bash
# Git Bash, from the repo folder
API_DB_PATH=backend/test_api.db .venv/Scripts/python -m uvicorn backend.main:app --port 8001
```

```powershell
# PowerShell, from the repo folder
$env:API_DB_PATH="backend/test_api.db"; .venv\Scripts\python -m uvicorn backend.main:app --port 8001
```

- It uses the models in `.env`. With no `.env`, it uses the free offline models, which give the same decisions for the complaints used here.
- Testing the live server (`http://10.0.30.131:8000`) works the same way. **Never test it between 15:00 and 15:45**, while the organisers' hidden test is running.

**Run the commands in Git Bash** (it comes with Git for Windows), from the repo folder. You need `curl` and `python` on the path. In PowerShell, `curl` is a different command and the JSON quoting breaks, so use Git Bash, or the `/docs` page.

**Paste this setup first.** It sets the server address, a prefix for this test run, and five small helpers:

```bash
B=http://127.0.0.1:8001   # the server to test
P=T1                      # prefix for this run's complaint IDs; use T2, T3... to run the steps again

# call METHOD PATH [JSON] [TOKEN]: prints the HTTP code and the start of the answer
call() {
  local args=(-s -o /tmp/resp.json -w 'HTTP %{http_code}  ' -X "$1" "$B$2" -H "content-type: application/json")
  [ -n "$3" ] && args+=(-d "$3")
  [ -n "$4" ] && args+=(-H "authorization: Bearer $4")
  curl "${args[@]}"; head -c 300 /tmp/resp.json; echo
}
# copy SOURCE NEW_ID: a training complaint as JSON, under a new ID
copy() {
  python -c "import csv,json,sys; r=next(r for r in csv.DictReader(open('data/complaints.csv',encoding='utf-8')) if r['complaint_id']==sys.argv[1]); r['complaint_id']=sys.argv[2]; print(json.dumps(r))" "$1" "$2"
}
# wait_done ID...: wait until the agent has decided each case
wait_done() {
  for id in "$@"; do until curl -s "$B/cases/$id" | grep -q '"status":"done"'; do sleep 1; done; echo "$id done"; done
}
# state ID: where a case is now (needs $MANAGER from section 2)
state() {
  curl -s "$B/api/cases/$1" -H "authorization: Bearer $MANAGER" | python -c "import sys,json; c=json.load(sys.stdin)['case']; print({k: c.get(k) for k in ('queue','workflow','sent','sensitive','assigned_to','waiting_reason')})"
}
# login USERNAME: prints a token
login() {
  curl -s -X POST "$B/api/auth/login" -H "content-type: application/json" -d "{\"username\":\"$1\",\"password\":\"teratai123\"}" | python -c "import sys,json; print(json.load(sys.stdin)['token'])"
}
```

**The test complaints.** Each action closes a case, so each test gets its own copy of a training complaint:

| IDs | Copy of | The agent decides | Used for |
|---|---|---|---|
| `$P-A1` … `$P-A7` | CMP-00244 | refund RM550.00, waits for approval (within the officer's RM2,000 limit) | approve, reject, edits, send back, sensitive, reassign |
| `$P-B1` | CMP-00023 | refund RM2,788.60, waits for approval (over the officer's limit) | escalate, second-tier approve |
| `$P-C1` | CMP-00001 | refund RM46.54, auto-resolved | acting on a closed case |
| `$P-F1`, `$P-F3` | CMP-00003 | unauthorised card RM1,404.18, fraud team | the fraud steps |
| `$P-F2` | CMP-00005 | scam transfer RM8,085.08, fraud team (over the analyst's RM5,000 limit) | fraud escalation |

## 1. Contract routes (no login)

These are the routes the organisers call. Their answers are the contract's short case view.

**`GET /health`**: the server is up.

```bash
call GET /health
```

Expect `HTTP 200  {"ok":true}`.

**`POST /complaints`**: hand the agent a complaint. Post all twelve test complaints and wait for the agent (about 5–20 s):

```bash
for pair in A1:CMP-00244 A2:CMP-00244 A3:CMP-00244 A4:CMP-00244 A5:CMP-00244 A6:CMP-00244 A7:CMP-00244 \
            B1:CMP-00023 C1:CMP-00001 F1:CMP-00003 F2:CMP-00005 F3:CMP-00003; do
  call POST /complaints "$(copy ${pair#*:} $P-${pair%%:*})"
done
wait_done $P-A1 $P-A2 $P-A3 $P-A4 $P-A5 $P-A6 $P-A7 $P-B1 $P-C1 $P-F1 $P-F2 $P-F3
```

Expect `HTTP 202  {"complaint_id":"T1-A1","status":"processing"}` for each, then `T1-A1 done` and so on.

Bad input:

```bash
call POST /complaints "$(copy CMP-00244 $P-A1)"     # the same complaint again
call POST /complaints '{"complaint_id":"X","customer_id":"CUS-02394","received_at":"2026-07-20 22:32"}'   # no text
```

Expect `HTTP 200  {"complaint_id":"T1-A1","status":"done"}` (no second case, no change), then `HTTP 422` with `"loc":["body","text"]`.

**`GET /cases/{id}`**: the agent's decision and where the case is.

```bash
call GET /cases/$P-A1
call GET /cases/NO-SUCH-CASE
```

Expect `HTTP 200` with `"outcome":"REFUND","refund_amount_myr":"550.00",...,"route":"HUMAN_APPROVAL"`, then `HTTP 404  {"detail":"unknown complaint NO-SUCH-CASE"}`.

**`POST /cases/{id}/actions`**: approve, reject, or edit and approve, with a typed name.

```bash
call POST /cases/$P-A1/actions '{"action":"edit_approve","actor":"Aina","reason":"friendlier","reply_text":"We will refund RM999.00 for TXN-0000001."}'
call POST /cases/$P-A1/actions '{"action":"approve","actor":"Aina","reason":"journal checked"}'
call POST /cases/$P-A1/actions '{"action":"approve","actor":"Aina"}'
call POST /cases/$P-A2/actions '{"action":"reject","actor":"Aina"}'
call POST /cases/$P-A2/actions '{"action":"reject","actor":"Aina","reason":"wrong transaction"}'
call POST /cases/$P-C1/actions '{"action":"approve","actor":"Aina"}'
```

| Step | Expect |
|---|---|
| edit with an invented amount and transaction | `HTTP 422`, `"edited reply fails the self-check; nothing was sent"` and the three problems |
| approve | `HTTP 200`; `GET /cases/$P-A1` now shows `"case_state":"approved","sent":true` |
| approve again (a double click) | `HTTP 409  {"detail":"T1-A1 is approved, not awaiting_approval"}` |
| reject without a reason | `HTTP 422  {"detail":"reason is required for reject"}` |
| reject with a reason | `HTTP 200`, `"case_state":"rejected","sent":false` |
| approve an auto-resolved case | `HTTP 409  {"detail":"T1-C1 is auto_resolved, not awaiting_approval"}` |

**`POST /cases/{id}/acknowledge`**: the fraud team sends the holding reply; the case stays with them.

```bash
call POST /cases/$P-F3/acknowledge '{"actor":"Farid","reason":"holding reply"}'
```

Expect `HTTP 200`, `"route":"FRAUD_TEAM"`, and `"sent":true` further on in the answer.

## 2. Login and reading

There are four users, all with the password `teratai123`: `officer1` and `officer2` (RM2,000 limit), `fraud1` (RM5,000), `manager1` (no limit). The platform actions need a token. Reads work without one while `AUTH_REQUIRED` is off, but the commands below send one anyway.

**`POST /api/auth/login`**:

```bash
OFFICER=$(login officer1); OFFICER2=$(login officer2); FRAUD=$(login fraud1); MANAGER=$(login manager1)
call POST /api/auth/login '{"username":"officer1","password":"wrong"}'
```

Expect no output from the first line, then `HTTP 401  {"detail":"wrong username or password"}`.

**`GET /api/auth/me`**, **`GET /api/users`**:

```bash
call GET /api/auth/me "" "$OFFICER"
call GET /api/users "" "$MANAGER"
call GET /api/users "" "$OFFICER"
```

Expect `HTTP 200` with officer1 (`"approval_limit_myr":"2000.00"`), `HTTP 200` with the user list, then `HTTP 403  {"detail":"manager only"}`.

**`GET /api/cases`**: the queues. Each role sees only its own team's cases.

```bash
call GET "/api/cases?queue=awaiting_approval&sort=recent&limit=3" "" "$OFFICER"
call GET "/api/cases?q=$P-&limit=20" "" "$MANAGER"
call GET "/api/cases?queue=nonsense" "" "$MANAGER"
```

Expect `HTTP 200` with `total`, `counts` and `items`; then `HTTP 200` with `"total":12` (all of this run's cases); then `HTTP 422` naming the allowed queues.

**`GET /api/cases/{id}`**: everything about one case: complaint, clues, match, decision, evidence, reply, audit trail.

```bash
call GET /api/cases/$P-A3 "" "$OFFICER"
call GET /api/cases/$P-F1 "" "$OFFICER"
```

Expect `HTTP 200` with `"queue":"awaiting_approval","waiting_reason":"Refund over RM500"`, then `HTTP 404`, because a fraud case is hidden from an officer.

**`GET /api/metrics`**, **`GET /api/audit`**:

```bash
call GET "/api/metrics?as_of=2026-09-30T16:30" "" "$MANAGER"
call GET "/api/audit?complaint_id=$P-A1" "" "$MANAGER"
```

Expect `HTTP 200` with `"cases":{"total":...}`, then `HTTP 200` with the case's events (`ingest`, `agent_run`, `edit_approve_refused`, `approve`).

## 3. Officer actions

The person acting comes from the token. Each action returns the full case, like `GET /api/cases/{id}`.

**`approve`**, **`edit-reply`**: an edited reply is checked, and approve stays locked while the edit fails.

```bash
call POST /api/cases/$P-A3/approve '{"reason":"x"}'
call POST /api/cases/$P-A3/edit-reply '{"reply_text":"We will refund RM999.00 for TXN-0000001.","reason":"friendlier"}' "$OFFICER"
call POST /api/cases/$P-A3/approve '{"reason":"checked"}' "$OFFICER"
GOOD=$(curl -s "$B/api/cases/$P-A3" -H "authorization: Bearer $OFFICER" | python -c "import sys,json; print(json.dumps(json.load(sys.stdin)['reply']['text']))")
call POST /api/cases/$P-A3/edit-reply "{\"reply_text\":$GOOD,\"reason\":\"back to the agent's text\"}" "$OFFICER"
call POST /api/cases/$P-A3/approve '{"reason":"checked"}' "$OFFICER"
state $P-A3
```

| Step | Expect |
|---|---|
| approve with no token | `HTTP 401  {"detail":"login required"}` |
| edit with an invented amount | `HTTP 200`: the draft is saved, flagged |
| approve | `HTTP 422`, `"the reply fails the self-check; nothing was sent"` |
| edit back to the agent's reply | `HTTP 200` |
| approve | `HTTP 200`, `"queue":"approved","sent":true` |

**`reject`**:

```bash
call POST /api/cases/$P-A4/reject '{}' "$OFFICER"
call POST /api/cases/$P-A4/reject '{"reason":"wrong transaction"}' "$OFFICER"
state $P-A4
```

Expect `HTTP 422  {"detail":"reason is required"}`, then `HTTP 200`, then `'queue': 'rejected', 'sent': False`.

**`send-back`**: the agent re-runs the case with the officer's note.

```bash
call POST /api/cases/$P-A5/send-back '{"note":"Customer says the ATM was at Miri Mall."}' "$OFFICER"
until state $P-A5 | grep -q "'workflow': None"; do sleep 1; done; state $P-A5
```

Expect `HTTP 202` with `"workflow":"reprocessing"` and `"waiting_reason":"Sent back: the agent is re-running it"`. A few seconds later: `'queue': 'awaiting_approval', 'workflow': None`. The re-run always waits for a person.

**`escalate`**: over the limit, the officer passes the case to the manager.

```bash
call POST /api/cases/$P-B1/approve '{"reason":"checked"}' "$OFFICER"
call POST /api/cases/$P-B1/escalate '{"reason":"over my limit"}' "$OFFICER"
state $P-B1
```

Expect `HTTP 403`, `"why":"refund RM2,788.60 is over your limit RM2,000.00"`; then `HTTP 200`; then `'workflow': 'escalated', 'waiting_reason': 'Escalated to the manager'`.

**`flag-sensitive`**: a sensitive case needs the manager, whatever the amount.

```bash
call POST /api/cases/$P-A6/flag-sensitive '{"reason":"customer is in hospital"}' "$OFFICER"
call POST /api/cases/$P-A6/approve '{"reason":"checked"}' "$OFFICER"
call POST /api/cases/$P-A6/escalate '{"reason":"sensitive case"}' "$OFFICER"
```

Expect `HTTP 200` with `"sensitive":true`, then `HTTP 403`, `"why":"sensitive: customer is in hospital"`, then `HTTP 200` with `"workflow":"escalated"`.

## 4. Manager actions

**`second-tier-approve`**, **`second-tier-reject`**: only the manager decides escalated cases.

```bash
call POST /api/cases/$P-B1/second-tier-approve '{"reason":"evidence checked"}' "$OFFICER"
call POST /api/cases/$P-B1/second-tier-approve '{"reason":"evidence checked"}' "$MANAGER"
state $P-B1
call POST /api/cases/$P-A6/second-tier-reject '{"reason":"call the customer first"}' "$MANAGER"
state $P-A6
```

Expect `HTTP 403  {"detail":"only the manager decides escalations"}`; `HTTP 200`; `'queue': 'approved', 'workflow': 'closed', 'sent': True`; `HTTP 200`; `'queue': 'rejected', 'workflow': 'closed', 'sent': False`.

**`reassign`**: only the assigned person (or the manager) can then act.

```bash
call POST /api/cases/$P-A7/reassign '{"username":"officer2","reason":"Daniel knows this customer"}' "$MANAGER"
call POST /api/cases/$P-A7/approve '{"reason":"checked"}' "$OFFICER"
call POST /api/cases/$P-A7/approve '{"reason":"checked"}' "$OFFICER2"
state $P-A7
```

Expect `HTTP 200` with `"assigned_to":"officer2"`; `HTTP 403  {"detail":"this case is assigned to officer2"}`; `HTTP 200`; `'queue': 'approved', 'assigned_to': 'officer2'`.

## 5. Fraud team actions

The order is acknowledge → investigate (any number of times) → record outcome.

**`acknowledge`**, **`investigate`**, **`record-outcome`**:

```bash
call POST /api/cases/$P-F1/acknowledge '{"reason":"holding reply sent"}' "$OFFICER"
call POST /api/cases/$P-F1/acknowledge '{"reason":"holding reply sent"}' "$FRAUD"
call POST /api/cases/$P-F1/investigate '{"note":"Card was chip+PIN at a petrol station","kind":"investigation"}' "$FRAUD"
call POST /api/cases/$P-F1/investigate '{"note":"Asked the merchant bank to hold the funds","kind":"recall_attempt"}' "$FRAUD"
call POST /api/cases/$P-F1/record-outcome '{"outcome":"maybe","reason":"x"}' "$FRAUD"
call POST /api/cases/$P-F1/record-outcome '{"outcome":"not_fraud","reason":"customer made the payment"}' "$FRAUD"
state $P-F1
```

| Step | Expect |
|---|---|
| acknowledge as the officer | `HTTP 403  {"detail":"this case belongs to another team"}` |
| acknowledge as the fraud analyst | `HTTP 200`, `"sent":true` (the holding reply) |
| investigate, twice | `HTTP 200` each |
| record a made-up outcome | `HTTP 422`, `"unknown outcome 'maybe'; use confirmed_fraud, not_fraud, recall_succeeded, recall_failed"` |
| record `not_fraud` | `HTTP 200`; then `'queue': 'with_fraud_team', 'workflow': 'closed'` |

**`escalate`** (fraud): over RM5,000 the analyst proposes an outcome and the manager decides.

```bash
call POST /api/cases/$P-F2/acknowledge '{"reason":"holding reply sent"}' "$FRAUD"
call POST /api/cases/$P-F2/record-outcome '{"outcome":"confirmed_fraud","reason":"mule account"}' "$FRAUD"
call POST /api/cases/$P-F2/escalate '{"reason":"over my limit","outcome":"confirmed_fraud"}' "$FRAUD"
call POST /api/cases/$P-F2/second-tier-approve '{"reason":"agree, mule account"}' "$MANAGER"
state $P-F2
call GET "/api/audit?people_only=true&limit=5" "" "$MANAGER"
```

Expect `HTTP 200`; `HTTP 403`, `"why":"disputed transaction RM8,085.08 is over your limit RM5,000.00"`; `HTTP 200` with `"waiting_reason":"Escalated to the manager"`; `HTTP 200`; `'workflow': 'closed'`; and the audit log with every person's action.

## All 24 endpoints

| Endpoint | Section | Main check |
|---|---|---|
| `GET /health` | 1 | 200 |
| `POST /complaints` | 1 | 202; repeat 200; no text 422 |
| `GET /cases/{id}` | 1 | 200; unknown 404 |
| `POST /cases/{id}/actions` | 1 | approve / reject / edit_approve; invented amount 422; double click 409 |
| `POST /cases/{id}/acknowledge` | 1 | 200, holding reply sent |
| `POST /api/auth/login` | 2 | token; wrong password 401 |
| `GET /api/auth/me` | 2 | the user |
| `GET /api/users` | 2 | manager 200; officer 403 |
| `GET /api/cases` | 2 | filtered by role; bad filter 422 |
| `GET /api/cases/{id}` | 2 | full detail; other team's case 404 |
| `GET /api/metrics` | 2 | 200 |
| `GET /api/audit` | 2, 5 | events, newest first |
| `POST /api/cases/{id}/approve` | 3 | 200; no token 401; over limit or sensitive 403; flagged draft 422 |
| `POST /api/cases/{id}/reject` | 3 | 200; no reason 422 |
| `POST /api/cases/{id}/edit-reply` | 3 | saved, with its self-check |
| `POST /api/cases/{id}/send-back` | 3 | 202, re-runs, then waits |
| `POST /api/cases/{id}/escalate` | 3, 5 | `workflow: escalated` |
| `POST /api/cases/{id}/flag-sensitive` | 3 | `sensitive: true` |
| `POST /api/cases/{id}/second-tier-approve` | 4, 5 | manager only (403 for others) |
| `POST /api/cases/{id}/second-tier-reject` | 4 | rejected, closed |
| `POST /api/cases/{id}/reassign` | 4 | only the assignee can act (403) |
| `POST /api/cases/{id}/acknowledge` | 5 | fraud team only (403 for others) |
| `POST /api/cases/{id}/investigate` | 5 | timeline entry |
| `POST /api/cases/{id}/record-outcome` | 5 | closed; over RM5,000 403; bad outcome 422 |

## Clean up

Stop the test server (Ctrl+C), then delete `backend/test_api.db`, `backend/test_api.db-wal` and `backend/test_api.db-shm`. Git ignores them, so they can't be committed by mistake. To run the steps again without deleting anything, change `P` (for example `P=T2`).
