# Smart Household Finance Manager — Blueprint

Status: reconstructed 2026-08-24. Steps 1–2 (Users/Auth, Accounts, Categories)
were already implemented before this document existed; everything else below
is planned. Sections are marked **[BUILT]** or **[PLANNED]**.

---

## 1. Product Overview

A full-stack web app that answers, for a household or an individual: *where
is our money going, what can we afford, and are we on track for our goals?*
Deterministic financial calculations (not "AI") turn transaction history into
budgets, forecasts, and rule-based insights.

## 2. Problem Statement

Most budgeting apps are either single-user ledgers or heavyweight bank
aggregators. Households need a middle ground: shared visibility into joint
expenses (rent, groceries) without forcing every transaction — one partner's
salary, personal shopping — into a shared pool. Existing tools rarely model
that personal/shared split well.

## 3. Target Users

Households of 1–6 members. A household is the tenancy boundary for shared
data; a user can belong to more than one household (e.g., roommates *and*
a family) but each transaction/account is unambiguously either personal to
one user or visible to one household — never both, never neither.

## 4. MVP Scope

**MVP** = smallest deployable slice that proves the core value prop end to
end. **V1** = adds the features that make this a portfolio piece rather than
a CRUD app.

| Tier | Modules |
|---|---|
| **MVP** | Auth **[BUILT]**, Households + membership/roles, Accounts **[BUILT]**, Categories **[BUILT]**, Transactions (income/expense/transfer, personal/shared), a single monthly Budget per category, a dashboard with 4 charts + 3 rule-based insights |
| **V1 (portfolio-complete)** | Recurring transaction engine, Loans + amortization, Savings goals, Forecasting engine, CSV import, Notifications (Celery), Audit log, Docker Compose, CI |
| **Explicitly out of scope** | Real bank integrations, storing bank credentials, multi-currency FX conversion (store currency per account/transaction, don't convert), native mobile, LLM-generated narrative insights |

Cutting recurring/loans/forecasting from MVP is deliberate — they're what
differentiates this project (§26), but building them on a Transaction model
that doesn't exist yet, or on top of a still-changing household model, is
wasted work. MVP first proves the shape is right; V1 adds depth.

## 5. Future Features (post-V1)

Multi-currency with live FX rates; per-member budget breakdowns within a
shared budget; investment account price feeds; shared bill-splitting/IOU
tracking between household members; PWA/offline support; real AI narrative
layer *on top of* the deterministic insight engine (never replacing it).

## 6. User Stories

**Auth [BUILT]** — register, log in, log out, see my own profile, be rejected
generically (no email enumeration) on bad login.

**Households** — create a household; invite a member by email; accept/decline
an invite; see my role; remove a member (if Owner/Admin); leave a household;
switch between households I belong to.

**Accounts [BUILT]** — create/edit/deactivate an account; see its computed
balance; filter by type.

**Categories [BUILT]** — see system defaults; create custom categories/
subcategories; can't edit/delete system ones.

**Transactions** — record income/expense/transfer; tag as personal or
household-shared; edit/delete my own (or, if shared, any member's, subject to
role); filter by date/account/category/type; attach a receipt.

**Budgets** — set a monthly budget per category; see spent/remaining/
utilization; see a daily-recommended-spend figure; see last month's
performance.

**Recurring** — define a recurring income/expense; see upcoming occurrences;
have them auto-post without duplication if I check twice.

**Loans** — record a loan; see the amortization schedule; log an extra
payment and see the new payoff date.

**Savings goals** — set a target amount/date; see progress, required monthly
contribution, and a warning if I'm behind pace.

**Dashboard** — see net cash flow, savings rate, net worth, and 3–5 rule-based
insights at a glance, scoped to the active household or "personal only."

**Import** — upload a CSV, map columns, preview, see flagged duplicates,
confirm, see per-row errors for anything that failed.

**Notifications** — get notified in-app when a budget is exceeded/near
limit, a recurring payment is due soon, or a goal is falling behind.

## 7. Core Domain Model

```
User [BUILT] ──< HouseholdMembership >── Household
  │                    (role: owner/admin/member)
  │
  ├──< Account [BUILT] (owned by one User; currency, type, no stored balance)
  │
  ├──< Category [BUILT] (owned by one User, or is_system=True/shared; 1 level deep)
  │
  ├──< Transaction >── Account (income | expense | transfer)
  │        │                also FKs: Category, optional Household (null = personal)
  │        └──(transfer only)── to_account
  │
  ├──< Budget >── Category, month, amount
  │
  ├──< RecurringTransaction >── generates ──< Transaction
  │
  ├──< Loan >──< LoanPayment
  │
  ├──< SavingsGoal >──< SavingsContribution
  │
  ├──< ImportBatch >──< ImportRow >── (creates) Transaction
  │
  ├──< Notification
  │
  └──< AuditLogEntry (generic: entity_type, entity_id, action, metadata)
```

**Key decision — where "household" attaches.** Accounts and Categories stay
user-owned (already built that way, and it's correct: *your* bank account is
yours even in a shared household). The personal/shared split lives on
**Transaction**, via a nullable `household` FK: `null` = personal,
`household=X` = visible to every member of X. This means Account/Category
don't need to change; only Transaction (and anything downstream: Budget,
Dashboard, Insights) needs to be household-aware from day one.

