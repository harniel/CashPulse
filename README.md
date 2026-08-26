# CashPulse

Understand your money. Improve your future.

CashPulse is a full-stack household finance manager: shared visibility into joint expenses (rent, groceries) without forcing every transaction — one partner's salary, personal shopping — into a shared pool. Budgets, forecasts, and rule-based insights are computed deterministically from transaction history, not "AI."

See [BLUEPRINT.md](BLUEPRINT.md) for the full product spec, domain model, and phased build plan.

## Status

**Backend: all planned V1 work done** (BLUEPRINT.md §4/§27, Steps 1–14). **Frontend: underway** (Step 15) — app shell + Auth + Households + Accounts + Categories + Transactions + Budgets + Dashboard built and verified against the real backend in a browser (register → create accounts → record income/expense/transfer → confirm computed balances are correct → edit; create a budget → confirm every Dashboard stat/chart number by hand); 5 other feature areas still need a UI.

Backend modules, all with a working, tested API:

- **Auth** — custom email-based user, JWT with the refresh token in an httpOnly cookie, register/login/refresh/logout/me
- **Accounts** — CRUD, computed (not stored) balance
- **Categories** — system-seeded defaults + user-custom, one-level tree
- **Households** — membership, roles (Owner/Admin/Member), email invitations, leave/remove-member
- **Transactions** — income/expense/transfer, personal or household-shared, filtering, computed account balances
- **Budgets** — monthly per category, computed spent/remaining/utilization/daily-recommended-spend, historical performance
- **Dashboard** — one summary endpoint: net cash flow, savings rate, net worth, 4 chart series, 3 rule-based insight types
- **Recurring transactions** — idempotent generation engine (unique constraint, not convention), catch-up on missed periods, `skip-next`
- **Loans** — amortization schedule + extra-payment payoff simulation, Decimal-only math, computed remaining balance/projected payoff date
- **Savings goals** — target amount/date, computed progress, required monthly contribution, behind-pace warning; household-shareable
- **Forecasting** — trailing-N-month moving average projection, recurring transactions override the average for their own future month, explicitly labeled "not a guarantee"
- **CSV import** (transactions) — upload/parse/validate/duplicate-detect/confirm workflow, per-row audit trail, ±2-day fuzzy duplicate detection, type derived from amount sign
- **Excel import** (budgets) — fixed-header `.xlsx` upload/preview/confirm, downloadable template, upserts an existing budget by category+month instead of duplicating it
- **Notifications** — hourly rule sweep (budget/recurring/loan/goal), anti-spam dedup, in-app only
- **Audit logging** — retrofitted into transactions/budgets/loans/households, captures the actual actor (not just the entity owner), diff-based for updates, full snapshot for deletes

Frontend, built so far:

- **App shell** — routing, MUI theme, TanStack Query + Redux providers, protected/guest route wrappers
- **Auth** — register/login/logout with the access-token-in-memory + httpOnly-refresh-cookie pattern (§13), silent session restore on page reload
- **Households** — list, create, switch the active household via a top-bar switcher
- **Accounts** — CRUD, deactivate, computed balance displayed per account
- **Categories** — system category tree (income/expense, parent → child) + custom categories
- **Transactions** — income/expense/transfer, filtered by type/account, scoped by the active household switcher (personal vs. a specific shared household)
- **Budgets** — CRUD, progress bars colored by utilization threshold, plus an Excel import (download a template, upload, review a create/update preview per row with inline errors, confirm)
- **Dashboard** — stat cards (net cash flow, savings rate, net worth), rule-based insight alerts, and 4 live charts (cash flow, net worth, spending by category, budget utilization) via `@mui/x-charts`

Everything else backend-complete-but-no-UI-yet: Recurring, Loans, Savings, Forecasting, transaction CSV import, Notifications. See BLUEPRINT.md §27 for the phase-by-phase order.

**Docker Compose + CI**: backend + frontend Dockerfiles, full compose stack (backend/frontend/postgres/redis/celery), GitHub Actions (backend: ruff + pytest against real Postgres; frontend: oxlint + tsc + vitest; Docker build check for both images). **Verified with a real `docker compose up --build`**: all six containers start, migrations apply against the containerized Postgres, register/login and the frontend both work through the containers, and a Celery task dispatched via `.delay()` is picked up by the worker over containerized Redis and completes — plus the full 279-test backend suite (278 passing — one pre-existing, unrelated date-hardcoding test bug, see backend/README.md) passes directly against that Postgres. Still open: the GitHub Actions workflow hasn't run on GitHub's own runners yet (a real PR is the remaining check for the workflow file's mechanics, not the app itself).

## Stack

- **Backend:** Django + Django REST Framework, SQLite for local dev / PostgreSQL in Docker, JWT auth (`djangorestframework-simplejwt`), pytest + factory_boy for tests
- **Frontend:** React 19 + TypeScript (Vite), TanStack Query, Redux Toolkit (one slice), React Hook Form + zod, MUI, Vitest + React Testing Library + MSW (see BLUEPRINT.md §11–12)
- **Background jobs:** Celery + Redis wired up (app config, beat schedule, docker-compose services); no worker/beat process deployed yet — the recurring-transaction generator and notification sweep also run synchronously via management commands, no Redis needed

## Getting started

Backend setup/tests/endpoints: [backend/README.md](backend/README.md). Frontend setup/architecture: [frontend/README.md](frontend/README.md).

Without Docker — run each in its own terminal:

```bash
# backend
cd backend
python3 -m venv venv          # Python 3.10+
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate      # also seeds default categories
python manage.py createsuperuser
python manage.py runserver

# frontend
cd frontend
npm install
cp .env.example .env
npm run dev
```

Or with Docker (backend + frontend + Postgres + Redis + Celery worker/beat):

```bash
docker compose up --build
```

**Deploying**: backend on Railway, frontend on Vercel/Netlify — split,
since the frontend has nothing to run server-side. Full walkthrough (and
the monorepo gotcha to expect — Railway needs each service's Root
Directory set explicitly) in [backend/README.md](backend/README.md#deploying-railway)
and [frontend/README.md](frontend/README.md#deploying-vercel-or-netlify).

## Repository layout

```
backend/               Django + DRF API (see backend/README.md)
frontend/              React + TypeScript SPA (see frontend/README.md)
docker-compose.yml     Local dev/demo stack: backend, frontend, postgres, redis, celery
.github/workflows/     CI (backend + frontend lint/test, Docker build check)
BLUEPRINT.md           Full product spec, domain model, and phased roadmap
```
