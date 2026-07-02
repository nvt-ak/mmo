# US-003: Web Frontend (Next.js Inbox)

## Story Packet

| Doc | Purpose |
| --- | --- |
| [overview.md](US-003-web-frontend/overview.md) | Problem, scope, success criteria |
| [design.md](US-003-web-frontend/design.md) | Architecture, routes, state, API client |
| [execplan.md](US-003-web-frontend/execplan.md) | Implementation phases |
| [validation.md](US-003-web-frontend/validation.md) | Proof plan + results |
| [CHANGELOG.md](US-003-web-frontend/CHANGELOG.md) | History |

## Status

implemented

## Lane

normal

## Product Contract

Operators manage the keyword suggestion workflow through a browser UI: review
today's inbox, approve/reject in bulk, report video outcomes, manage YouTube
sources, adjust scoring settings, and view learning insights.

## Relevant Product Docs

- `docs/product/PRD.md` — operator workflow
- `docs/decisions/0008-web-only-fastapi-postgresql.md`
- `docs/ARCHITECTURE.md`
- `web/README.md`

## Acceptance Criteria

- Next.js app on port 3000, redirects `/` → `/today`
- `/today` — inbox with bulk approve/reject, report dialog, improve action
- `/sources` — YouTube channel list + manual scan trigger
- `/settings` — scoring weights + niche topics
- `/insights` — learning patterns + cycle trigger
- Typed API client in `web/src/lib/api/`
- React Query for server state
- `NEXT_PUBLIC_API_URL` overrides backend URL (default localhost:8000)

## Design Notes

**Routes:** `web/src/app/{today,sources,settings,insights}/`

**Components:** `web/src/components/{inbox,sources,settings,insights,layout,shared}/`

**API client:** `web/src/lib/api/client.ts`, `types.ts`

## Validation

```bash
cd web && npm run build && npm run lint
```

| Layer | Expected proof |
| --- | --- |
| Unit | None yet (no component tests) |
| Integration | TypeScript compile + API types match backend |
| E2E | Manual browser walkthrough (4 routes) |
| Platform | `npm run build` succeeds |

Harness update:

```bash
scripts/bin/harness-cli story update --id US-003 --status implemented \
  --unit 0 --integration 0 --e2e 0 --platform 1 \
  --verify "cd web && npm run build && npm run lint"
```

## Harness Delta

- `web/README.md` — setup and run instructions
- E2E test story deferred (future US-004 or harness backlog item)

## Evidence

- `web/src/` — 4 feature pages + shared components
- Build/lint pass required before marking platform proof
- Retro alignment: 2026-07-02