## 8. Database ERD Proposal

Conventions already established and carried forward: UUID PKs everywhere
(`common.TimeStampedUUIDModel`), `created_at`/`updated_at` on every table,
`DecimalField(max_digits=12, decimal_places=2)` for all money (never float —
binary floating point can't represent ₱0.10 exactly, and rounding errors
compound across thousands of transactions; Decimal with fixed scale is exact
and matches how currency actually works). Timestamps stored UTC
(`USE_TZ=True`, already set), converted to household/user local time only at
the presentation layer — a household's members may be in different time
zones, so "today" must be resolved per-viewer, not baked into stored data.

| Table | Key columns | Constraints / indexes |
|---|---|---|
| `households_household` | name, created_by | — |
| `households_householdmembership` | user_id, household_id, role | unique(user, household); index(household_id) |
| `households_invitation` | household_id, email, invited_by, token, status, expires_at | unique(household_id, email, status='pending') |
| `accounts_account` **[BUILT]** | user_id, name, account_type, currency, institution, is_active | unique(user, name) |
| `categories_category` **[BUILT]** | user_id (null=system), name, kind, parent_id, is_system | unique(user, name, kind, parent) |
| `transactions_transaction` | user_id, household_id (null), account_id, to_account_id (transfers only), category_id, type, amount, currency, date, description, notes | index(account_id, date); index(household_id, date); check(type='transfer' → category_id IS NULL); check(amount > 0) |
| `budgets_budget` | household_id (null), user_id, category_id, month (date, day=1), amount | unique(user, household, category, month) |
| `recurring_transactions_recurringtransaction` | template fields mirroring Transaction, frequency, next_run_date, end_date | index(next_run_date) |
| `recurring_transactions_generatedoccurrence` | recurring_id, due_date, transaction_id | unique(recurring_id, due_date) — this is what makes generation idempotent |
| `loans_loan` | principal, interest_rate, term_months, start_date, lender | — |
| `loans_loanpayment` | loan_id, date, amount, principal_portion, interest_portion, is_extra | index(loan_id, date) |
| `savings_savingsgoal` | household_id (null), name, target_amount, target_date | — |
| `savings_savingscontribution` | goal_id, date, amount | index(goal_id, date) |
| `imports_importbatch` | user_id, account_id, filename, status, row_count | — |
| `imports_importrow` | batch_id, raw_data (JSON), status, error, transaction_id, is_duplicate | index(batch_id) |
| `notifications_notification` | user_id, household_id (null), type, payload (JSON), read_at | index(user_id, read_at) |
| `audit_auditlogentry` | user_id, household_id, action, entity_type, entity_id, metadata (JSON), created_at | index(household_id, created_at); index(entity_type, entity_id) |

