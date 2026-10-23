# Running the system

How to start, check, fill and recover the backend, for anyone on the team. Every command runs from the repo folder. On Windows use PowerShell or Git Bash; the commands are the same.

**Day 2 at a glance**
- **12:00 Checkpoint 2:** the server is running and reachable, and `api_check` passes.
- **15:00 freeze:** `predictions.csv` is final, and the server must be **running and reachable**. The organisers' hidden test calls it right after 15:00.
- **15:00 until the end of your demo:** keep the server running and the laptop awake and plugged in.
- **16:30 demos:** the judges send 3 complaints to the same server and watch them in the UI.

## 1. One-time setup

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt        # macOS/Linux: .venv/bin/pip
```

Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`. **Never commit `.env`; the repo is public.** The models already chosen in `.env.example` are:

| Setting | Value | Why |
|---|---|---|
| `LLM_EXTRACT` | `openrouter:deepseek/deepseek-v4-flash` | Reads the complaint. Compared with 3 other models: same accuracy ([EXTRACTOR_RESULTS.md](EXTRACTOR_RESULTS.md#extraction-model-comparison-2026-10-23)) |
| `LLM_DRAFT` + `LLM_DRAFT_REASONING=none` | `openrouter:anthropic/claude-haiku-5.5` | Writes the reply |
| `LLM_ISSUES` (empty) + `LLM_ISSUES_REASONING=none` | follows `LLM_EXTRACT` | The second-issue check |
| `AUTH_REQUIRED` | `false` | `true` makes every `/api` read need a login (turn it on for the bonus demo) |
| `JWT_SECRET` | a long random string | Signs login tokens; the server warns if it's left at the development key |

With no `.env` at all, everything runs on the free offline **fake** models (keyword reader, code-written replies). That's fine for UI work, not for the real run.

## 2. Start the server

**Double-click `backend.bat`**, or:

```bash
.venv\Scripts\python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

- `--host 0.0.0.0` lets other laptops (the organisers, the UI) reach it.
- The window must stay open. Closing it, or pressing Ctrl+C, stops the server.
- At startup the server checks the model config and refuses to start if a key is missing. It loads the data, creates the demo users, and re-queues any complaint that was still processing when it stopped.
- It keeps its cases in `backend/api.db` (separate from the batch database `backend/teratai.db`).

**Laptop settings for Day 2:** set sleep to "never" while plugged in, and turn off Windows Update restarts for the day.

## 3. Make it reachable (Checkpoint 2, hidden test, demo)

**Option A: venue Wi-Fi (in use; passed from a teammate's laptop on Day 2).**
1. Find the laptop's address: `ipconfig` → "IPv4 Address" under Wi-Fi (Day 2: `10.0.30.131`).
2. The URL is `http://<that-address>:8000`. Test from another device on the same Wi-Fi: `http://<address>:8000/health` must show `{"ok":true}`.
3. If other devices can't connect, allow the port in Windows Firewall. In PowerShell **as administrator**:

   ```powershell
   New-NetFirewallRule -DisplayName "Teratai API 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any
   ```

**Option B: tunnel (if the Wi-Fi blocks laptop-to-laptop traffic, or the address keeps changing).** It gives a public `https://` URL and needs no firewall change.
- **Cloudflare:** install `cloudflared`, then run `cloudflared tunnel --url http://localhost:8000`. It prints a `https://….trycloudflare.com` URL. Keep that window open too.
- **ngrok:** `ngrok http 8000` (needs a free account and token).

**The URL changes** if the Wi-Fi address changes or the tunnel restarts. Re-check it before 15:00, and use the final one in the submission PR.

## 4. Check it's healthy

```bash
curl http://127.0.0.1:8000/health                                        # {"ok":true}
.venv\Scripts\python scoring/api_check.py http://127.0.0.1:8000          # the organisers' test: expect 100.0, 9/9 probes
.venv\Scripts\python scoring/api_check.py http://127.0.0.1:8000 --n 20 --no-probes   # 20 at once, like the hidden test
.venv\Scripts\python scoring/api_check.py http://127.0.0.1:8000 --complaints backend/eval/messy/complaints_messy.csv --labels backend/eval/messy/labels_messy.csv --all --no-probes   # messy text
```

- Run `api_check` against the **real URL from another laptop** too (that's what the organisers do).
- Use `127.0.0.1` rather than `localhost` on Windows; `localhost` adds about 0.2 s per call.
- Interactive API docs: `http://127.0.0.1:8000/docs`.

## 5. Fill the demo database

The server starts with only what's been posted to it. To give the queues and dashboard real numbers for the demo, add the 750 test complaints. The answers come from the LLM cache, so it's free and takes about a minute:

```bash
.venv\Scripts\python -m backend.batch.runner --ids test --db backend/api.db
```

- It can run while the server is up; new cases appear on the next poll.
- **Don't run it while `api_check` or the hidden test is running.**
- For a quicker small set: `--ids pilot` (50 complaints).
- To start the API database empty: stop the server, delete `backend/api.db` (and any `api.db-wal` / `api.db-shm`), start it again.

## 6. Regenerate and check the submission

After any change to the engine, a prompt or a model:

```bash
.venv\Scripts\python -m backend.batch.runner --ids test --rerun                   # re-run the 750; only changed replies are redrafted
.venv\Scripts\python -m backend.batch.submit --ids test --strict                  # writes submissions/<TEAM_NAME>/predictions.csv, refuses if any row is invalid
.venv\Scripts\python -m backend.batch.runner --ids train --no-draft               # training run (no replies)
.venv\Scripts\python -m backend.batch.submit --ids train --score                  # training score (currently 100.00)
```

- The runner warns if any complaint fell back after an LLM error (`llm_error`). Re-run with `--rerun` until there are none.
- The submission file must have exactly 750 valid rows; `--strict` guarantees it.
- After regenerating, commit `predictions.csv`.

## 7. When something goes wrong

| Problem | What to do |
|---|---|
| The server won't start: "Config error" | A key is missing or a model name is wrong in `.env`. Read the message |
| The server won't start: port 8000 in use | Another server is already running. Close the other window, or find it with `Get-NetTCPConnection -LocalPort 8000` |
| The AI provider is down or slow | Nothing to do: extraction falls back to the keyword reader, replies to the code-written reply, and the case is held for a person (`llm_error`). Nothing goes out wrongly |
| The second-issue check misbehaves | Set `LLM_ISSUES=off` in `.env` and restart. Cases then behave exactly as before it existed |
| A case is stuck in `processing` after a crash | Restart the server; it re-queues them |
| A case is stuck in `reprocessing` (send back) after a crash | Restart; it goes back to its queue with a `send_back_failed` event |
| The organisers can't reach the URL | Test `/health` from another device; then the firewall rule (section 3), or switch to a tunnel and send them the new URL |
| The laptop fails completely | Another laptop: clone, set up (section 1) with the same `.env` key, start (section 2), make it reachable (section 3), send the organisers the new URL |
| Switching branches in GitHub Desktop "lost" work | Desktop stashes uncommitted changes on a switch. Switch back, or restore them from the stash list. Commit before switching |

## 8. Logins for the bonus platform

There are four demo users, all with the password `teratai123`:

| User | Role | Limit |
|---|---|---|
| `officer1` | Complaints officer | RM2,000 |
| `officer2` | Complaints officer | RM2,000 |
| `fraud1` | Fraud analyst | RM5,000 (disputed transaction) |
| `manager1` | Manager | none |

The UI logs in with `POST /api/auth/login` ([UI_API.md](UI_API.md#login-roles-and-the-platform-actions)). The organisers' contract routes never need a login.

## 9. Submission (before 15:00)

1. The final `predictions.csv` is committed on `dev` (section 6).
2. Merge `dev` → `main`.
3. Open a PR from the fork to upstream, titled **`Submission: Santa_Claude`**, with `submissions/Santa_Claude/predictions.csv`. In the description put the **freeze commit hash** (`git rev-parse HEAD` on `main`) and the **API URL** (section 3).
4. Leave the server running.
