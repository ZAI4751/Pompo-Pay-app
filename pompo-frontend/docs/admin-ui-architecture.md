# Pompo Master Admin — Frontend Architecture

Separate application from `pompo-backend`, intended to sit alongside it as
`pompo-admin/`. This document is the map for anyone (including future-me)
picking this codebase back up.

## Stack and why

- **Next.js 16 (App Router) + React 18 + TypeScript.** Chosen for real
  architectural value, not fashion: file-based routing maps directly onto
  the nav information architecture below, layouts give us auth-gating and
  the persistent sidebar/topbar for free, and Server/Client Component
  separation is a natural fit for a dashboard that's mostly data tables.
- **Started on Next 14.2.15, upgraded to 16.3.3 during this build.** `npm
  install` flagged that 14.2.15 carries a critical DoS advisory and several
  other CVEs with a patched major already available; shipping a
  known-vulnerable framework version in a fintech admin tool isn't
  defensible just because it was the initially-planned pin. Verified `npm
  audit` reports 0 vulnerabilities after the upgrade.
- **Tailwind CSS 3**, driven entirely by CSS variables (see "Design
  tokens" below) rather than hardcoded colors in component classes.
- **next-themes** for light/dark switching (class-based, SSR-safe).
- **lucide-react** for icons, **clsx** + **tailwind-merge** for the `cn()`
  className utility used by every component.
- No state management library. Server-derived UI state is per-page
  `useState` + a plain typed service call (see "Mock/API boundary"); the
  only genuinely cross-cutting client state is auth (`AuthContext`) and
  toasts (`ToastProvider`) — both plain React Context, not because a
  library was rejected on principle, but because two small pieces of state
  didn't earn one.

## Project structure

```
pompo-admin/
├── src/
│   ├── app/                    # App Router pages
│   │   ├── login/page.tsx
│   │   ├── (app)/              # route group: authenticated shell
│   │   │   ├── layout.tsx      # auth-gates every child route
│   │   │   ├── dashboard/
│   │   │   ├── merchants/
│   │   │   ├── users/
│   │   │   ├── roles/
│   │   │   │   └── [id]/
│   │   │   ├── permissions/
│   │   │   └── ...             # 17 "coming soon" stub routes
│   │   ├── layout.tsx           # root layout, providers
│   │   └── globals.css          # design tokens
│   ├── components/
│   │   ├── ui/                  # design-system primitives
│   │   └── layout/               # Sidebar, TopBar, PageShell, nav-config
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts         # fetch wrapper (real backend calls)
│   │   │   ├── config.ts         # API_BASE_URL, USE_MOCKS from env
│   │   │   └── services/         # one file per resource
│   │   ├── auth/                 # AuthContext, usePermissions
│   │   ├── types/                 # one file per domain concept
│   │   └── utils/cn.ts
│   └── mocks/data.ts              # typed demo data
└── docs/admin-ui-architecture.md  # this file
```

## Design tokens

Every color is a CSS variable defined once in `src/app/globals.css`,
referenced from `tailwind.config.ts`, never hardcoded in a component.
Light mode and dark mode are two separate variable sets (`:root` and
`.dark`) — **dark mode is a real pitch-black theme**, not an inverted
light theme, per the brand spec.

| Token | Light | Dark | Use |
|---|---|---|---|
| `primary` | `#2E90E5` | `#4FA3F2` (brightened for contrast on black) | Brand actions, active nav, links |
| `dark-blue` | `#0B2545` | `#14335C` | Secondary brand accent (avatar fill, etc.) |
| `background` | `#F7F9FB` | `#000000` | App canvas |
| `surface` | `#FFFFFF` | `#0B0D10` | Cards, tables, sidebar |
| `text` / `text-muted` / `text-subtle` | `#101828` / `#4B5768` / `#8A94A6` | `#F2F4F7` / `#A0A8B4` / `#6B7280` | Three-tier text hierarchy |
| `success` / `warning` / `error` / `info` | — | — | Status only, always secondary to brand blues |

`background` is a hair off-white rather than pure `#FFFFFF` specifically
so white `surface` cards still read as a distinct layer against it — pure
white-on-white gave zero hierarchy. This is the one deliberate departure
from a literal reading of "BASE: White"; the base tone is still white,
applied to the content layer that actually needs to look white (cards),
not the canvas behind it.

## Component system

Built in `src/components/ui/`: Button, IconButton, Input, Badge (+
StatusBadge/ActiveBadge), Card, MetricCard, Table (+Th/Td/Tr), EmptyState,
ErrorState, Skeleton (+TableSkeleton), Modal, ConfirmationDialog, Toast,
Breadcrumb, MockDataBadge, ComingSoon.

**Honest scope note:** the spec listed ~30 components (Select, MultiSelect,
DatePicker, Search, Pagination, Drawer, Tabs, Dropdown, Sidebar, TopBar,
Timeline, Chart container among them). I built the ones the actual screens
in this milestone needed and left the rest for when a real screen needs
them — writing a DatePicker or Timeline with no consumer would be
unverifiable, untested code sitting in the repo. `Sidebar`/`TopBar` exist
under `components/layout/` since they're layout, not general-purpose UI.

Every component reads colors through Tailwind's token classes
(`bg-surface`, `text-muted`, etc.) — none hardcode a hex value.

## Navigation architecture

`src/components/layout/nav-config.ts` is the single source of truth for
the sidebar. Each `NavItem` optionally carries:
- `permission` — hidden entirely if `usePermissions().hasPermission()`
  returns false (see "RBAC-aware frontend" below)
- `comingSoon` — routes to a real page rendering `<ComingSoon />` rather
  than a fake fully-built screen, with a "Soon" tag in the sidebar

This means adding a real screen later is: delete `comingSoon: true` from
one config entry, replace that route's `page.tsx` body. No layout or nav
restructuring needed — this was one of the spec's explicit constraints and
directly shaped this design.

## Mock/API boundary

`NEXT_PUBLIC_USE_MOCKS` is **true only when set to the string `"true"`**. Unset or
`false` means live `/api/v1` for every capability the backend already exposes.

**REAL API INTEGRATED**

| Capability | Contract |
|---|---|
| Auth | `POST /auth/login`, `/refresh`, `/logout`, `GET /auth/me` |
| Effective permissions | `GET /rbac/roles/{role_id}` → `permission_codes` (not on `/me`) |
| Merchants | `GET/POST /organization/merchants`, `GET/PATCH/DELETE /organization/merchants/{id}` (delete is soft) |
| Branches | `GET/POST /organization/merchants/{id}/branches`, `PATCH/DELETE /organization/branches/{id}` |
| Roles | `GET/POST /rbac/roles`, `GET/PATCH/DELETE /rbac/roles/{id}` |
| Permissions catalog | `GET /rbac/permissions`, `GET /rbac/permissions/{id}` |
| Role grants | `POST/DELETE /rbac/roles/{role_id}/permissions/{permission_id}` |
| User role assign | `PUT /rbac/users/{user_id}/role` (service exists; no user directory UI) |
| Payment by reference | `GET /payments/{reference}`, cancel, process |
| Tills | `GET/POST /organization/branches/{branch_id}/tills`, `GET/PATCH/DELETE /organization/tills/{id}` |
| Providers | `GET /payments/providers`, `GET/PATCH /payments/providers/{code}` (catalog; simulated only) |
| Health | `GET /health`, `/health/ready`, `/health/live` (503 still carries the health body) |

**MOCK / NOT YET AVAILABLE**

| Surface | Why |
|---|---|
| User list / user CRUD | No user administration API |
| Transaction/payment list | No `GET /payments` list |
| Webhooks, audit logs, API keys, reports, QR, live Airtel/TNM | Future milestones |
| Dashboard volume chart | No ledger aggregate API — labeled demo series |

When mocks are on (`NEXT_PUBLIC_USE_MOCKS=true`), live capabilities still return
labeled fixtures and login uses the demo session (no password sent). Mutations
that would persist are refused in demo mode.

Services never call `fetch` from page components. Pages consume
`src/lib/api/services/*` which return `ApiResult<T>`. Bearer tokens are attached
by `src/lib/api/session.ts`, written only by `AuthContext`.

`usePermissions()` is UX only. If `GET /rbac/roles/{id}` is forbidden (for
example a merchant owner without `roles:read`), `permissionCodes` is `null` and
the UI does **not** invent grants — gated nav stays visible so we do not hide
real capabilities, and the API still returns 403.

## Authentication architecture

`AuthContext` (`src/lib/auth/AuthContext.tsx`) owns the entire session
lifecycle:
- **Login** — calls real `/auth/login`, then real `/auth/me`, stores both
  tokens.
- **Session restore on reload** — tokens live in `sessionStorage`
  (deliberately not `localStorage`: a shared/kiosk machine shouldn't keep a
  session alive across browser restarts) under one key. On mount, tries
  `/auth/me` with the stored access token; if that fails, tries
  `/auth/refresh` once before giving up and clearing the session.
- **Logout** — calls real `/auth/logout` (revokes the refresh session
  server-side, matching the backend's M003 rotation/revocation design),
  then clears local state and redirects to `/login`.
- **Route protection** — the `(app)` route group's `layout.tsx` reads
  `status` from `AuthContext` and redirects to `/login` whenever it's
  `"unauthenticated"`, so no individual page needs its own auth check.

This is the one part of the frontend backed by a real, already-verified
backend contract, not a placeholder.

## RBAC-aware frontend

`usePermissions()` exposes `hasPermission(code)` for sidebar and mutation
affordances. **UX only.** The backend remains the sole security boundary.

`/auth/me` still does not return permission codes (schema comment is stale
relative to M004). After login the admin loads `GET /rbac/roles/{role_id}`
and uses `permission_codes`. That call requires `roles:read`, which platform
administrators have. Other roles may receive 403; the frontend then treats
permissions as unknown rather than inventing a catalog.

## 401 vs 403 semantics

Mirrors the backend's own M003/M004 distinction:
- **401 (unauthorized)** → `AuthContext` treats this as "the session is
  over" — clears state, `(app)/layout.tsx`'s redirect fires.
- **403 (forbidden)** → surfaces via `<ErrorState kind="forbidden" />`,
  which does **not** clear the session or redirect — the user is still
  authenticated, just not allowed to do this one thing.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | No (defaults to `http://localhost:8000/api/v1`) | Base URL of the FastAPI backend |
| `NEXT_PUBLIC_USE_MOCKS` | No (default live API) | `"true"` enables labeled demo fixtures and demo login |

No secrets belong in either variable or anywhere else in this codebase —
both are `NEXT_PUBLIC_*`, meaning they're bundled into client-side JS by
design. `.env.local` is gitignored; `.env.example` documents variable
names only, with no real values.

## Accessibility

- Every icon-only control (`IconButton`) requires an `aria-label` at the
  type level — omitting one is a TypeScript error, not just a lint
  warning.
- Focus is never suppressed: `:focus-visible` gets a visible brand-colored
  ring globally (`globals.css`), with no `outline: none` anywhere in the
  codebase.
- Tables use `<th scope="col">`; form inputs get programmatic
  `label`/`aria-describedby` wiring (`Input` component); modals are
  `role="dialog"` + `aria-modal` + Escape-to-close + label association.
- Not yet done: a full automated audit (axe or similar) — see "Known
  limitations."

## Verification actually performed

- `npm install` — 0 vulnerabilities (after the Next.js version fix above)
- `npm run build` — succeeds; all 26 routes compile and prerender
- `npm run typecheck` (`tsc --noEmit`) — 0 errors
- `npx eslint .` — 0 errors, 0 warnings (fixed 6 real
  `react-hooks/set-state-in-effect` findings — genuine issues, not
  suppressed: 4 were "reset state, then fetch" effects restructured so the
  synchronous reset only happens in the retry click-handler, not the mount
  effect; 1 (`AuthContext`) was fixed by moving synchronously-knowable
  initial state into a `useState` lazy initializer; 1 (`ThemeToggle`) is a
  documented, deliberate exception with an inline justification comment,
  since next-themes' own hydration-safety pattern requires it)

**Not performed** (no browser available in the environment this was
built in): visual verification of dark mode, responsive breakpoints,
keyboard-navigation walkthrough, or an automated accessibility audit.
These are the honest gaps — see "Known limitations."

## Known limitations

- `/auth/me` does not return permission codes; the admin uses `GET /rbac/roles/{id}`.
- No user directory, payment list, webhook, or audit-log APIs.
- Dashboard volume series remain labeled mock data.
- No automated frontend tests (unit or e2e) yet.

## Recommended next backend milestone (not started)

Do not start M008 (live Airtel/TNM adapters) automatically.

Highest-leverage gaps for the Master Admin:

1. Include `permission_codes` on `GET /auth/me` so merchant-scoped users do not need `roles:read`.
2. User directory (list/get) so role assignment has a real operator surface.
3. Payment/transaction list and search.
4. Live Airtel/TNM/bank adapters (M008) — not started.
