# US-040: Daily Batch Review UI (`/batch`)

## Status

implemented

## Lane

normal

## Product Contract

Implement Module **M3b (Batch Review)** — operator reviews downloaded videos once
per day with **Keep** (→ merge pool) or **Skip** (excluded).

**Epic:** E07 Batch & Merge  
**Roadmap:** R4 — M3b batch review (`docs/superpowers/plans/2026-07-02-r4-batch-review.md`)

## Relevant Product Docs

- `docs/product/workflows.md` — daily operator step 3
- `docs/superpowers/specs/2026-07-02-videoscout-workflow-design.md` — M3b section

## Acceptance Criteria

- `GET /api/v1/batch` lists downloaded videos with channel name, keyword, thumbnail
- `POST /api/v1/videos/{id}/review` accepts `keep` | `skip`
- Bulk review endpoint for multi-select
- Web route `/batch` with grid, tabs (Pending / Kept / Skipped), Keep/Skip actions
- Nav link in app shell

## Validation

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/ -v
```

## Harness Delta

- Story registered in Harness matrix
- Matrix evidence updated after full API suite run
