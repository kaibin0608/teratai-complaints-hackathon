# Teratai Ops: frontend

The staff app for the Teratai complaints agent: queues, one case with its evidence and reply, approval and fraud steps, and the manager's console. React 19, TypeScript (strict), Vite, Tailwind CSS 4.

It builds only against the backend's UI contract, [`docs/UI_API.md`](../docs/UI_API.md). How cases move between people is in [`docs/USERFLOW.md`](../docs/USERFLOW.md); the screens and what each uses are in [`docs/FRONTEND_BUILD.md`](../docs/FRONTEND_BUILD.md).

## Run it

```bash
# Backend, from the repo root (see docs/UI_API.md for the one-time setup and filling it with cases)
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000     # or backend.bat

# Frontend
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Sign in as `officer1`, `officer2`, `fraud1` or `manager1` with password `teratai123`.

| Script | What |
|---|---|
| `npm run dev` | Dev server (proxies `/api` and `/complaints` to the backend) |
| `npm run build` / `npm run preview` | Typecheck and build / serve the build |
| `npm test` | Unit tests for the business rules |
| `npm run typecheck` / `npm run lint` | TypeScript / oxlint |

Settings (environment variables): `BACKEND_URL` (dev and preview proxy target, default `http://127.0.0.1:8000`), `VITE_API_URL` (call a backend directly instead of proxying), `VITE_DEMO_DATE` (the demo clock's date, default `2026-09-30`).

## Where things are

```
src/
├── api/          One module per backend resource; client.ts holds fetch, the token and ApiError
├── components/   layout (frame, sidebar, route guards) · shared (badges, buttons, fields, dialog)
│                 · case (the case page's cards) · case/actions (decision bar and dialogs)
│                 · queue · dashboard · charts · audit · intake
├── context/      Sign-in state
├── hooks/        Data loading (useApi: polling, cancellation), auth, demo clock
├── lib/          Business rules and formatting, no React: actions (who may do what), advance, replyCheck,
│                 money, sla, events, intake, csv, format, labels, types (mirror of UI_API.md)
├── pages/        One file per route
├── styles/       tokens.css (the Teratai colour system and the tunable spacing / radius / shadow)
└── test/         Fixtures for the tests
```

## Rules of the house

- **The backend decides; the UI explains.** Roles, limits and the self-check are enforced by the backend. The UI mirrors them (`lib/actions.ts`) to hide the wrong buttons and say why, and always handles the backend saying no.
- **Money is a string.** Format it with `formatMoney`; compare it with `compareMoney`. Never `parseFloat`.
- **Times are Malaysia time with no offset.** Parse by parts (`lib/format.ts`); never `new Date(string)`.
- **Colours come from `tokens.css`.** Tailwind's default palette is removed, so only the brand palette exists. Spacing, radius and shadow tokens are meant to be tuned in that one file.
- **Tailwind needs literal class names.** Don't build a class from pieces (`` `min-[${n}px]:hidden` `` generates nothing).
- **SLA timers run on the demo clock** (30 Sep 2026 at the current time of day), because the data is from the past.
