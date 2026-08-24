# CashPulse — Frontend

React + TypeScript (Vite). Built so far: the core app shell (routing,
theming, providers) and five features — Auth (register/login/logout, JWT
access-token-in-memory + httpOnly-refresh-cookie handling), Households
(list, create, switch active household), Accounts (CRUD, deactivate,
computed balance display), Categories (system-category tree + custom
categories, income/expense grouped), and Transactions (income/expense/
transfer, filtering, household-scoped via the active household switcher).
Everything else (Budgets, Dashboard, Recurring, Loans, Savings,
Forecasting, Imports, Notifications) has a working, tested backend
(`/backend`) but no UI yet.

Verified end-to-end in a real (headless) browser against the actual
backend, not just asserted in unit tests: register → create accounts →
record income/expense/transfer transactions → confirm computed account
balances are correct → edit a transaction. Same flow re-verified through
the real Docker Compose stack once Docker was available.

## Stack

- **React 19 + TypeScript**, Vite for dev/build
- **TanStack Query** for all server state (queries/mutations against the API)
- **Redux Toolkit** — one slice (`session`): current user + active household id.
  Deliberately *not* auth-token storage (see Architecture notes)
- **React Router** for routing, **React Hook Form + zod** for forms
- **MUI** for components, **axios** for the API client, **dayjs** for dates
- **Vitest + React Testing Library + MSW** for tests

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000/api
npm run dev
```

Needs the backend running too — see `/backend/README.md`. Or run both
together: `docker compose up --build` from the repo root.

```bash
npm run typecheck   # tsc -b --noEmit
npm run lint        # oxlint
npm run test         # vitest run
npm run build        # tsc -b && vite build
```

## Project structure

```
src/
├── app/            # store.ts (the one Redux slice + createStore factory), hooks.ts
├── api/            # client.ts (axios + refresh-token interceptor), tokenStore.ts, auth.ts
├── features/       # auth/, households/, accounts/, categories/, transactions/
│                   #   each: components, hooks.ts, api.ts, types.ts, schemas.ts
├── components/     # shared: AppLayout, ProtectedRoute, GuestRoute, SessionExpiredHandler
├── pages/          # route-level composition of feature components
├── hooks/          # cross-feature: useCurrentUser, useActiveHousehold
├── types/          # shared types only (Money, ISODate, User, ...)
└── lib/            # queryClient, theme, dayjs config, apiErrors adapter, money formatting
```

## Architecture notes worth knowing

- **Access token in memory, refresh token in an httpOnly cookie** —
  `api/tokenStore.ts` holds the access token in a plain module variable,
  never in Redux/localStorage. `api/client.ts`'s response interceptor
  catches a 401, calls `/auth/refresh/` (using the cookie the browser
  sends automatically), retries the original request once, and only
  bounces to `/login` if the refresh itself fails. Concurrent 401s share
  one in-flight refresh call rather than each firing their own.
- **`useBootstrapSession`** (features/auth/hooks.ts) runs once at app
  boot and calls `/auth/me/`. On a fresh page load there's no access
  token yet, so this 401s immediately — that's expected, not a bug — and
  the interceptor's silent-refresh-via-cookie either restores the
  session or leaves the user logged out. Verified against the real
  backend in a headless-Chromium run (register → dashboard → create
  household → switch household → log out → back to `/login`), not just
  asserted in tests.
- **Redux holds `user`/`activeHouseholdId`, not the token** — the slice
  is called `session` because that's the *concept*, but the actual JWT
  never touches Redux/persisted storage; only its presence (the user
  object) does. This matches the backend's own reasoning for keeping the
  refresh token in an httpOnly cookie: a value XSS can't read can't be
  stolen by XSS.
- **One error adapter** (`lib/apiErrors.ts`) for every form — DRF only
  ever returns `{field: [messages]}` or a top-level `detail`/
  `non_field_errors`, so there's exactly one place that turns an axios
  error into `{fieldErrors, message}` for `setError()` + a top-level alert.
- **`oxlint`, not `eslint`** — the current `npm create vite` scaffold
  ships oxlint by default; it does the same job (catch obvious
  mistakes) faster, so it wasn't swapped out just to match older
  tooling conventions.
- **Test isolation**: `app/store.ts` exports both the app's singleton
  `store` and a `createStore()` factory; `testUtils.tsx`'s
  `renderWithProviders` always uses a fresh store + QueryClient per
  test, so logging in during one test can't leak into the next.
  `testSetup.ts` calls Testing Library's `cleanup()` by hand in
  `afterEach` — Vitest's `globals: false` (kept so every test file's
  imports stay explicit) means Testing Library's usual auto-registration
  of that cleanup doesn't fire on its own.
- **`features/categories/api.ts::fetchCategories` follows pagination** —
  the seed data alone is ~29 system categories, already past the API's
  default page size (25), so this is the one list in the app that can't
  just read page 1 and call it done; every other list (accounts,
  households) is short enough that it doesn't matter yet.
- **`features/transactions/schemas.ts`** mirrors `Transaction.clean()`/
  `TransactionSerializer.validate()` server-side: a transfer needs a
  different destination account and no category; income/expense need a
  category and no destination account. Same shape-validation duplication
  the backend itself uses (serializer + model), just on the other side
  of the wire.
- **Transactions are scoped by the active household switcher, not a
  separate filter control** — `TransactionsPage` derives `{household:
  activeHouseholdId}` or `{is_shared: false}` from Redux's
  `activeHouseholdId` rather than exposing its own household filter,
  keeping "which household am I looking at" a single, consistent piece
  of UI (the top-bar switcher) instead of two things that could disagree.
- **MUI v9 dropped `Stack`'s system-prop shorthands** (`justifyContent=`,
  `alignItems=`, `mb=` as direct props no longer type-check) — every
  `Stack` in this codebase uses `sx={{ ... }}` for those instead. Found
  via a real `tsc` error, not assumed from older MUI docs.

## What's next

Budgets + Dashboard are the natural next slice — Budgets because it's a
straightforward CRUD feature, and a real Dashboard (charts, insights)
only makes sense once there's actual transaction data to summarize,
which now exists. See `/BLUEPRINT.md` for the full list of backend
modules still needing a UI (Recurring, Loans, Savings, Forecasting,
Imports, Notifications).
