# US-013: Web Experiments & Performance Report UI

## Status

planned

## Lane

normal

## Product Contract

Extend the web `/insights` surface so operators can submit TikTok performance
reports and review keyword experiments without the deprecated PyQt6 desktop UI.
Completes Module **M1 (Keyword Intelligence)** operator-facing workflow on the
browser stack started in US-003.

**Epic:** E04 Keyword Intelligence v2  
**Roadmap:** R1 — M1 complete (`docs/superpowers/plans/2026-07-02-r1-keyword-intelligence-v2.md`)

## Relevant Product Docs

- `docs/product/workflows.md` — Module M1, daily workflow Steps 1 and 6
- `docs/product/keyword-experiments.md` — start experiment, report results (web steps)
- `docs/superpowers/plans/2026-07-02-r1-keyword-intelligence-v2.md` — Task 6
- `docs/decisions/0008-web-only-fastapi-postgresql.md`
- `web/README.md`

## Acceptance Criteria

- API client methods: `submitPerformanceReport`, `listExperiments` in `web/src/lib/api/client.ts`
- Types for performance report payload and experiment list in `web/src/lib/api/types.ts`
- `performance-report-form.tsx` on `/insights` — fields: keyword (select from approved suggestions or free text), views, likes, comments, followers_gained, outcome
- Recent experiments table on `/insights` showing `in_progress` and reported experiments
- Form submits to `POST /api/v1/performance/reports`; table loads from `GET /api/v1/experiments`
- `npm run build` and `npm run lint` pass with no errors
- Completing US-013 marks E04 R1 deliverable ready for closeout (Task 7 docs)

## Design Notes

- **Commands:** None
- **Queries:** TanStack Query for experiments list and report submission
- **API:** Consumes US-010 experiments API and US-012 performance API
- **Tables:** None (frontend only)
- **Domain rules:** Match backend outcome enum and experiment status filters
- **UI surfaces:** `web/src/components/insights/performance-report-form.tsx`, extend `insights-page.tsx`

## Validation

```bash
cd web && npm run build && npm run lint
```

| Layer | Expected proof |
| --- | --- |
| Unit | Component renders (optional) |
| Integration | API client typed methods compile |
| E2E | Manual: submit report, see experiment list update |
| Platform | `npm run build && npm run lint` clean |
| Release | Harness story update; E04 R1 web proof |

Harness update on completion:

```bash
scripts/bin/harness-cli story update --id US-013 --status implemented \
  --unit 0 --integration 0 --e2e 0 --platform 1 \
  --verify "cd web && npm run build && npm run lint"
```

## Harness Delta

- Registered via Task 1: story add US-013
- Verify command: `cd web && npm run build && npm run lint`

## Evidence

_Add commands, reports, or links after validation exists._