**Amount sign convention:** store `amount` as a positive Decimal on every
transaction; `type` (income/expense/transfer) determines the sign applied
when summing. Storing signed amounts is a common source of double-negative
bugs when a transaction type changes; positive-magnitude + explicit type is
easier to reason about and to validate (`amount > 0` as a DB check
constraint, not just app-level).

**Soft deletion:** not used for Account/Category/Transaction. A hard-deleted
transaction still has to be *auditable* — so deletion goes through the
service layer, which writes an `AuditLogEntry` capturing the full row before
the DB delete, rather than adding a `deleted_at` column everywhere and having
every query remember to filter it out. Trade-off: you can't "undelete" from
the UI directly (you'd restore from the audit trail), but you also can't
forget a `.filter(deleted_at=None)` and leak deleted data — a real bug class
soft-delete introduces if applied inconsistently.

## 9. Backend Architecture

One Django app per bounded context, matching what's already there:
`common`, `users`, `households` (new), `accounts` **[BUILT]**, `categories`
**[BUILT]**, `transactions`, `budgets`, `recurring_transactions`, `loans`,
`savings`, `imports`, `notifications`, `audit`, `dashboard`, `forecasting`.

**Business logic lives in a `services.py` per app, not in views or
serializers.** E.g. `transactions/services.py::create_transaction(...)` does
validation-that-spans-models, audit logging, and (later) notification
triggers; the view/serializer stays thin. This is the fix for the spec's
explicit warning against "business logic hidden inside serializers" —
serializers validate *shape*, services own *behavior*.

**Household isolation** extends the existing `OwnedModelViewSet` pattern
(`common/viewsets.py`) rather than replacing it: a new
`HouseholdScopedModelViewSet` filters `Q(user=request.user) |
Q(household__memberships__user=request.user)`, mirroring how
`CategoryViewSet` already does its own OR-based queryset for system vs. user
categories. Same 404-not-403 philosophy: a user probing another household's
transaction ID gets "not found," never "forbidden" (which would confirm the
record exists).

Audit logging is **explicit calls from services, not Django signals** —
signals make "what happens when a transaction is deleted" implicit and
scattered; a service function that calls `audit.log(...)` inline is visible
in the same place as the business logic it's describing, and is trivial to
unit test without wiring up signal receivers.

## 10. REST API Design

Already live **[BUILT]**:

```
POST   /api/auth/register/        POST /api/auth/refresh/
POST   /api/auth/login/           POST /api/auth/logout/
GET    /api/auth/me/
GET|POST /api/accounts/           GET|PATCH|DELETE /api/accounts/{id}/
GET|POST /api/categories/         GET|PATCH|DELETE /api/categories/{id}/
```

Planned, same conventions (PageNumberPagination, DjangoFilterBackend,
household/owner-scoped 404s):

```
/api/households/                       CRUD; nested actions below
/api/households/{id}/members/          list, DELETE {user_id} (role-gated)
/api/households/{id}/invitations/      POST (invite), GET
/api/invitations/{token}/accept/       POST
/api/transactions/                     CRUD; filter: account, category, type,
                                        date_from, date_to, household, is_shared
/api/budgets/                          CRUD; ?month=2026-08
/api/budgets/{id}/performance/         historical utilization
/api/recurring-transactions/           CRUD; POST /{id}/skip-next/
/api/loans/                            CRUD
/api/loans/{id}/amortization-schedule/ GET
/api/loans/{id}/payments/              POST (log payment, incl. extra)
/api/savings-goals/                    CRUD
/api/savings-goals/{id}/contributions/ POST
/api/dashboard/summary/                GET — overview + chart series + insights
/api/reports/spending-by-category/     GET
/api/reports/cash-flow/                GET
/api/forecast/                         GET — projection given assumptions
/api/imports/                          POST (upload), GET (list batches)
/api/imports/{id}/preview/             GET — parsed rows + duplicate flags
/api/imports/{id}/confirm/             POST — column mapping in body
/api/notifications/                    GET; PATCH {id} (mark read)
```

Validation errors follow DRF's default `{field: [messages]}` shape
throughout — no custom envelope, so the frontend needs exactly one error
adapter.

## 11. Frontend Architecture (not started — greenfield)

```
frontend/src/
├── app/            # store (the one small RTK slice), providers, router root
├── api/            # one file per resource: axios/fetch client + TanStack Query hooks
├── features/       # auth, households, accounts, categories, transactions,
│                   # budgets, recurring, loans, savings, dashboard, imports
│                   #   each: components/, hooks.ts, api.ts, types.ts
├── components/     # shared, presentational only (Button wrappers, EmptyState, MoneyInput)
├── pages/           # route-level composition of feature components
├── hooks/            # cross-feature hooks (useActiveHousehold, useCurrentUser)
├── types/            # shared types only (Money, ISODate) — not a dumping ground
└── lib/              # dayjs config, MUI theme, query client config
```

Feature-based over the flatter layered structure the spec sketched — a
`transactions/` feature folder that owns its components + hooks + API calls
scales better past ~5 modules than parallel top-level `components/`,
`hooks/`, `api/` folders where finding "everything about budgets" means
hunting three directories.

## 12. State Management Strategy

- **Server state:** TanStack Query for everything that comes from the API.
  Mutations use `invalidateQueries` scoped to the affected resource + the
  dashboard (a transaction write invalidates transactions, the relevant
  budget, and dashboard summary). Optimistic updates only for high-frequency,
  low-risk actions (marking a notification read) — not for money-affecting
  writes, where the cost of an optimistic UI rollback confusing a user about
  their balance outweighs the latency win.
- **Redux Toolkit — one slice, deliberately:** `session` (in-memory access
  token, current user, **active household id**). Active household is the one
  piece of state that's genuinely global and non-derivable — nearly every
  query needs it, it must survive route changes, and it isn't naturally
  "owned" by any single feature. Everything else the spec listed as Redux
  candidates (form state → React Hook Form, server cache → TanStack Query)
  stays out of Redux. This is intentionally *not* auth-token storage — the
  access token lives in a JS variable, not persisted Redux/localStorage state
  (see §13); only its *presence* (booleans/user object) is in the store.
- **Forms:** React Hook Form + zod resolver for every form; validation
  schema shared, where shapes match, with what the DRF serializer enforces
  (duplicated by necessity — client and server validate independently — but
  kept adjacent in code so drift is easy to spot in review).

## 13. Authentication & Authorization **[BUILT, backend]**

**JWT with the refresh token in an httpOnly cookie, access token returned in
the body and held in memory on the frontend** — already implemented in
`users/views.py`. Chosen over (a) plain JWT-in-localStorage: readable by any
injected script, so one XSS hole anywhere in the app becomes full account
takeover; (b) pure Django session cookies: works, but throws away the
stateless-API benefit DRF/JWT gives you if you ever split the frontend to a
different origin or add a mobile client later. This hybrid keeps the
long-lived credential (refresh token) unreadable to JS while keeping the
short-lived one (access token, 10 min) out of persistent storage entirely —
an XSS bug can steal at most 10 minutes of access, not a 14-day refresh
token. `SameSite=Lax` + the cookie's `path=/api/auth/` scoping is the CSRF
mitigation for the refresh/logout endpoints, since they're the only ones a
browser will attach the cookie to automatically.

**Authorization, planned:** a `HouseholdRolePermission` DRF permission class
parameterized by minimum role (`owner`, `admin`, `member`), checked against
`HouseholdMembership` for the household implied by the request. Combined with
`HouseholdScopedModelViewSet` (§9) for the "must be a member at all" layer —
role check is a second, narrower gate on top (e.g., only Owner/Admin can
remove a member; any member can create a shared transaction).

## 14. Financial Calculation Architecture

- **Decimal, never float**, for every monetary field — already the pattern
  the codebase will need to continue (Account/Transaction/Budget/Loan all use
  `DecimalField`). Arithmetic in Python code uses `decimal.Decimal` exclusively;
  a `common/money.py` helper centralizes rounding/quantization
  (`ROUND_HALF_UP` to 2 places) so it's not reimplemented per app.
- **Account balance is computed, not stored** — already decided and
  documented in `accounts/models.py`. A stored balance can silently drift
  from reality the moment any write path (a bug, a manual DB fix, a future
  bulk-import script) forgets to update it — in a finance app that's the
  worst possible bug class, because it's *silent*. The cost is a `SUM()`
  aggregate query per account fetch instead of a column read. Mitigation if
  that becomes measurably slow: index `transactions(account_id)` (already
  planned above), and only if profiling shows it's still a bottleneck, add a
  periodically-refreshed cached balance (e.g., updated by a Celery task, not
  by application writes) — never let two sources of truth exist that the
  request path itself has to keep in sync.
- **Budget spent/remaining** computed the same way: aggregate transactions
  for `(category, month)`, not a running counter.

## 15. Forecasting Design

Trailing-N-month (default N=6, configurable) simple moving average of income
and expenses, **excluding transfers** (they net to zero across accounts and
aren't real income/expense). `avg_monthly_savings = avg_income -
avg_expenses`. Projection: `current_net_worth + avg_monthly_savings ×
months`. Where recurring transactions exist, their known future amounts
override the average for the months they fall in, rather than double-
counting them inside both the average *and* a separate recurring projection.
Explicitly surfaced to the user as *"projection based on your last 6 months
— not a guarantee"*, with the N and the averages shown, not hidden — the
spec is right that this must never be presented as certain. Edge cases:
fewer than 2 months of history → don't project, show "not enough data yet"
rather than a misleading single-data-point trend.

## 16. CSV Import Architecture

Upload → parse (Python's stdlib `csv`, no pandas dependency needed for this
scale) → **validation pass that persists nothing**, returning per-row
errors/warnings → column-mapping UI (user maps CSV headers to
date/description/amount/account) → **duplicate detection**: flag a row as a
likely duplicate if an existing transaction matches on
`(account, date, amount)` within a ±2-day window (handles bank posting-date
vs. transaction-date drift) — flagged, not auto-skipped, user decides per row
→ confirm → persist inside one DB transaction per batch, writing
`ImportRow` records (raw data + outcome) for a full audit trail and easy
"why did row 47 fail" debugging. Files over a row-count threshold (e.g. 500)
process via Celery with a polled status endpoint; smaller ones process
synchronously in the request for simplicity.

## 17. Background Jobs (Celery + Redis)

Celery beat schedule:

- **Recurring transaction generator** (daily): for every
  `RecurringTransaction` with `next_run_date <= today`, create the
  `Transaction` + a `GeneratedOccurrence(recurring_id, due_date)` row inside
  one DB transaction, guarded by the `unique(recurring_id, due_date)`
  constraint — a retried/duplicated task run hits an `IntegrityError`
  on the second attempt and is caught/ignored, so the job is idempotent
  by construction, not by convention.
- **Notification sweep** (hourly): evaluate budget-threshold, upcoming-
  recurring, loan-due, and goal-behind-pace rules; each rule checks for an
  existing unread `Notification` of the same type/entity before creating a
  new one, so repeated sweeps don't spam duplicates.

## 18. Notification Architecture

`Notification(user, household, type, payload: JSON, read_at)`. Types map 1:1
to the rule-based triggers in §17 (budget_exceeded, budget_approaching,
recurring_due_soon, loan_payment_due, goal_behind_pace, unusual_expense).
`payload` carries the structured data the frontend needs to render the
message (amounts, entity id) rather than a pre-rendered string, so copy can
change without a migration. In-app only for V1 (bell icon + `GET
/api/notifications/`, polled or refetched on window focus); email delivery
is a documented extension point (the Celery task that creates the
Notification is the natural place to also enqueue an email task) but not
built, to avoid needing a transactional-email provider for a portfolio demo.

## 19. Audit Logging

`AuditLogEntry(user, household, action, entity_type, entity_id, metadata:
JSON, created_at)`. Written by explicit `audit.log(...)` calls inside each
app's `services.py` (see §9's reasoning vs. signals) for: transaction
create/update/delete, budget change, loan payment recorded, household member
added/removed, role changed. `metadata` stores a diff (`{field:
{old, new}}`) for updates and the full row for deletes, so an audit entry is
enough to reconstruct what happened without needing the (hard-)deleted row.

## 20. Testing Strategy

Continues the existing pattern (pytest + pytest-django + factory_boy, one
`tests/factories.py` + `tests/test_*.py` per app, cross-tenant isolation
always asserted as 404-not-403). Priorities, matching "test business-critical
logic, not coverage numbers":

- **Backend:** model constraint tests (unique/check constraints actually
  reject bad data); service-layer tests for every calculation (budget
  utilization, amortization schedule, forecast projection, recurring
  generation idempotency under a simulated double-run); API tests for every
  household-isolation boundary and every role-gated action; a CSV import test
  with a deliberately malformed file.
- **Frontend:** Vitest + React Testing Library for components with real
  logic (MoneyInput formatting/parsing, budget progress bar thresholds);
  hook tests for the TanStack Query hooks against MSW-mocked responses; RHF
  validation tests for the transaction and CSV-mapping forms; one Playwright
  (or RTL-level) smoke test for the golden path (register → create household
  → add account → record transaction → see it on dashboard).

## 21. Docker Architecture (not built yet)

`docker-compose.yml` services: `frontend` (Vite dev server), `backend`
(Django, gunicorn in a prod-target stage), `postgres`, `redis`,
`celery-worker`, `celery-beat`. `.env.example` already assumes Compose
service names (`DB_HOST=db`) — actual compose file + Dockerfiles are the
next infra task once the API surface stabilizes past MVP, so the image
doesn't need rebuilding every time a new app is added.

## 22. CI/CD Strategy

GitHub Actions on PR: backend (`ruff` lint, `pytest` against a real
`postgres:16` service container — not sqlite, so CI matches prod behavior on
things sqlite is lenient about), frontend (`eslint`, `tsc --noEmit`,
`vitest run`), and a Docker build check. No auto-deploy — deployment is
documented (§23) but triggered manually, since this is a portfolio project
without a paying user base that needs zero-downtime releases.

## 23. Deployment Strategy (documented, not necessarily run continuously)

Backend + Postgres + Redis + Celery worker/beat on a PaaS with managed
Postgres/Redis (Render or Railway — cheaper/simpler than hand-rolling ECS for
a portfolio deploy); frontend as a static Vite build on Vercel/Netlify/
Cloudflare Pages. Secrets via each platform's env-var store, never committed.
Migrations run as a release-phase step, not on container boot (avoids two
replicas racing to migrate simultaneously). Given always-on hosting costs
money for a demo project, also plan a **seeded demo mode** (§30) so the app
doesn't need to run 24/7 to be reviewable.

## 24. Security Considerations

Builds on what's already in place: generic auth error messages (no email
enumeration), login throttled 10/min, `AUTH_PASSWORD_VALIDATORS`, httpOnly
refresh cookie, `Secure`/`SameSite=Lax` in non-DEBUG. Gaps to close in V1:
throttle scopes for **registration** and **password reset** too (only login
is throttled today); CSV upload validation (max file size, `.csv` extension
+ content-sniff, row-count cap before it even reaches Celery); consistent
household-scoped 404s extended to every new app via
`HouseholdScopedModelViewSet` (§9), not re-implemented per app; DRF's
built-in serializer validation plus the ORM's parameterized queries are the
SQL-injection defense (no raw SQL planned anywhere in this design); React's
default escaping plus MUI components is the XSS defense — the one place to
watch is CSV-imported free-text `description` fields rendered later in the
UI, which need the same escaping as any other user input (no special
handling needed if nothing bypasses React's default rendering, but worth a
explicit test given the data enters via a file, not a form).

## 25. Performance Considerations

Indexes as listed in §8 (`account_id+date`, `household_id+date` on
Transaction) support the two dominant query patterns (account ledger,
household activity feed). `select_related('category', 'account')` on every
transaction list endpoint to avoid N+1. Dashboard summary is **one endpoint
issuing a small fixed set of aggregate queries**, not N widgets each firing
their own request — the spec's chart list (6+ charts) must not become 6+
round trips. Computed balances revisited only if profiling under realistic
seed data (§27) shows it's actually slow — not optimized preemptively.

## 26. Portfolio Differentiators

Ranked by interview value vs. effort, given the stack already chosen:

1. **Recurring transaction engine with idempotent generation** — small
   surface area, but the unique-constraint-backed idempotency (§17) is a
   concrete, defensible answer to "how do you guarantee a Celery task retry
   doesn't double-charge someone," which is a real distributed-systems
   question interviewers ask.
2. **Household permission model** — multi-tenant row-level isolation +
   RBAC is exactly the kind of thing SaaS interviews probe ("how do you
   guarantee household A can never see household B's data, even via a bug").
3. **Financial forecasting engine** — simple math, but demonstrates you can
   turn ambiguous requirements ("project my savings") into an explained,
   bounded algorithm rather than either skipping it or overselling it as ML.
4. **CSV import + duplicate reconciliation** — real-world messy-data
   handling; the ±2-day fuzzy-match duplicate heuristic is a good "how would
   you improve this" discussion (embeddings on description text, ML
   classifier, etc. — v2 ideas, not needed now).
5. **Loan amortization + payoff simulation** — self-contained financial math
   that's easy to demo visually and easy to unit-test exhaustively (a strong
   "show me a test you're proud of" answer).

Audit logging and notifications are worth building (they round out the
feature set) but rank lower for interview differentiation — they're common
enough patterns that most senior candidates could sketch them without having
built this specific project.

## 27. Suggested Development Phases

| Step | Scope | Status |
|---|---|---|
| 1 | Users/Auth (custom email user, JWT+cookie, register/login/refresh/logout/me) | **Done** |
| 2 | Accounts + Categories (incl. system category seed) | **Done** |
| 3 | **Households** (model, membership, roles, invitations, permission class) | Next |
| 4 | Transactions (income/expense/transfer, personal/shared, filtering) | Planned |
| 5 | Budgets (monthly, utilization calc, service-layer tests) | Planned |
| 6 | Dashboard v1 (summary endpoint, 4 core charts, 3 rule-based insights) — **MVP complete here** | Planned |
| 7 | Recurring transactions + Celery/Redis wired up | Planned |
| 8 | Loans + amortization | Planned |
| 9 | Savings goals | Planned |
| 10 | Forecasting engine | Planned |
| 11 | CSV import | Planned |
| 12 | Notifications (Celery beat sweep) | Planned |
| 13 | Audit logging (retrofitted into services from steps 3–12) | Planned |
| 14 | Docker Compose + CI | Planned |
| 15 | Frontend build — **start this in parallel once Step 4 lands**, not after Step 13; the API contract is stable enough by then and building UI against a real (if partial) backend beats building it last | Planned |
| 16 | Docs polish: README, ADRs, ERD image, screenshots, seeded demo data | Planned |

Frontend deliberately isn't "last" — building 8 backend modules before any
UI exists risks discovering API-shape mistakes only once the frontend needs
them. Starting frontend after Transactions (Step 4) means Auth, Households,
Accounts, Categories, and Transactions — enough for a real user flow — get
UI-validated early, and every backend module after that gets a frontend
feature folder added incrementally.

## 28. Git Branch & Commit Strategy

Repo isn't git-initialized yet — that's an action item, not done silently.
Recommended once you confirm: trunk-based, `main` always deployable,
short-lived `feat/<step-name>` branches per phase step above (e.g.
`feat/households`), Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`,
`chore:`), PR-per-step even solo — self-review via diff before merge is a
cheap habit that also produces a clean, narratable commit history for the
portfolio's git log itself.

## 29. Interview Discussion Points

- **Why UUID PKs everywhere?** Financial record IDs shouldn't be
  sequentially guessable (an incrementing `transaction_id` leaks how many
  transactions exist and lets IDOR attempts enumerate); the cost is a larger
  index than `bigint`, acceptable at this scale.
- **Why Decimal, never float?** Binary floats can't represent most base-10
  fractions exactly (`0.1 + 0.2 != 0.3`); errors compound across thousands of
  transactions. `Decimal` with a fixed scale is exact and matches how
  currency is actually defined.
- **Why compute balance instead of storing it?** A stored balance is a
  second source of truth that can silently drift if any write path forgets
  to update it — computing from the transaction ledger means the balance is
  *always* correct by construction, at the cost of an aggregate query.
- **How do you isolate household data?** Every queryset is scoped at the ORM
  level (`HouseholdScopedModelViewSet`), and unauthorized access returns 404,
  not 403 — the API never confirms another household's record exists at all.
- **How does the recurring engine avoid duplicates?** A unique DB constraint
  on `(recurring_transaction, due_date)` backstops the idempotency — even if
  the Celery task itself is buggy or retried, the database physically
  rejects the duplicate insert.
- **How do you prevent duplicate CSV imports?** Fuzzy match on
  `(account, amount, date±2days)` against existing transactions, surfaced to
  the user as a flag rather than a silent skip — false positives are cheap
  to dismiss, false negatives (a real duplicate silently imported) aren't.
- **How would you scale to 1M transactions?** The two indexes in §8 already
  target the real query patterns; beyond that, partition `transactions` by
  `household_id` or by month, and move the dashboard's aggregates to a
  materialized view refreshed by Celery rather than computed live on every
  request.
- **JWT vs. session cookies?** Hybrid: refresh token httpOnly-cookie
  (unreadable by JS, mitigates XSS token theft), access token in-memory
  (short-lived, never persisted) — keeps the API stateless for the access
  path while keeping the long-lived credential off anything JS can read.

## 30. Risks and Tradeoffs

- **Household retrofit (biggest risk):** Transactions, Budgets, Dashboard,
  and Insights all depend on the household model that doesn't exist yet.
  Addressed by inserting it as Step 3, before anything else touches
  household-scoped data — building Transactions against a household FK that
  exists from day one is far cheaper than adding household-awareness to an
  already-built Transaction model later.
- **Scope (17 modules) vs. solo timeline:** the full spec is large for a
  portfolio project. The MVP/V1 split in §4 is the mitigation — ship a real
  working core (Steps 1–6) before spending time on breadth. If time runs
  short later, cut from the bottom of §26's ranking (notifications, audit
  log) before cutting the top (forecasting, recurring, households).
- **Computed-balance query cost at real scale:** acceptable now, needs
  revisiting only if profiling under seed data (10k+ transactions) shows it
  matters — flagged so it isn't silently "fixed" prematurely.
- **Operational cost of always-on Celery/Redis/Postgres for a portfolio
  demo:** running four services continuously costs money for something
  reviewers may open twice a year. Mitigation: ship a seeded demo mode
  (fixture data + read-only or a demo login) so the live deploy doesn't need
  Celery running 24/7 to look complete — background jobs can be demoed via
  a "run now" admin action or a recorded screenshot/GIF instead of a live
  scheduler, without weakening the code itself as a portfolio artifact.
- **CSV duplicate-detection false negatives:** the ±2-day window is a
  heuristic, not a guarantee — worth stating explicitly in the UI ("possible
  duplicates flagged, please review") rather than implying certainty.
