# Submission checklist (deadline: 15:00 on Day 2)

The organisers' rules ([README.md](../README.md) "Submitting") are:
- a pull request to `DM-Data-Science/teratai-complaints-hackathon`, titled **`Submission: Santa_Claude`**
- it adds **only** `submissions/Santa_Claude/predictions.csv`
- the description gives the **repo link**, the **freeze commit hash** and the **API URL**

**The file in the PR is locked at 15:00**; a file pushed later isn't scored. The hidden test calls the API URL right after 15:00.

## What's already prepared

| Item | Status |
|---|---|
| Submission branch `submission/Santa_Claude` on the fork | ✅ pushed. It adds only `submissions/Santa_Claude/predictions.csv` |
| The file | ✅ identical to `dev`'s, which matches the current code. 750 rows, every test ID once, valid columns, no empty replies |
| The API on the venue Wi-Fi | ✅ `http://10.0.30.131:8000`; `api_check` passed from a teammate's laptop |
| The pull request | ❌ **not opened yet**: that's the actual submission |

## Step 1: open the PR early (13:00–14:00), not at 14:59

1. Logged in to GitHub as `kaibin0608`, open:
   **https://github.com/DM-Data-Science/teratai-complaints-hackathon/compare/main...kaibin0608:teratai-complaints-hackathon:submission/Santa_Claude**
2. Check the bar at the top:
   - **base repository** `DM-Data-Science/teratai-complaints-hackathon`, base `main`
   - ← **head repository** `kaibin0608/teratai-complaints-hackathon`, compare `submission/Santa_Claude`
3. Check **Files changed** shows **exactly 1 file**: `submissions/Santa_Claude/predictions.csv`.
4. Click **Create pull request**. Title: **`Submission: Santa_Claude`**. Paste the description below; the hash gets filled in at step 2.

```markdown
**Team:** Santa_Claude
**Repo:** https://github.com/kaibin0608/teratai-complaints-hackathon
**Freeze commit hash:** <fill in at 14:50: `git rev-parse main`>
**API URL:** http://10.0.30.131:8000

Adds `submissions/Santa_Claude/predictions.csv` (750 test complaints).
```

## Step 2: freeze at about 14:50

1. **Stop changing the agent and API.** No more backend commits for scoring.
2. **Merge `dev` → `main` and push:**

   ```bash
   git switch main
   git merge --ff-only dev
   git push origin main
   git switch dev
   ```

   In GitHub Desktop: switch to `main` → Branch → Merge into current branch → `dev` → Push. Commit or stash any open changes first.
3. **Get the freeze hash:** `git rev-parse main`, the full 40-character hash.
4. **Edit the PR description:** replace the hash placeholder.
5. **Re-check the API URL.** From a teammate's laptop: `http://10.0.30.131:8000/health` shows `{"ok":true}`, or run `python scoring/api_check.py http://10.0.30.131:8000`. If the laptop's Wi-Fi address changed (`ipconfig`), put the new URL in the PR.

## If predictions change before 15:00

Regenerate on `dev` ([RUNNING.md](RUNNING.md) section 6), then copy the new file onto the submission branch and push. The open PR updates by itself:

```bash
git switch submission/Santa_Claude
git checkout dev -- submissions/Santa_Claude/predictions.csv
git commit -m "Submission: Santa_Claude (updated predictions)"
git push origin submission/Santa_Claude
git switch dev
```

Check **Files changed** still shows only that one file. After 15:00, nothing changes the score.

## From 15:00 until the end of the demo

- **Keep the server running** (`backend.bat` window open) and the laptop **plugged in and awake**.
- **15:00–15:45:** the organisers run the hidden test (20 complaints at once). **Don't** restart the server, load data, run `api_check` or batch runs.
- **Don't push agent or backend changes.** UI and ops-platform work can continue until 16:30.
- Make sure there's **enough LLM quota** (OpenRouter credit) for 20 complaints at once, plus the demo.

## If the PR can't be opened

Send the organisers the four things before 15:00:
- the `predictions.csv` file
- the repo link
- the freeze commit hash
- the API URL

They'll load them themselves.
