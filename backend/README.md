# Smart Household Finance Manager — Backend (Phase 1, Steps 1–14 — all backend V1 work done)

Django + DRF backend, complete through every backend step the blueprint's
V1 phase plan lists (Steps 1–14; only the frontend and docs-polish steps
remain). Covers: custom email-based user model, JWT auth with the refresh
token in an httpOnly cookie, Accounts (computed balance), Categories
(system-seeded + user-custom, one-level tree), Households (membership,
roles, email invitations), Transactions (income/expense/transfer,
personal/shared), Budgets (monthly, computed spent/remaining/utilization/
daily-recommended-spend), a Dashboard summary (net cash flow, savings
rate, net worth, 4 chart series, rule-based insights), Recurring
transactions (idempotent generation engine + Celery beat), Loans
(amortization schedule + extra-payment payoff simulation), Savings goals
(progress, required monthly contribution, behind-pace warning), a
Forecasting engine (trailing-average projection, recurring-aware),
Transaction CSV import (upload/validate/duplicate-detect/confirm) and
Budget .xlsx import (fixed-header upload/preview/confirm, upserts
existing budgets by category+month instead of erroring), Notifications (hourly
rule sweep, anti-spam dedup), Audit logging (actor-aware, retrofitted
across services), and Docker Compose + CI — plus a test suite proving
cross-user/cross-household isolation on every resource. See
`/BLUEPRINT.md` for the full phased plan and what's still ahead (frontend,
docs polish).

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

Celery/Redis are only needed to actually *run* the recurring-transaction
generator asynchronously — `runserver`, `migrate`, and `pytest` never
contact Redis. To generate due recurring transactions locally without
Redis at all:

```bash
python manage.py generate_recurring_transactions
```

## Tests

```bash
pytest -v
```

279 tests (278 passing; 1 pre-existing, unrelated failure — see caveat below):
- **users** (16): registration, login (incl. the generic-error check
  that prevents email enumeration), refresh-token rotation +
  blacklist-on-reuse, logout blacklisting, `/me/` isolation.
