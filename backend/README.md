# Smart Household Finance Manager — Backend (Phase 1, Steps 1–3)

Django + DRF backend. Covers so far: custom email-based user model, JWT
auth with the refresh token in an httpOnly cookie, Accounts, Categories
(system-seeded + user-custom, one-level tree), and Households (membership,
roles, email invitations) — plus a test suite proving cross-user/cross-
household isolation on every resource.

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

66 tests, all passing:
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
- **households** (25): membership-scoped visibility (404 for non-members),
  role-gated rename/delete/invite/remove-member, owner-can't-be-removed,
  leave-household (incl. sole-owner-leaving deletes the household, and
  owner-with-other-members can't leave without transferring first),
  invitation lifecycle (invite/re-invite, accept/decline, email-mismatch
  rejection, expiry).

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
| GET/POST | `/api/households/` | Bearer access | List households you're a member of; create makes you Owner |
| GET/PATCH/DELETE | `/api/households/{id}/` | Bearer access | Member-only 404; rename needs Admin+, delete needs Owner |
| GET | `/api/households/{id}/members/` | Bearer access, member | List members + roles |
| DELETE | `/api/households/{id}/members/{user_id}/` | Bearer access, Admin+ | Can't remove the Owner |
| GET/POST | `/api/households/{id}/invitations/` | Bearer access, Admin+ | POST invites by email; re-inviting refreshes the pending invite |
| POST | `/api/households/{id}/leave/` | Bearer access, member | Sole owner leaving deletes the household; owner with co-members must transfer first |
| POST | `/api/invitations/{token}/accept/` | Bearer access | 403 if the token's email doesn't match the authenticated user |
| POST | `/api/invitations/{token}/decline/` | Bearer access | Same email check as accept |

## Architecture notes worth knowing

- `common/viewsets.py::OwnedModelViewSet` is the base class every
  user-owned resource inherits from — it's the single choke point for
  "you can only ever see your own data," so a future app can't forget
  to filter its queryset. `CategoryViewSet` doesn't inherit it because
  categories are user-owned *or* system-shared (an OR, not a plain
  equality filter) — see the comment in `categories/views.py`. Households
  use their own membership-scoped `get_queryset()` for the same reason —
  ownership isn't the right relation there, membership is.
- `households/permissions.py::HouseholdRolePermission(minimum_role)` is a
  factory, not a plain permission class — DRF instantiates
  `permission_classes` with no arguments, so parameterizing "how senior a
  role is required" (Owner/Admin/Member) needs a closure. It's the second,
  narrower gate on top of the membership-scoped queryset.
- `households/services.py` owns the business logic (invite/accept/decline,
  remove-member, leave) per the blueprint's "services, not views or
  serializers" rule — views stay thin, calling into services and letting
  DRF's exception handling turn `PermissionDenied`/`ValidationError`/
  `NotFound` into the right status code.
- Accounts have no stored `balance` — see the docstring in
  `accounts/models.py`. That field arrives once Transactions exist and
  balance can be computed, not stored.

## What's next (Phase 1, step 4)

Transactions app (income/expense/transfer, personal/shared via the
`household` FK) — see `/BLUEPRINT.md` in the project root for the full
phased plan.
