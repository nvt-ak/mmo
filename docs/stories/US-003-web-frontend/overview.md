# US-003: Web Frontend — Overview

## Current Behavior (before)

- PyQt6 desktop UI (`videoscout/ui/`) for channel scan, digest, TikTok check
- No browser-based operator workflow
- No shared API client; UI reads SQLite directly

## Target Behavior (after)

- Next.js App Router app on port 3000
- Sidebar nav: Inbox, Sources, Settings, Insights
- All actions call US-002 FastAPI backend via typed client
- Server state via TanStack React Query (cache, mutations, refetch)

## Problem Statement

ADR 0008 pivots to web-only. Operators need a daily inbox to triage keyword
suggestions without running the deprecated desktop app.

## Solution

Build 4 feature pages in `web/src/`, shared layout shell, typed API layer
matching backend `/api/v1/*` contracts.

## Scope

### In Scope

- Routes: `/today`, `/sources`, `/settings`, `/insights`
- Redirect `/` → `/today`
- Inbox: status tabs, search, bulk approve/reject, report, improve
- Sources: channel CRUD, manual scan trigger
- Settings: scoring weight sliders, niche topics
- Insights: patterns display, learning cycle trigger
- `NEXT_PUBLIC_API_URL` config

### Out of Scope

- Auth / login
- Component unit tests
- Playwright E2E (US-004)
- Mobile layout polish
- LLM API key UI (backend-only for now)
- Real-time WebSocket updates

## Success Criteria

| Criterion | Target |
| --- | --- |
| App builds | `npm run build` |
| Lint clean | `npm run lint` |
| 4 routes render | No crash with API up |
| Inbox workflow | approve, reject, report, improve |
| Sources | add/toggle/delete channel, run scan |
| Settings | save weights + topics |
| Insights | load patterns, run cycle |

## Stakeholders

- **Operator** — daily keyword triage
- **US-002 backend** — API contract provider

## Non-Goals

- PyQt6 feature parity (experiments tab, desktop notifications)
- Offline mode
- i18n (English UI only)