- **accounts** (11): CRUD, server-side ownership (client can't set
  `user` in the payload), duplicate-name rejection, and cross-user
  isolation on retrieve/update/delete (all return 404, not 403 — the
  API never confirms another user's record exists).
- **categories** (16): seed-data checks against the real migration,
  the one-level tree constraint, parent/child kind matching, system
  categories being read-only via the API, the same cross-user isolation
  pattern as accounts, and a regression pair for two bugs found while
  building Budgets — see the architecture notes below.
- **households** (25): membership-scoped visibility (404 for non-members),
  role-gated rename/delete/invite/remove-member, owner-can't-be-removed,
  leave-household (incl. sole-owner-leaving deletes the household, and
  owner-with-other-members can't leave without transferring first),
  invitation lifecycle (invite/re-invite, accept/decline, email-mismatch
  rejection, expiry).
- **transactions** (27): shape validation (amount>0, category required
  for income/expense and forbidden for transfers, category kind must
  match type, transfer needs a different destination account), account-
  ownership enforcement (can't post against or repoint to someone else's
  account — checked against the transaction's *owner*, not just the
  actor, so a co-member editing a shared transaction can't hijack it),
  household-membership gate on sharing, cross-user/cross-household
  visibility, filtering (type/date range/is_shared), computed account
  balance across income/expense/transfer, and PROTECT-on-delete for
  accounts/categories/households that still have transactions.
- **budgets** (17): household-membership gate on sharing, category-access
  check, the two conditional unique constraints (dup personal budget
  rejected; dup shared budget rejected; a personal and a shared budget
  for the same category+month can coexist), spent/remaining/utilization
  computed from real transactions (income excluded), daily-recommended-
  spend's three cases (normal, over-budget → 0, past month → null),
  `?month=` filtering, and `/performance/`'s prior-months lookup.
- **dashboard** (14): auth + household-membership gate (incl. a clean 400
  for a malformed `?household=`), personal vs. household scope actually
  filtering transactions differently, all 4 chart series (cash flow by
  month, spending by category, net worth by month, budget utilization),
  and the 3 insight types (budget_exceeded, budget_approaching,
  negative_cash_flow) each firing/not-firing at the right threshold.
- **recurring_transactions** (23): same shape/ownership/household-membership
  validation as transactions, `skip-next` (advances without generating),
  the `_advance_date` helper standalone (weekly/biweekly/monthly/yearly,
  incl. month-end and leap-day clamping), and the generation engine:
  generates when due, doesn't generate early, a sequential double-run
  doesn't duplicate, a *pre-existing* `GeneratedOccurrence` for the same
  due_date isn't duplicated either (the actual constraint-based safety
  net, not just the next_run_date advance), multi-period catch-up when
  the job hasn't run in a while, stops at `end_date`, and shared
  recurring templates generate shared transactions.
- **loans** (29): standard CRUD + owner isolation, `monthly_payment`
  against the textbook fixed-rate formula (hand-computed and checked
  against a ₱10,000 @ 12%/12mo example: ₱888.49/mo), the full
  amortization schedule matching that same hand-computed table row by
  row (incl. the final row's rounding-drift absorption landing on
  exactly ₱0), a zero-interest edge case, a 1-month term edge case,
  `log_payment`'s regular-vs-extra split (extra = 100% principal, no
  interest), overpayment/already-paid-off/pre-start-date/interest-not-covered
  all rejected, and — the core "log an extra payment and see the new
  payoff date" story — `projected_payoff_date` provably moving earlier
  after an extra payment, plus a genuine (not vacuous) test of its `None`
  case where a payment can't even cover interest due.
- **savings** (22): household-membership gate on sharing, overcontribution
  beyond target is allowed (not an error — a goal exceeded is a valid
  state), `required_monthly_contribution`'s three cases (normal, met →
  0.00, past target_date → null), and `is_behind_pace`'s linear-pacing
  logic (not behind on day one, behind when underfunded partway through,
  not behind when on track, never behind once fully funded, null when
  target_date isn't after creation) — verified by backdating `created_at`
  directly, since it's `auto_now_add` and can't be set through the factory.
- **forecasting** (13, no models — pure aggregation): the "fewer than 2
  months of history" gate (0 months, 1 month, exactly 2 = enough),
  trailing average excluding both transfers and recurring-attributable
  transactions, the core "recurring overrides the average for its own
  month" story (a yearly recurring expense visibly dents the projected
  net worth series only in its due month, not smeared across every
  month), household scope actually filtering differently from personal,
  and query-param validation (`trailing_months`/`projection_months` must
  be positive integers).
