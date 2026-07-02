# US-021: Keyword Approve Cascade Job

## Status

implemented

## Lane

high-risk

## Product Contract

When operators approve keywords, automatically trigger background cascade jobs
that discover channels, subscribe internally, and persist job state for
observability.

**Epic:** E05 Channel Cascade  
**Roadmap:** R2 — M2 cascade (`docs/superpowers/plans/2026-07-02-r2-channel-cascade.md`)

## Relevant Product Docs

- `docs/product/workflows.md` — Step 2 automation contract
- `docs/superpowers/plans/2026-07-02-r2-channel-cascade.md`
- `docs/ARCHITECTURE.md`
- `docs/decisions/0010-channel-cascade-discovery-subscribe.md`

## Acceptance Criteria

- New schema supports `keyword_cascade_jobs` and `channel_keyword_links`
- `bulk_approve` triggers FastAPI background cascade work only for newly approved
  suggestions
- `GET /api/v1/cascade/jobs/{job_id}` returns job status and counters
- Worker records status transitions: `started | running | completed | failed`
- Job stores discovered/subscribed counts and error details on failures
- Integration tests verify end-to-end cascade behavior with mocked YouTube API
- Scope excludes download/yt-dlp (R3)

## Validation

```bash
python -m pytest videoscout/tests_api/test_channel_cascade.py -v
python -m pytest videoscout/tests_api/ -v
```

## Harness Delta

- Story registered in Harness as high-risk
- Verify command updated to the suite command for R2 completion
