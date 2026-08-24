# CashPulse

Understand your money. Improve your future.

CashPulse is a full-stack household finance manager: shared visibility into joint expenses (rent, groceries) without forcing every transaction — one partner's salary, personal shopping — into a shared pool. Budgets, forecasts, and rule-based insights are computed deterministically from transaction history, not "AI."

See [BLUEPRINT.md](BLUEPRINT.md) for the full product spec, domain model, and phased build plan.

## Status

Backend only, early phase. Built so far:

- **Auth** — custom email-based user, JWT with the refresh token in an httpOnly cookie, register/login/refresh/logout/me
- **Accounts** — CRUD, computed (not stored) balance
- **Categories** — system-seeded defaults + user-custom, one-level tree

Everything else (households, transactions, budgets, recurring transactions, loans, savings goals, forecasting, CSV import, notifications, audit log, frontend, Docker/CI) is planned — see BLUEPRINT.md §27 for the phase-by-phase order.

## Stack

- **Backend:** Django + Django REST Framework, SQLite for local dev / PostgreSQL in Docker, JWT auth (`djangorestframework-simplejwt`), pytest + factory_boy for tests
- **Frontend:** not started yet — planned as React + TanStack Query + Redux Toolkit (one slice) + React Hook Form + MUI (see BLUEPRINT.md §11–12)
- **Background jobs (planned):** Celery + Redis

## Getting started

Backend setup, tests, and endpoint reference live in [backend/README.md](backend/README.md). Quick start:

```bash
cd backend
python3 -m venv venv          # Python 3.10+
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate      # also seeds default categories
python manage.py createsuperuser
python manage.py runserver
```

## Repository layout

```
backend/   Django + DRF API (see backend/README.md)
BLUEPRINT.md  Full product spec, domain model, and phased roadmap
```
