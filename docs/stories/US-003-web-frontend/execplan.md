# US-003 Execution Plan

Retroactive plan — phases reflect work already implemented.

## Phase 1: Scaffold (DONE)

- Next.js 16 App Router + TypeScript + Tailwind
- Root layout, globals, Geist fonts
- `Providers` with React Query defaults

**Files:**

- `web/package.json`, `next.config.ts`, `tsconfig.json`
- `web/src/app/layout.tsx`, `globals.css`
- `web/src/lib/providers.tsx`

**Acceptance:**

- `npm run dev` starts on 3000

## Phase 2: API Layer (DONE)

- Typed `api` object covering all US-002 endpoints
- Shared types matching backend schemas
- `ApiError` for failed responses

**Files:**

- `web/src/lib/api/client.ts`
- `web/src/lib/api/types.ts`
- `web/.env.local.example`

**Acceptance:**

- TypeScript compiles without API type errors

## Phase 3: Layout Shell (DONE)

- Sidebar navigation with 4 routes
- Active link highlighting
- Wrap all pages in `AppShell`

**Files:**

- `web/src/components/layout/app-shell.tsx`

**Acceptance:**

- Nav links route correctly

## Phase 4: Inbox Page (DONE)

- Status tabs + search + table
- Bulk approve/reject with selection
- Reject modal (reason + note)
- Report dialog (views, likes, outcome)
- Improve action per row

**Files:**

- `web/src/app/today/page.tsx`
- `web/src/components/inbox/inbox-page.tsx`
- `web/src/components/inbox/reject-modal.tsx`
- `web/src/components/inbox/report-dialog.tsx`
- `web/src/components/shared/score-badge.tsx`

**Acceptance:**

- Full suggestion lifecycle operable against live API

## Phase 5: Sources Page (DONE)

- Channel list with scan toggle
- Add channel by YouTube ID
- Delete channel
- Manual scan trigger

**Files:**

- `web/src/app/sources/page.tsx`
- `web/src/components/sources/sources-page.tsx`

**Acceptance:**

- CRUD + scan mutation succeed

## Phase 6: Settings Page (DONE)

- Weight sliders (0–1, step 0.05)
- Niche topics comma-separated input
- Save via PUT settings

**Files:**

- `web/src/app/settings/page.tsx`
- `web/src/components/settings/settings-page.tsx`

**Acceptance:**

- Settings persist after reload

## Phase 7: Insights Page (DONE)

- Summary metrics grid
- Rejection + success pattern lists
- Run learning cycle button

**Files:**

- `web/src/app/insights/page.tsx`
- `web/src/components/insights/insights-page.tsx`

**Acceptance:**

- Insights load; cycle mutation refreshes data

## Phase 8: Validation & Harness (DONE)

- Build + lint proof
- Story packet + harness-cli registration
- Home redirect `/` → `/today`

**Files:**

- `web/README.md`
- `docs/stories/US-003-web-frontend/*`

**Acceptance:**

- `npm run build && npm run lint` pass (2026-07-02)

## Pending

- **US-004:** Playwright E2E for 4 routes
- Auth gate before production
- Component tests for inbox mutations
