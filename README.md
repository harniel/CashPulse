# CashPulse

Understand your money. Improve your future.

CashPulse is a full-stack household finance manager: shared visibility into joint expenses (rent, groceries) without forcing every transaction — one partner's salary, personal shopping — into a shared pool. Budgets, forecasts, and rule-based insights are computed deterministically from transaction history, not "AI."

See [BLUEPRINT.md](BLUEPRINT.md) for the full product spec, domain model, and phased build plan.

## Status

Backend only. **All planned backend V1 work is done** (BLUEPRINT.md §4/§27, Steps 1–14) — only the frontend and docs polish remain:

- **Auth** — custom email-based user, JWT with the refresh token in an httpOnly cookie, register/login/refresh/logout/me
- **Accounts** — CRUD, computed (not stored) balance
- **Categories** — system-seeded defaults + user-custom, one-level tree
- **Households** — membership, roles (Owner/Admin/Member), email invitations, leave/remove-member
- **Transactions** — income/expense/transfer, personal or household-shared, filtering, computed account balances
- **Budgets** — monthly per category, computed spent/remaining/utilization/daily-recommended-spend, historical performance
- **Dashboard** — one summary endpoint: net cash flow, savings rate, net worth, 4 chart series, 3 rule-based insight types
- **Recurring transactions** — idempotent generation engine (unique constraint, not convention), catch-up on missed periods, `skip-next`; Celery beat wired but no worker/beat process running yet
- **Loans** — amortization schedule + extra-payment payoff simulation, Decimal-only math, computed remaining balance/projected payoff date
- **Savings goals** — target amount/date, computed progress, required monthly contribution, behind-pace warning; household-shareable
- **Forecasting** — trailing-N-month moving average projection, recurring transactions override the average for their own future month, explicitly labeled "not a guarantee"
- **CSV import** — upload/parse/validate/duplicate-detect/confirm workflow, per-row audit trail, ±2-day fuzzy duplicate detection, type derived from amount sign
- **Notifications** — hourly rule sweep (budget/recurring/loan/goal), anti-spam dedup, in-app only
- **Audit logging** — retrofitted into transactions/budgets/loans/households, captures the actual actor (not just the entity owner), diff-based for updates, full snapshot for deletes
- **Docker Compose + CI** — backend Dockerfile (dev/prod stages), compose stack (backend/postgres/redis/celery), GitHub Actions (ruff + pytest against real Postgres + Docker build check); no frontend service/job yet since there's no frontend code to run. **Unverified end-to-end** — this sandbox has neither Docker nor a local Postgres, so this is built-and-inspected, not run; see backend/README.md's Docker & CI section

Only the frontend (Step 15) and docs polish (Step 16) remain — see BLUEPRINT.md §27 for the phase-by-phase order.

## Stack

- **Backend:** Django + Django REST Framework, SQLite for local dev / PostgreSQL in Docker, JWT auth (`djangorestframework-simplejwt`), pytest + factory_boy for tests
- **Frontend:** not started yet — planned as React + TanStack Query + Redux Toolkit (one slice) + React Hook Form + MUI (see BLUEPRINT.md §11–12)
- **Background jobs:** Celery + Redis wired up (app config, beat schedule, docker-compose services); no worker/beat process deployed yet — the recurring-transaction generator and notification sweep also run synchronously via management commands, no Redis needed

## Getting started

Backend setup, tests, and endpoint reference live in [backend/README.md](backend/README.md). Quick start (no Docker):

```bash
cd backend
python3 -m venv venv          # Python 3.10+
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate      # also seeds default categories
python manage.py createsuperuser
python manage.py runserver
```

Or with Docker (backend + Postgres + Redis + Celery worker/beat):

```bash
docker compose up --build
```

## Repository layout

```
backend/               Django + DRF API (see backend/README.md)
docker-compose.yml     Local dev/demo stack (no frontend service yet)
.github/workflows/     CI (backend lint + test + Docker build check)
BLUEPRINT.md            Full product spec, domain model, and phased roadmap
```