- **imports** (37): transaction CSV import (20) — file validation
  (extension, size limit, row-count cap, missing-column, empty-file),
  per-row parsing failures (bad date, bad/zero amount) marked `FAILED`
  with a message rather than raising for the whole batch, duplicate
  detection's ±2-day window (in and out of range), `confirm`'s default
  (all non-duplicates) vs. explicit `row_ids` (can deliberately include a
  flagged duplicate), imported transactions' derived type-from-amount-
  sign and default system category, "can't confirm twice," unknown row
  id rejected, and owner isolation on upload/preview/confirm. Budget
  `.xlsx` import (17) — same shape plus: staging as `create` vs. `update`
  depending on whether a budget already exists for that category+month,
  confirming actually upserts (re-importing doesn't duplicate), a bad
  category/month/amount/household fails only that row (others still
  import), household-membership enforcement, and the template-download
  endpoint's headers round-tripping through `openpyxl`.
- **notifications** (17): all 4 rule types firing at the right threshold
  (budget exceeded/approaching, recurring due within 3 days but not yet
  overdue — overdue is the generator's job, loan payment due within 3
  days but never for a paid-off loan, goal behind pace), the anti-spam
  dedup (a second sweep doesn't duplicate an unread notification, but a
  new one *can* be created once the old one's marked read), the
  `_next_loan_payment_due_date` helper tested standalone against fixed
  dates, and the API's "PATCH always marks read regardless of body" +
  owner isolation.
- **audit** (12): the generic `full_snapshot`/`field_diff` helpers
  (timestamps excluded, FKs serialized to id strings, only actually-changed
  fields appear in a diff), and the retrofit itself across four apps —
  transaction create/update/delete, budget create/update/delete, a loan
  payment logged, a household invite accepted and a member removed —
  including the one that actually matters: a household member editing
  *another* member's shared transaction produces an audit entry naming
  the editor as `user`, not the transaction's owner. Also: a no-op update
  (PATCH with a value equal to the current one) writes no audit entry at
  all, and an `AuditLogEntry` survives its household being deleted
  (`household_id` goes to `NULL`, the row itself doesn't disappear).

**Known pre-existing failure, unrelated to the above**:
`notifications/tests/test_notifications.py::TestGoalSweep::
test_behind_pace_goal_creates_notification` hardcodes `TODAY =
datetime.date(2026, 8, 24)` and manually overwrites `created_at` via a
queryset `.update()` — which doesn't refresh the in-memory `goal`
object, so `goal.created_at` still reflects the real wall-clock time the
factory ran at. The test only passed by coincidence, on the day it was
written; it now fails every day after, since `TODAY` is in the past
relative to the object's actual `created_at`. Fix is a one-line
`goal.refresh_from_db()` after the `.update()` call; left as-is since
it's outside the scope of whatever change surfaced it.

## Endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/auth/register/` | — | Returns `access` + sets `refresh_token` cookie |
| POST | `/api/auth/login/` | — | Throttled 10/min |
| POST | `/api/auth/refresh/` | refresh cookie | Rotates + blacklists old refresh token |
| POST | `/api/auth/logout/` | Bearer access | Blacklists refresh token, clears cookie |
| GET | `/api/auth/me/` | Bearer access | Current user only |
| GET/POST | `/api/accounts/` | Bearer access | List/create; filter by `account_type`, `is_active`; search `name`, `institution`; each row includes computed `balance` |
| GET/PATCH/DELETE | `/api/accounts/{id}/` | Bearer access | Owner only — 404 otherwise; delete blocked (400) while transactions reference it |
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
| GET/POST | `/api/transactions/` | Bearer access | List/create; visible = yours + anything shared with a household you're in; filter by `account`, `category`, `type`, `household`, `date_from`, `date_to`, `is_shared` |
| GET/PATCH/DELETE | `/api/transactions/{id}/` | Bearer access | Yours, or any member's if shared — 404 otherwise |
| GET/POST | `/api/budgets/` | Bearer access | List/create; filter by `category`, `household`, `month` (`2026-08` or a full date); each row includes computed `spent`/`remaining`/`utilization_pct`/`daily_recommended_spend` |
| GET/PATCH/DELETE | `/api/budgets/{id}/` | Bearer access | Yours, or any member's if shared — 404 otherwise |
| GET | `/api/budgets/{id}/performance/` | Bearer access | Prior months' budgets for the same category+scope, same computed fields |
| GET | `/api/dashboard/summary/` | Bearer access | `?household=<id>` (omitted = personal scope, 403 if not a member); one response with totals, `charts`, and `insights` |
| GET/POST | `/api/recurring-transactions/` | Bearer access | List/create; filter by `account`, `category`, `type`, `household`, `frequency` |
| GET/PATCH/DELETE | `/api/recurring-transactions/{id}/` | Bearer access | Yours, or any member's if shared — 404 otherwise |
| POST | `/api/recurring-transactions/{id}/skip-next/` | Bearer access | Advances `next_run_date` one period without posting a transaction |
| GET/POST | `/api/loans/` | Bearer access | List/create; each row includes computed `monthly_payment`, `remaining_balance`, `payoff_date` (theoretical), `projected_payoff_date` (reflects actual payments) |
| GET/PATCH/DELETE | `/api/loans/{id}/` | Bearer access | Owner only — 404 otherwise |
| GET | `/api/loans/{id}/amortization-schedule/` | Bearer access | The theoretical schedule from day one (no extra payments) |
| GET/POST | `/api/loans/{id}/payments/` | Bearer access | GET lists logged payments; POST logs one — `principal_portion`/`interest_portion` are server-computed, not accepted from the client |
| GET/POST | `/api/savings-goals/` | Bearer access | List/create; each row includes computed `total_contributed`, `progress_pct`, `required_monthly_contribution`, `is_behind_pace` |
| GET/PATCH/DELETE | `/api/savings-goals/{id}/` | Bearer access | Yours, or any member's if shared — 404 otherwise |
| GET/POST | `/api/savings-goals/{id}/contributions/` | Bearer access | GET lists contributions; POST logs one (overcontribution beyond target is allowed) |
| GET | `/api/forecast/` | Bearer access | `?household=`, `?trailing_months=` (default 6), `?projection_months=` (default 12) — all optional |
| GET/POST | `/api/imports/` | Bearer access | POST is `multipart/form-data`: `file`, `account`, `date_column`, `description_column`, `amount_column` |
| GET | `/api/imports/{id}/` | Bearer access | Owner only — 404 otherwise; no PATCH/DELETE |
| GET | `/api/imports/{id}/preview/` | Bearer access | All staged rows + their status/error/duplicate flag |
| POST | `/api/imports/{id}/confirm/` | Bearer access | JSON body: optional `row_ids` (default = every non-duplicate pending row) |
| GET | `/api/imports/budgets/template/` | Bearer access | Downloads a blank `.xlsx` with the expected header row + one example row |
| GET/POST | `/api/imports/budgets/` | Bearer access | POST is `multipart/form-data`: just `file` — no column mapping, a fixed header row (Category/Month/Amount, optional Household) instead |
| GET | `/api/imports/budgets/{id}/preview/` | Bearer access | Staged rows + status/error, and `action` (create vs. update) determined against the DB at preview time |
| POST | `/api/imports/budgets/{id}/confirm/` | Bearer access | JSON body: `row_ids` — re-resolves create-vs-update fresh per row rather than trusting the preview-time `action` |
| GET | `/api/notifications/` | Bearer access | Yours only |
| PATCH | `/api/notifications/{id}/` | Bearer access | Marks read regardless of body content — 404 for another user's notification |

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
- Accounts still have no stored `balance` column — `Account.balance` is a
  `@property` that aggregates `transactions` (SUM by type, signed) on
  every read. Kept as a plain property rather than a `SerializerMethodField`
  N+1 trap on list views for now; revisit only if profiling under real
  data shows it's slow (Section 25 — not optimized preemptively).
- `common/viewsets.py::HouseholdScopedModelViewSet` is `OwnedModelViewSet`'s
  sibling for resources that can be personal *or* shared: visible if you
  own it OR you're a member of the household it's shared with.
  `TransactionViewSet` and `BudgetViewSet` both use it; SavingsGoals
  likely will too.
- `common/exceptions.py::exception_handler` (wired via
  `REST_FRAMEWORK["EXCEPTION_HANDLER"]`) converts a plain
  `django.core.exceptions.ValidationError` — the kind `full_clean()`
  raises — into DRF's `ValidationError`. Without it, any model that
  validates itself on save (Category, Transaction, Budget) turned a
  constraint violation into an unhandled 500 instead of a 400; found
  while building Budgets, fixed once for every app instead of per-serializer.
- `categories/models.py::Category`'s uniqueness is two conditional
  `UniqueConstraint`s, not one covering all four columns — SQL (and
  Django's own `validate_unique`) treat NULL as never equal to NULL, so a
  single constraint including the nullable `parent` column silently never
  fired for top-level categories (most of them). `budgets/models.py::Budget`
  has the same shape of fix for its nullable `household` column, done
  correctly from the start.
- `common/money.py::quantize` is the ROUND_HALF_UP-to-2-places helper
  Section 14 calls for — added once `Budget.daily_recommended_spend`
  gave it a real caller (a division that can produce more than 2 places),
  not preemptively.
- `transactions/models.py::Transaction` uses `on_delete=PROTECT` on every
  FK except `user` (account, to_account, category, household) — a hard
  delete of any of those must never silently take transaction history
  down with it (Section 8). Each affected viewset's `perform_destroy`
  catches the resulting `ProtectedError` and re-raises it as a clean 400
  instead of a 500.
- Shape validation (transfer vs. category, category-kind-matches-type) is
  duplicated in `TransactionSerializer.validate()` (clean 400s) and
  `Transaction.clean()` (defense in depth for any non-API caller, e.g. a
  future import script) — same pattern `Category` already established.
  Ownership/membership checks live only in `transactions/services.py`,
  and are checked against the transaction's *owner*, not the request
  user, so a co-member editing a shared transaction can't repoint it at
  an account they — not the owner — happen to hold.
- `dashboard/` has no models — it's a read-only aggregation layer over
  Transaction/Budget, one `services.summary()` call issuing a small fixed
  set of aggregate queries (Section 25) rather than one request per
  chart. Net worth (`net_worth_by_month`) is always the requesting
  user's own even when the rest of the dashboard is household-scoped,
  because Accounts are never shared (Section 7); it also simplifies to
  `income − expense` since transfers between a user's own accounts net
  to zero — the same reasoning Section 15's forecasting design uses.
  `/api/reports/spending-by-category/` and `/api/reports/cash-flow/`,
  separately listed in the original blueprint (§10), ended up folded
  into `summary()`'s own `charts` object instead of built as standalone
  endpoints — no reason to make them separate round trips.
- `recurring_transactions/services.py::generate_due_occurrences` is plain
  Python, deliberately independent of Celery — `tasks.py` is a one-line
  `@shared_task` wrapper, and `manage.py generate_recurring_transactions`
  calls the same function directly. Idempotency is constraint-based, not
  convention-based: `GeneratedOccurrence`'s `unique(recurring, due_date)`
  means a retried/duplicated run for an already-posted due_date hits an
  `IntegrityError` (caught, ignored) rather than double-posting — tested
  directly by pre-creating the occurrence and re-running the engine, not
  just by calling it twice (which would trivially pass without the
  constraint doing any work, since `next_run_date` has already moved on).
  The engine catches up on multiple missed periods in one run rather than
  jumping straight to today, so a generator that hasn't run in 3 weeks on
  a weekly recurring posts 4 transactions, not 1.
- `RecurringTransaction.clean()` deliberately does *not* reject
  `end_date < next_run_date` — only `RecurringTransactionSerializer`
  does. The engine's own terminal state, after generating everything
  through `end_date`, is `next_run_date` landing *past* `end_date` (there's
  nothing left to generate) — if the model itself rejected that, the
  engine's own `save()` would raise on every schedule that finishes.
  Found by the test for that exact case failing with an unhandled 500
  before the check was narrowed to the serializer.
- `config/celery.py` wires the app + a daily beat entry for the recurring
  generator; `config/__init__.py` imports it so `@shared_task` works
  everywhere. No worker/beat process runs anywhere yet — Docker Compose
  (Section 21) isn't built — and Redis is never contacted by `runserver`,
  `migrate`, or the test suite, only by an actual `.delay()`/`apply_async()`
  call or a running `celery worker`/`celery beat` process.
- `common/dates.py::add_months` is shared between
  `recurring_transactions/services.py` (monthly/yearly frequency advance)
  and `loans/services.py` (schedule row dates, payoff dates) — extracted
  once there were two real callers with the same month-end-clamping need
  (Jan 31 + 1 month → Feb 28/29), not preemptively.
- `loans/models.py::Loan` isn't built on `HouseholdScopedModelViewSet`
  like Transaction/Budget/RecurringTransaction — it's plain
  `OwnedModelViewSet`. The blueprint's ERD never gave `loans_loan` a
  `household` column and no user story asks for a shared loan, so unlike
  those three apps this one stayed on the simpler personal-only pattern.
- `loans/services.py` keeps `amortization_schedule()` (the theoretical,
  day-one schedule) and `projected_payoff_date()` (simulated forward from
  the loan's *actual* `remaining_balance`, which reflects logged
  payments) as two distinct functions rather than one "smart" schedule —
  the theoretical schedule answers "what was I supposed to pay," the
  projection answers "given what I've actually paid, when am I done,"
  and conflating them would make neither answer cleanly.
- `LoanPayment.principal_portion`/`interest_portion` are always
  server-computed in `services.log_payment`, never accepted from the
  client — same reasoning as Transaction's amount-sign convention
  (Section 8): a value derived from state at a specific moment shouldn't
  be something the client asserts. A DB `CheckConstraint` enforcing
  `amount = principal_portion + interest_portion` backs this as an
  invariant, not just a convention.
- `savings/services.py::is_behind_pace` uses linear pacing (elapsed
  fraction of time vs. contributed fraction of target) from the goal's
  `created_at` to `target_date` — simple by design, matching the
  blueprint's forecasting philosophy (Section 15) of an explained,
  bounded approximation rather than anything more elaborate. Returns
  `None`, not `False`, when `target_date` isn't after `created_at` — pacing
  is undefined there, not "on track."
- Unlike `LoanPayment`, `SavingsContribution` has no upper-bound
  validation — overcontributing past `target_amount` is a valid, even
  celebratory state (goal exceeded), not an error the way overpaying a
  loan past its remaining balance would be.

- `households/services.py::resolve_household` is shared between
  `dashboard/services.py` and `forecasting/services.py` (both re-export
  it so `<app>.services.resolve_household` keeps working) — the identical
  "optional `?household=<id>` -> Household, membership-checked, clean
  400 on a malformed UUID" resolution, extracted once there were two
  real callers.
- `forecasting/services.py` excludes recurring-attributable transactions
  from the trailing average via the reverse `generated_occurrence` link
  (`generated_occurrence__isnull=True`), then simulates every still-active
  `RecurringTransaction` forward from its own `next_run_date` using
  `common/dates.py::advance_date` (promoted out of
  `recurring_transactions/services.py` once forecasting needed the exact
  same per-frequency date math) — this is what lets a known future
  recurring expense visibly dent one specific month's projection instead
  of being smeared flat across every month via the average.

- `imports/views.py::ImportBatchViewSet` isn't a plain `ModelViewSet` —
  `create()` takes a multipart file + a 3-column mapping + one target
  Account, not a JSON body shaped like `ImportBatch`'s own fields, so
  it's handled explicitly rather than through a writable serializer.
  `parser_classes` lists `MultiPartParser`/`FormParser` (for `create`)
  *and* `JSONParser` (for `confirm`'s `row_ids` body) since DRF picks the
  parser per-request from `Content-Type`, not per-action.
- `imports/services.py::create_batch` derives each row's Transaction
  `type` from the amount's sign (negative = expense, positive = income)
  rather than a mapped "type" column — matching Transaction's own
  positive-magnitude-plus-type convention (Section 8) and how real bank
  CSV exports actually look. Every imported row lands in the matching
  system "Other Income"/"Other Expense" catch-all category (already
  seeded by `categories/migrations/0002_seed_default_categories.py`) —
  recategorizing afterward is just a normal Transaction `PATCH`, not a
  special import-specific flow.
- `ImportRow.is_duplicate` is independent of `status` — set once at
  upload time and never overwritten, so even a row the user chose to
  import anyway (via explicit `row_ids`) still shows it was originally
  flagged, preserving that as audit history rather than as a decision
  that erases its own reasoning.
- **Deferred, not built**: routing files over the 500-row cap to Celery
  with a polled status endpoint (Section 16). This build always
  processes synchronously and simply rejects anything over the cap —
  matches the blueprint's own stated fallback for the common case
  without yet building the async path for the uncommon one.
- **Budget `.xlsx` import is a separate, simpler pipeline** — fixed
  header row (`Category`/`Month`/`Amount`, optional `Household`) instead
  of the transaction CSV import's column-mapping step, since a budget
  only ever has 3-4 fields; adding a mapping UI for that would be pure
  overhead. Parsed with `openpyxl` (`read_only=True, data_only=True` —
  cell *values*, not formulas). Unlike transactions, budgets are
  naturally idempotent per `(category, month)`, so there's no
  duplicate-detection/skip flow — re-importing the same category+month
  **updates** the existing budget instead of erroring, and
  `BudgetImportRow.action` records which one a row will be, determined
  fresh each time (staging *and* confirm both call `_existing_budget()`
  rather than confirm trusting the staged value, since the DB can change
  between preview and confirm). Actual persistence goes through
  `budgets.services.create_budget`/`update_budget` — the same functions
  the regular Budget API calls — so household-membership/category-access
  validation and audit logging aren't duplicated for the import path.

- `notifications/models.py::Notification.household` uses `on_delete=CASCADE`,
  unlike Transaction/Budget/RecurringTransaction/SavingsGoal's `PROTECT` —
  a notification is a transient alert, not financial history, so nothing
  is lost if a deleted household's notifications go with it.
- `notifications/services.py::_already_notified` queries
  `payload__entity_id` (a JSONField key lookup) rather than a dedicated
  `entity_id` column — matching the ERD's literal column list for
  `Notification` (Section 8), which only has `payload`, not a separate
  entity reference.
- Four of the five documented notification types are implemented;
  `unusual_expense` is deliberately deferred — see the architecture notes
  under Budgets/Dashboard for the same "don't invent an unspecified
  threshold" reasoning applied there.
- Same Celery-independent shape as recurring transactions:
  `notifications/services.py::sweep()` is the tested engine, `tasks.py`
  is a one-line wrapper, and `manage.py sweep_notifications` runs it
  without a broker. `config/celery.py`'s beat schedule now has two
  entries — the daily recurring generator and this hourly sweep.

- `audit/services.py::full_snapshot`/`field_diff` are generic across any
  model — driven by `instance._meta.fields`, not a hand-maintained list
  per entity type — so retrofitting a 5th app later means one `audit.log(...)`
  call, not a new serialization helper.
- Every retrofitted `update_*`/`delete_*` service function now takes an
  explicit `actor` parameter, separate from the entity's `user`/owner —
  this is what lets a household member editing *someone else's* shared
  Transaction or Budget produce an audit entry that correctly names the
  editor, not the owner, as `user` on the `AuditLogEntry`.
- `households/services.py::remove_member`/`leave_household` both log
  through `HouseholdMembership`'s id, captured *before* `.delete()`
  removes the row — `AuditLogEntry.entity_id` has nothing to point at
  once the row is gone, so the id has to be grabbed first.
- **Not implemented**: an audit entry for the sole-owner-leaves-and-the-
  household-itself-gets-deleted path in `leave_household` — a rare edge
  case where the household row disappears in the same call, not just a
  membership row. Flagged rather than silently skipped.
- **Not implemented**: "role changed" (Section 19) — there's no
  membership-role-change endpoint yet (role is only ever set once, at
  household creation or invite acceptance), so there's nothing for this
  step to audit-log. A pre-existing gap this step surfaced, not something
  in scope to fix here.

## Docker & CI

```bash
docker compose up --build
docker compose exec backend python manage.py migrate   # first run only
```

Builds `backend/Dockerfile`'s `dev` stage (runserver against a
live-mounted volume) plus `frontend`, `postgres`, `redis`,
`celery-worker`, and `celery-beat` — see the top-of-file comment in
`/docker-compose.yml` for exactly what depends on what. `redis` has a
`healthcheck` (`redis-cli ping`) that `backend`/`celery-worker`/
`celery-beat` all wait on via `condition: service_healthy` — added after
the first real run showed the celery containers racing Redis on startup
(harmless on its own — Celery's client retried and connected ~2s later —
but the healthcheck removes the race instead of relying on the retry).

`.github/workflows/ci.yml` runs on every PR: `ruff check` (see
`pyproject.toml` — line-length 120, and `RUF012` is deliberately not
selected since it flags ordinary Django/DRF class attributes like
`permission_classes = [...]` as bugs), `pytest` against a real
`postgres:16` service container (not sqlite, so CI catches anything sqlite
is lenient about that Postgres isn't), a frontend job (`oxlint`,
`tsc --noEmit`, `vitest run`), and a Docker build check for both images.

**Verified with a real `docker compose up --build`** (2026-08-24, once
Docker Desktop was available): all six containers start; migrations
apply cleanly against the containerized Postgres; register/login work
through the containerized backend; the frontend serves; and
`sweep_notifications.delay()` was dispatched through the containerized
Redis, picked up by `celery-worker`, and completed successfully — visible
in `docker compose logs celery-worker`. The full pytest suite (279
tests, 278 passing — see the pre-existing-failure note above) was also
run directly against this real Postgres via `docker compose exec backend
pytest`, not just sqlite. What's *not* yet verified is
`.github/workflows/ci.yml` running on GitHub's actual runners — a real PR
is the remaining check for the workflow file's own mechanics (action
versions, caching, secrets), separate from whether the underlying app
works against Postgres, which is now directly confirmed.

## Deploying (Railway)

Split deploy: backend + Postgres + Redis + Celery on Railway, frontend
as a static build on Vercel/Netlify (see `frontend/README.md`) — the
frontend has nothing to run server-side, so it doesn't belong on the
same platform as the API.

Railway is a **monorepo** here, so every service needs its **Root
Directory** (Service → Settings → Source) set to `backend` — pointing a
service at the repo root, which has no single recognizable app in it,
is exactly what produces a `Railpack could not determine how to build
the app` error. Create three services, all with Root Directory
`backend`:

1. **web** — default settings pick up `backend/Dockerfile` automatically
   (`railway.json` pins `builder: DOCKERFILE` explicitly too, so this
   isn't left to auto-detection). Docker builds the Dockerfile's last
   stage by default, which is the `prod` target — no start-command
   override needed; its own `CMD` runs `migrate` then `gunicorn`,
   binding to Railway's injected `$PORT`.
2. **celery-worker** — same image, but override **Custom Start Command**
   (Service → Settings → Deploy) to `celery -A config worker -l info`.
3. **celery-beat** — same, but `celery -A config beat -l info`.

Add Railway's **Postgres** and **Redis** plugins to the project, then in
each service's variables: `DATABASE_URL=${{Postgres.DATABASE_URL}}`,
`CELERY_BROKER_URL=${{Redis.REDIS_URL}}`. Also set `SECRET_KEY` (a real
one — don't reuse the dev default), `DEBUG=False`, `ALLOWED_HOSTS`
(Railway's assigned domain), and `CORS_ALLOWED_ORIGINS` (the deployed
frontend's exact URL, no trailing slash).

`config/settings.py` reads `DATABASE_URL` via `dj-database-url` in
preference to the discrete `DB_*` vars docker-compose.yml sets — both
paths are supported, so nothing about local/Docker dev changed. Static
files (`/admin/`, DRF's browsable API) are served by **whitenoise**
directly from the gunicorn process, since a PaaS web dyno has no nginx
in front of it the way `docker-compose`'s setup implicitly assumes.

Verified independent of Railway itself: `docker build --target prod`
then `docker run -e PORT=9000 ...` with no docker-compose involved —
migrations applied, gunicorn bound to the injected port, and the API
responded correctly — before ever touching Railway's own configuration.

## What's next (Phase 1, step 15)

The frontend (Section 11) — not started. Every backend step in the V1
phase plan (§27) is done; step 16 (docs polish: README, ADRs, ERD image,
screenshots, seeded demo data) is the only backend-adjacent work left —
see `/BLUEPRINT.md` in the project root for the full phased plan.
