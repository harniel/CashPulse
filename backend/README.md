# Smart Household Finance Manager — Backend (Phase 1, Steps 1–2)

Django + DRF backend. Covers so far: custom email-based user model, JWT
auth with the refresh token in an httpOnly cookie, Accounts, and
Categories (system-seeded + user-custom, one-level tree) — plus a test
suite proving cross-user isolation on every resource.

## Setup — local dev (SQLite, no Docker/Postgres needed)

```bash
python3 -m venv venv               # use Python 3.10+; 3.9 can't install Django 6.x
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

This repo already includes a working local-dev `.env` (SQLite, no
Postgres vars) — you don't need to copy `.env.example` over it. `.env.example`
is a *template for the eventual Docker Compose setup* (Section 21 of the
blueprint), with `DB_HOST=db` pointing at a Compose service name that
doesn't exist outside Docker. Copying it over your local `.env` will
break `migrate` with a "could not translate host name db" error — if
that happens, just restore `.env` to the SQLite version above.

```bash
python manage.py migrate           # also seeds default categories
python manage.py createsuperuser
python manage.py runserver
```

## Tests

```bash
pytest -v
```

41 tests, all passing:
- **users** (16): registration, login (incl. the generic-error check
  that prevents email enumeration), refresh-token rotation +
  blacklist-on-reuse, logout blacklisting, `/me/` isolation.
- **accounts** (11): CRUD, server-side ownership (client can't set
  `user` in the payload), duplicate-name rejection, and cross-user
  isolation on retrieve/update/delete (all return 404, not 403 — the
  API never confirms another user's record exists).
- **categories** (14): seed-data checks against the real migration,
  the one-level tree constraint, parent/child kind matching, system
  categories being read-only via the API, and the same cross-user
  isolation pattern as accounts.

## Endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/auth/register/` | — | Returns `access` + sets `refresh_token` cookie |
| POST | `/api/auth/login/` | — | Throttled 10/min |
| POST | `/api/auth/refresh/` | refresh cookie | Rotates + blacklists old refresh token |
| POST | `/api/auth/logout/` | Bearer access | Blacklists refresh token, clears cookie |
| GET | `/api/auth/me/` | Bearer access | Current user only |
| GET/POST | `/api/accounts/` | Bearer access | List/create; filter by `account_type`, `is_active`; search `name`, `institution` |
| GET/PATCH/DELETE | `/api/accounts/{id}/` | Bearer access | Owner only — 404 otherwise |
| GET/POST | `/api/categories/` | Bearer access | Returns own + system categories; filter by `kind`, `is_system`, `parent` |
| GET/PATCH/DELETE | `/api/categories/{id}/` | Bearer access | System categories are readable but not writable (403 on write) |

## Architecture notes worth knowing

- `common/viewsets.py::OwnedModelViewSet` is the base class every
  user-owned resource inherits from — it's the single choke point for
  "you can only ever see your own data," so a future app can't forget
  to filter its queryset. `CategoryViewSet` doesn't inherit it because
  categories are user-owned *or* system-shared (an OR, not a plain
  equality filter) — see the comment in `categories/views.py`.
- Accounts have no stored `balance` — see the docstring in
  `accounts/models.py`. That field arrives once Transactions exist and
  balance can be computed, not stored.

## What's next (Phase 1, step 3)

Transactions app (income/expense/transfer) — see `/BLUEPRINT.md` in
the project root for the full phased plan.
