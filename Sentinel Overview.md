# Sentinel Overview

> **AI oversight. Human judgment.**

This document explains what Sentinel is, who it is for, how it works, and how it is built. It is based on the source code in this repository.

---

## Contents

1. [What Sentinel is](#1-what-sentinel-is)
2. [The problem it addresses](#2-the-problem-it-addresses)
3. [Who uses it](#3-who-uses-it)
4. [Core concepts](#4-core-concepts)
5. [The six screens](#5-the-six-screens)
6. [The prioritization engine](#6-the-prioritization-engine)
7. [Decision rules and safety behaviors](#7-decision-rules-and-safety-behaviors)
8. [The sample data](#8-the-sample-data)
9. [State management and data flow](#9-state-management-and-data-flow)
10. [Keyboard shortcuts](#10-keyboard-shortcuts)
11. [Design system and theming](#11-design-system-and-theming)
12. [Tech stack](#12-tech-stack)
13. [Project structure](#13-project-structure)
14. [Running, building and deploying](#14-running-building-and-deploying)
15. [What is real and what is simulated](#15-what-is-real-and-what-is-simulated)

---

## 1. What Sentinel is

Sentinel is a **prototype of an oversight workspace for customer-support supervisors who review the work of AI agents**.

In the scenario Sentinel models, a company runs AI agents across three customer channels: **chat, email and voice**. Most interactions (about 92% in the sample data) are handled by the AI on its own, inside approved policy. A small share of interactions cannot be left to the AI alone, because they involve money, legal exposure, safety, privacy, vulnerable customers, or a low-confidence answer. Sentinel is where a human supervisor sees those cases, understands why each one was held back, and decides what happens next.

The product's stance is stated in the code itself: *the goal is the right level of oversight, not more of it.* That idea shapes the queue ordering, the policy-tuning screen, and the way AI confidence is deliberately played down.

It is a **front-end-only prototype**:

- All data is mocked and lives in TypeScript files.
- All decisions are held in memory. **Refreshing the page resets everything.**
- There is no backend, no authentication and no real AI.
- The in-code comments refer to a "case study" (sections such as §03, §04, §05, §06). The product was designed against a written case study, and the code cites its sections. The case study itself is not in this repository.

## 2. The problem it addresses

Putting AI agents in front of customers creates a new kind of work: someone has to supervise them. A naive approach fails in two ways.

| Failure mode | What goes wrong |
|---|---|
| **Too little oversight** | The AI promises a refund it should not, gives unsafe advice, or makes an irreversible change such as deleting data. |
| **Too much oversight** | Supervisors drown in routine approvals, start rubber-stamping, and customers wait longer than they should. |

Sentinel tries to address both. It routes only the cases that need a human to a queue, orders that queue in a way that cannot hide urgent work, gives the reviewer everything needed to decide quickly, and gives policy owners a way to tune the rules using evidence of how often reviewers disagree with the AI.

## 3. Who uses it

The app is built around one persona:

- **Jordan Lee, Support Ops Supervisor.** Shown in the sidebar and used as the reviewer on every decision made in the app (`CURRENT_REVIEWER` in `src/data/history.ts`).

Other people appear in the sample audit history and escalations (Marco Diaz, Sam Ortiz, Priya Shah), who act as other supervisors or specialists. There is no login and no role system. The Policies screen refers to a "policy owner" and to "Legal & Compliance" who own locked rules, but those are labels, not accounts.

## 4. Core concepts

### 4.1 Interactions and channels

An **interaction** is one customer conversation handled by an AI agent. It happens on one of three **channels**, and each gives the supervisor a different amount of time:

| Channel | Response window | Notes |
|---|---|---|
| **Chat** | Minutes | SLAs in the sample data range from 6 to 9 minutes. |
| **Email** | Hours | SLAs of 240 to 480 minutes. |
| **Voice** | Seconds | SLA of 3 minutes. The customer is **on hold** while the AI waits for approval. |

### 4.2 The three handling paths

Every interaction is evaluated against policy and risk and sent down one of three paths:

| Path | Meaning | Reaches a supervisor? |
|---|---|---|
| **Autonomous** | The AI proceeds within approved policy. | No. It never enters the queue. |
| **Human review** | The AI pauses before responding until a human approves. | Yes |
| **Restricted** | The AI's action is **blocked by policy** and the case must go to a specialist. | Yes, but a supervisor cannot approve it, only escalate or reject it. |

The Overview screen shows today's split: 1,176 autonomous, 94 human review and 14 restricted, out of 1,284 interactions.

### 4.3 Risk levels

Four levels: **critical, high, medium, low**. Risk colors are reserved for risk only: rose, orange, amber and gray.

### 4.4 Flags: the reasons a case needs a human

Each queued case carries one or more **flags**. A flag has a category, a title, a plain-language explanation and the **rule that fired** (for example `Refund auto-limit · $250`). The eight flag categories are:

`financial`, `legal`, `safety`, `vulnerability`, `sentiment`, `confidence`, `policy`, `privacy`.

### 4.5 Mandatory versus threshold-triggered review

A case reaches review for one of two reasons:

- **Mandatory.** A policy requires a human regardless of risk score (legal language, a vulnerable customer, card data, safety, irreversible actions).
- **Threshold-triggered.** A numeric limit was crossed, such as a refund over $250, a discount over 25%, sentiment below -0.6, or AI confidence below 75%.

### 4.6 The safe fallback

Every case has a **fallback**: the safe thing the system does if nobody acts in time. Examples from the data: *"Sends a formal acknowledgement and routes the case to Legal & Privacy"*, *"Processes the cancellation without a discount"*, *"The agent tells the customer a specialist will call back within 2 hours."* The fallback is shown on the case, in the Reject dialog and in the Escalate dialog, so the supervisor always knows what happens if they do nothing or reject the draft.

### 4.7 AI confidence

Each case has a confidence score from the AI. Sentinel shows it but **never uses it to order the queue**, and the UI states that it "doesn't make a response safe." A rule exists to *add* low-confidence cases to review, but the rule description is explicit that high confidence never takes a case out of review.

## 5. The six screens

Navigation is a sidebar on desktop and a slide-out drawer on mobile. The sidebar shows live counts: pending cases in the queue (red badge if any are critical) and escalations awaiting a specialist.

### 5.1 Overview (`/`)

The shift dashboard. It greets the reviewer by first name according to the time of day, and shows:

- **Five stat tiles:** Waiting for you (with a critical count), SLA at risk, Ageing cases (waiting over 45 minutes), Awaiting specialist, and Median review time (102 seconds in the sample data). Tiles link to the relevant screen.
- **Needs you now:** the top four cases in priority order, each with its risk, the plain-language reason for its position, the customer and a live SLA countdown.
- **How today's interactions were handled:** the autonomous / review / restricted split with counts and percentages.
- **By channel:** volume today, how many cases are waiting, the autonomous rate (93% chat, 90% email, 87% voice) and how long you have to respond.
- **Your decisions this shift:** counts of approved, edited, rejected and escalated decisions, plus a line such as "You changed or overruled the AI on X of Y". The code comment explains the purpose: if nearly everything is approved unchanged, the reviewer may be rubber-stamping, or the rules may be too strict.

A badge on the page states plainly: *"Sample data · illustrative, not measured results."*

### 5.2 Review queue (`/queue`)

The list of every pending case, grouped into three ordered **lanes** (see [section 6](#6-the-prioritization-engine)). Features:

- A **channel filter** (All / Chat / Email / Voice) and a **Restricted only** checkbox.
- A **Start with top case** button that opens the highest-priority case.
- Each row shows the channel, subject, risk badge, restricted badge, customer name, tier, intent, case ID, **why it is in this position**, an icon per flag, and optional badges: *Customer on hold*, *Possible duplicate*, *Ageing · Nm*, and *Last action failed*.
- On the right of each row: a live **SLA timer with a draining bar**, minutes waited and AI confidence.
- A colored strip on the left edge of each row shows its risk level.

### 5.3 Case review (`/queue/:caseId`)

The main working screen, where decisions are made. It is split into a header, three content areas and a decision bar.

**Header:** back link, subject, case ID, channel / risk / handling badges, a live SLA timer with bar, the position in the queue ("2 of 8"), and previous / next buttons.

**Left column, "what happened and who the customer is":**
- An AI-written **summary**, attributed to the named agent (Account Agent, Product Agent, Voice Agent, Billing Agent, Retention Agent).
- **Customer profile:** name, handle, tier (Standard / Plus / Enterprise), tenure, lifetime value, contacts in the last 30 days (highlighted at 3 or more), and a **sentiment meter** on a rose-to-green gradient.
- **Previous contacts**, collapsed by default so the current case leads.
- The **current conversation** as chat-style bubbles. System messages, such as "Customer placed on hold", appear as small notes.

**Right column:**
- **Case alerts**, most severe first (see [section 7.3](#73-exceptions-and-failure-states)).
- **Why this needs you:** the list of flags. **Hovering a flag highlights the exact words in the draft that triggered it**, and hovering highlighted draft text highlights the flag.
- **AI-proposed response:** the draft, stored as segments so risky spans are linked to flags and shown with numbered superscripts. Below it, **"If approved, the AI will also"** lists side effects such as issuing a refund or deleting data, marked **Irreversible** and/or **Blocked by policy**.
- **Evidence:** facts the decision depends on, each marked *Verified*, *Missing* or *Conflicting*, with its source. Gaps are shown first and verified facts are collapsed behind a toggle. Gaps are never hidden.
- **Policy guidance:** the relevant policy name and excerpt, plus "If nobody acts in time" (the fallback) and a de-emphasized AI confidence line.

**Decision bar (always in the same place and order):** **Reject**, **Escalate**, **Edit**, **Approve & send**. For voice cases, approve reads **Approve & say it**. See [section 7](#7-decision-rules-and-safety-behaviors) for how each works.

After any decision, the app shows a toast and automatically moves to the highest-priority remaining case. If none remain, it returns to the queue.

### 5.4 Escalations (`/escalations`)

A three-column board of cases handed to specialist teams: **Awaiting specialist**, **In progress**, **Resolved**. Each card shows the channel, case ID, risk, subject, customer, the receiving team, the supervisor's handoff note, the flags that fired, the owner (or who escalated it), and age. A card turns red and shows **"Overdue (Nh target)"** once its age exceeds the receiving team's response target.

Cards have a single action: **Assign to me** (moves to In progress) or **Mark resolved** (moves to Resolved and writes a `resolved` entry in the audit history). The page copy states the intent: each handoff includes the conversation, flags, evidence and the supervisor's note, "so nobody has to ask the customer again."

The five specialist teams:

| Team | Response target | Scope |
|---|---|---|
| Legal & Privacy | 24 h | Legal threats, data requests, regulators |
| Product Safety | 2 h | Injury, fire, recalls |
| Billing Specialists | 8 h | Tax, invoices, large refunds |
| Specialist Care | 4 h | Vulnerable and bereaved customers |
| Tier 2 Support | 1 h | Complex or repeat contacts |

### 5.5 Audit history (`/audit`)

A chronological, newest-first log of "every human decision on an AI response and its outcome: who decided, when, why, and exactly what changed." It includes:

- **Filter chips with counts:** All, Approved, Edited, Rejected, Escalated, Resolved, Action failed.
- Each row shows the time, channel, subject, risk, case ID, reviewer, reason (for rejections), destination team (for escalations) and an outcome badge.
- Rows **expand** to show the note, the actions that ran (or were attempted), and, for edits, a **side-by-side diff of the AI draft versus what was actually sent**.
- An **Export** button. In the prototype it only shows a toast ("Export queued"); it does not generate a file.

Outcomes recorded: `approved`, `edited`, `rejected`, `escalated`, `action_failed`, and `resolved` (the later outcome of an escalation, recorded alongside the original decision).

### 5.6 Policies (`/policies`)

Where supervisors tune the rules that decide which handling path each interaction takes. The page copy: *"Use reviewer outcomes to tune them, so humans review what matters and nothing more."*

Rules are in three groups:

| Group | Rules | Behavior |
|---|---|---|
| **Restricted** (owned by Legal & Compliance) | Product safety; Irreversible actions & data requests | AI actions are blocked and the case goes to a specialist. Locked. |
| **Mandatory review** | Legal language (locked); Vulnerable customers (locked); Payment card data (can be toggled) | Always paused for a human, whatever the AI's confidence. |
| **Review thresholds** | Refund auto-limit ($250, range $50 to $1000); Retention discount cap (25%, range 5 to 60%); Negative sentiment (-0.6, range -0.9 to -0.2); Low AI confidence (75%, range 50 to 95%) | Paused for a human only when a limit is crossed. Each has a slider and an on/off toggle. |

Each rule row shows how many **cases per day** it currently sends to humans, and its **reviewer override rate**: the share of its cases where reviewers changed or overruled the AI in the last 30 days. That drives a learning-loop hint:

- **Override rate of 40% or more:** "Often catches real problems" (keep it).
- **Below 10% and not locked:** "Rarely changes the outcome; could be loosened."
- Otherwise: no hint.

An **Impact preview** panel updates live as sliders move, showing total cases sent to humans per day and reviewer hours per day (at 2.5 minutes per review), with a note on the trade-off: fewer reviews are faster but let more decisions out unchecked; more reviews catch more edge cases but risk review fatigue and rubber-stamping.

**Reset** restores defaults and **Submit changes** shows a "Sent for approval" toast. Edits made here are local to the page and **do not change the queue or any case**.

## 6. The prioritization engine

Implemented in `src/lib/prioritization.ts`. The central design decision is that **risk, urgency, policy requirements and waiting time are deliberately not blended into one score**, because a blended score could let a stale low-risk case quietly outrank a mandatory one. Instead the queue is split into ordered lanes:

| Order | Lane | Who is in it | Sorting inside the lane |
|---|---|---|---|
| 1 | **Mandatory approval** | Cases where policy requires a human decision. Takes precedence over ordinary ranking. | Risk first (critical to low), then time left on SLA, then longest waiting. |
| 2 | **Critical risk** | Non-mandatory cases with critical risk. | Time left on SLA, then longest waiting. |
| 3 | **Ranked by urgency** | Everything else. | Time left on SLA, then longest waiting. |

Supporting rules:

- **Time left on SLA** = `(slaMinutes − waitingMinutes) × 60 − elapsedSeconds`. Timers tick live every second.
- **SLA state:** `overdue` when time is up, `soon` when less than 35% of the window remains, otherwise `ok`. These drive amber and rose coloring.
- **Overdue display:** the timer reads *"Fallback sent … ago"*, reflecting that the safe fallback would have run.
- **Ageing:** a case is flagged as ageing after **45 minutes** of waiting.
- **Position reason:** each case explains its place in plain language, such as "Required by policy · Legal language", "Critical risk" or "Threshold crossed · Refund auto-limit".
- **AI confidence is never used for ordering.**

## 7. Decision rules and safety behaviors

### 7.1 The four decisions

| Decision | What happens |
|---|---|
| **Approve & send** | The AI's response is sent and its non-blocked actions run. If the case has actions, a **confirmation dialog** first lists exactly what will happen and flags irreversible ones as "Can't be undone". A plain message with no actions is approved in one step to keep routine review fast. |
| **Edit** | Opens the draft in a text area. The supervisor sends an edited version. The original draft and the edited text are both kept in the audit log and shown as a diff. A hint reminds them: *editing only changes the message; if an action is wrong, reject or escalate instead.* "Reset to AI draft" is available. |
| **Reject** | The response is not sent and the **safe fallback applies**. A **structured reason is required** (Factually wrong, Breaks policy, Wrong tone, Missing something, Unsafe advice) plus an optional note. The code explains why: it completes the audit record and reveals patterns of incorrect AI handling over time. |
| **Escalate** | Hands the case to a specialist team. The supervisor picks a team (the system suggests one) and **must write a handoff note of at least 10 characters**. The dialog states what the specialist will receive: the conversation, flags, evidence and the AI's draft. |

### 7.2 When approval is blocked

A case cannot be approved when `approvalBlock` returns one of two reasons (`decision-rules.ts`):

- **`restricted`:** policy blocks the AI's action. The Approve button becomes a disabled, locked button and **Escalate becomes the primary action**. The tooltip reads: *"Restricted cases can't be approved. Escalate to a specialist."* Editing is also disabled.
- **`no_policy`:** no policy guidance exists for the situation, so the system cannot establish the action is permitted. It follows the safe fallback rather than proceed. The tooltip reads: *"No policy confirms this action is permitted, so it can't be approved."*

For restricted cases that name a required team, the escalation destination is **locked** to that team ("required by policy") and the Escalate button is labeled with it, for example "Escalate to Legal & Privacy". For other cases the team is chosen by `suggestTeam` (`routing.ts`): the policy-required team if there is one, otherwise by the first flag's category (legal and privacy go to Legal & Privacy, safety to Product Safety, vulnerability to Specialist Care, financial to Billing), otherwise Tier 2.

### 7.3 Exceptions and failure states

The case screen has dedicated alerts so the system never quietly proceeds when something is off:

| Situation | What the reviewer sees |
|---|---|
| **Last approval failed** | A rose alert: "The last approval failed. Nothing was sent to the customer," with the error and a **Retry** button. The queue row also shows "Last action failed". |
| **Restricted case** | A violet alert naming the required team and explaining that approval is unavailable. |
| **Live call, customer on hold** | A sky alert: the voice agent is waiting, and what happens if time runs out. |
| **No policy guidance** | An amber alert: this can't be approved; escalate or reject. |
| **Possible duplicate** | An amber alert naming the other open case and warning to check the refund was not already promised there. |
| **Missing or conflicting evidence** | Shown first in the Evidence panel, with a count of facts that could not be confirmed. |

### 7.4 Quiet design choices worth knowing

- Decisions are always in the **same place and order**.
- Toasts sit **above** the decision bar so they never cover the main action.
- Risk colors are used for risk only.
- Editing a draft never triggers a keyboard shortcut (shortcuts are ignored while typing).
- The case view is keyed by case ID, so edit state resets when moving between cases.

## 8. The sample data

All of it is hand-written to cover each path through the system and each failure state.

### 8.1 The eight queued cases

| ID | Channel | Subject | Risk | Handling | Mandatory | What it demonstrates |
|---|---|---|---|---|---|---|
| INT-4817 | Email | Formal complaint: data shared without consent | Critical | Restricted | Yes | A law firm alleges data sharing and requests GDPR erasure. The AI drafted a denial and proposes deleting the account. Identity not verified. **Required team: Legal & Privacy.** Deletion action is blocked and irreversible. |
| INT-4824 | Chat | Space heater sparked and scorched the carpet | Critical | Restricted | Yes | The AI promises a replacement and tells the customer they can keep using the unit. Unsafe guidance. **Required team: Product Safety.** Three similar reports on the same batch. |
| CALL-301 | Voice | Wants $4,800 early termination fee waived | High | Review | Yes | Live call, customer on hold, mentions legal action. The AI would waive 9.6 times the voice limit of $500. **No policy guidance found**, so approval is blocked. |
| INT-4809 | Email | Closing my late husband's account | High | Review | Yes | A bereaved customer who struggles with computers. The draft has no condolences and sends her to a complex portal. Demonstrates the vulnerability flag. |
| INT-4828 | Chat | Shared full card number in chat | Low | Review | Yes | The AI handled it correctly (redaction plus secure link), but PCI rules require human sign-off. Low risk yet mandatory. |
| INT-4821 | Chat | Double-charged for annual plan, wants a refund | Critical | Review | No | The draft refunds $480 when only $240 was duplicated (**conflicting evidence**), stacks a goodwill credit on a refund, and the customer threatens a chargeback. Also a **possible duplicate** of an open email case. |
| INT-4826 | Chat | Wants to cancel; AI offered a retention discount | Medium | Review | No | 40% discount against a 25% cap. **The first approval attempt fails** (simulated billing timeout) so the failure and retry flow can be shown. |
| INT-4813 | Email | Invoice shows the wrong VAT rate | Medium | Review | No | Confidence 58%. The EU VIES lookup was unavailable, so a key fact is **missing**. Has been waiting 84 minutes, so it is already ageing. |

In the default queue order, the five mandatory cases come first (sorted by risk, then SLA), then INT-4821 as the only non-mandatory critical case, then INT-4826 and INT-4813 ranked by time left.

### 8.2 Seed history

- **Seven audit entries** from earlier in the shift, covering every outcome type: an escalation and its later resolution (battery cover, Product Safety), an approved refund, an edited reply about wheelchair access (with a before/after diff), a regulator-threat escalation, a rejection for breaking policy, and a failed-then-retried coupon action.
- **Three escalations** seeded across the three board columns: one in progress (Legal & Privacy), one resolved (Product Safety), and one awaiting (Billing, a disputed $3,100 in usage overages).
- **Operational metrics** (`metrics.ts`): the daily path split, per-channel totals and autonomous rates, a 102-second median review time, and 2 SLA breaches today.

### 8.3 Timing

Mock timings are relative to when the page loads (`SESSION_START` in `useClock.ts`). Timers genuinely count down in real time. Leave a case alone long enough and it goes overdue.

## 9. State management and data flow

There is no store library. State is plain React context plus a reducer.

### 9.1 Provider stack

```
ThemeProvider → ToastProvider → SentinelProvider → RouterProvider
```

### 9.2 `SentinelProvider` (the app's domain state)

State held in a reducer (`sentinel-reducer.ts`):

| Field | Meaning |
|---|---|
| `decidedIds` | IDs of cases a supervisor has already decided. The pending queue is every interaction not in this list. |
| `failures` | Map of case ID to the last failed-action error message. |
| `audit` | The audit log (seeded, then new entries prepended). |
| `escalations` | The escalations board (seeded, then new escalations prepended). |

Actions handled by the reducer:

- **`decided`:** removes the case from the queue, writes an audit entry (including, for approved or edited decisions, the non-blocked actions that ran; and for edits, the before/after text), and, when the decision is an escalation, creates an `awaiting` escalation. Clears any recorded failure for that case.
- **`action_failed`:** records the error and writes an `action_failed` audit entry. The case **stays in the queue**.
- **`escalation_status`:** moves an escalation along. Resolving writes a `resolved` audit entry attributed to the owner.

Audit and escalation IDs are generated from an in-memory counter (`AUD-1208…`, `ESC-1208…`).

### 9.3 Simulated downstream failure

In `SentinelProvider.decide`, if a case is approved or edited and has a non-blocked action with a `failsWith` message, **the first attempt fails**, an error toast appears, and nothing is sent. Because a failure is now recorded for that case, the **second attempt succeeds**. This exists only to demonstrate the failure and retry states.

### 9.4 Derived and shared hooks

- `usePrioritizedQueue(filter?)` produces both the grouped lanes and a flat priority-ordered list, re-sorting every second as timers tick.
- `useCaseNavigation(caseId)` gives the current position, previous / next handlers, and `advance()`, which jumps to the highest-priority case that is not the one just decided.
- `useElapsedSeconds()` is a once-per-second clock shared by timers, SLA states and ageing.
- `useHotkeys(map, enabled)` binds single-key shortcuts.

### 9.5 Persistence

The only thing that persists across a refresh is the **theme choice**, stored in `localStorage` (wrapped in try/catch because storage can be blocked). On first visit the theme follows the operating system's light or dark preference. Everything else resets.

## 10. Keyboard shortcuts

Active on the case review screen when no dialog is open and the draft is not being edited. Ignored while typing in any input, and when Ctrl, Alt or Meta is held.

| Key | Action |
|---|---|
| `A` | Approve (opens the confirmation dialog if the case has actions) |
| `E` | Edit the draft |
| `R` | Reject (opens the dialog) |
| `X` | Escalate (opens the dialog) |
| `J` | Next case |
| `K` | Previous case |

Shortcut hints are displayed on the buttons. `A` and `E` do nothing on cases that cannot be approved. `Escape` closes the mobile navigation drawer.

## 11. Design system and theming

- **Fonts:** Inter for text and JetBrains Mono for IDs, timers and rules. The code names these fonts but does not load them, so they fall back to system fonts unless installed on the viewer's machine.
- **Components:** a small in-house UI kit in `src/components/ui` (Avatar, Badge, Button, Card, Dialog, EmptyState, PageHeader, Toggle) and shared domain badges in `src/components/shared` (ChannelBadge, HandlingBadge, RiskBadge, SlaTimer).
- **Icons:** `lucide-react`.
- **Visual language:** every enum (risk, channel, flag category, handling path, decision outcome) has its icon, label and color defined once in `src/lib/meta.ts`, so every screen uses the same visual vocabulary.
- **Dark mode:** a light / dark switch in the sidebar. Components use ordinary Tailwind color classes (`bg-white`, `text-zinc-900`, `bg-rose-50`), each backed by a CSS variable that is redefined under `.dark`, so no `dark:` variants are scattered through components. The color scale is read as "contrast with the surface" rather than literal lightness (in dark mode `zinc-900` is near-white text and `white` is the darkest surface). Status colors become low-chroma tints of their hue over the dark surface.
- **Brand color:** indigo.
- **Responsive layout:** desktop shows a fixed sidebar and a two-column case view; smaller screens get a top bar with a drawer menu and a stacked case view with a sticky decision bar.
- **Accessibility touches:** `prefers-reduced-motion` is respected, buttons have focus rings, tabs and radio groups use proper ARIA roles, alerts use `role="status"`, toasts sit in an `aria-live` region, and expandable sections use `aria-expanded`.

## 12. Tech stack

| Area | Choice |
|---|---|
| Language | TypeScript (strict, `~5.6`) |
| UI | React 18 |
| Routing | React Router 7 (`createBrowserRouter`) |
| Build tool | Vite 8 with `@vitejs/plugin-react` |
| Styling | Tailwind CSS 4 (via `@tailwindcss/vite`) plus a custom `tailwind.config.js` for theme variables |
| Icons | lucide-react |
| Hosting | Vercel (`vercel.json` rewrites all paths to `index.html` for client-side routing) |
| Runtime requirement | Node.js 18 or later |

The `@` path alias points to `src/`. There are no tests, no linter configuration and no backend dependencies in the repository.

## 13. Project structure

```
Sentinel/
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js        # theme variables, light/dark palettes
├── vercel.json               # SPA rewrite for deployment
├── public/favicon.svg
└── src/
    ├── main.tsx
    ├── index.css
    ├── app/
    │   ├── App.tsx           # provider stack
    │   └── router.tsx        # the six routes
    ├── types/index.ts        # the whole domain model
    ├── data/                 # mock data
    │   ├── interactions.ts   # the 8 queued cases
    │   ├── history.ts        # seed audit entries, escalations, current reviewer
    │   ├── policies.ts       # policy rules and reject reasons
    │   ├── teams.ts          # specialist teams
    │   └── metrics.ts        # shift numbers for the Overview
    ├── context/              # Sentinel (domain), Theme, Toast providers + reducer
    ├── hooks/                # useClock, useHotkeys, usePrioritizedQueue
    ├── lib/                  # prioritization, routing, meta, draft, format, cn
    ├── components/
    │   ├── layout/           # AppShell, Sidebar, Logo, ThemeSwitcher
    │   ├── shared/           # domain badges and SLA timer
    │   └── ui/               # generic UI primitives
    └── features/             # one folder per screen
        ├── overview/
        ├── queue/
        ├── review/           # components/, dialogs/, decision-rules.ts, useCaseNavigation.ts
        ├── escalations/
        ├── audit/
        └── policies/         # includes policy-impact.ts
```

Business logic is kept apart from components in small pure modules: `prioritization.ts` (lane and SLA logic), `routing.ts` (team suggestion), `decision-rules.ts` (approval blocking and confirmation) and `policy-impact.ts` (volume projection and override signals).

## 14. Running, building and deploying

```bash
npm install
npm run dev         # development server at http://localhost:5173
npm run build       # type-check, then production build into dist/
npm run preview     # serve the production build locally
npm run typecheck   # type-check only
```

To deploy, import the repository into Vercel at vercel.com/new and use the default settings. `vercel.json` already specifies the Vite framework, the build command, the `dist` output directory, and a rewrite that sends every path to `index.html` so deep links such as `/queue/INT-4821` work.

## 15. What is real and what is simulated

Being clear about this matters, because the UI looks like a finished product.

**Real, working behavior**
- Queue lane ordering, live SLA countdowns, SLA states and ageing.
- Hover linking between flags and highlighted draft text.
- Approve / edit / reject / escalate flows with validation (reject reason required, handoff note of 10+ characters, edited text non-empty), confirmation dialogs, and approval blocking.
- Audit log and escalation board updating from your decisions within a session, including edit diffs.
- The simulated failure-then-retry flow on INT-4826.
- Policy sliders and toggles with a live workload-impact estimate.
- Light and dark themes, with the choice remembered.
- Keyboard shortcuts and responsive layout.

**Simulated or stubbed**
- **All customer, case and metric data is invented.** The UI labels it "Sample data · illustrative, not measured results."
- **No AI exists.** Drafts, summaries, flags, confidence and evidence are static text.
- **No backend.** Nothing is sent to a customer; no refund, deletion or coupon actually runs.
- **Refreshing resets all decisions and escalations.**
- **Overdue cases do not disappear.** A case past its SLA just displays "Fallback sent … ago"; no fallback is actually executed.
- **Policy changes are local to the Policies page.** They do not alter which cases are in the queue. "Submit changes" only shows a toast.
- **Export** on the Audit page only shows a toast.
- **Policy impact numbers are a rough linear model**, which the code describes as "good enough to show the direction and scale of a trade-off, not a forecast."
- **There is no authentication.** Every action is attributed to Jordan Lee.
