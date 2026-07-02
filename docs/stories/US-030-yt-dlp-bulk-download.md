# US-030: yt-dlp Bulk Download Service

## Status

implemented

## Lane

high-risk

## Product Contract

Implement Module **M3 (Ingestion)** bulk download flow for approved keyword
cascades. After channel discovery/subscribe completes, fetch recent videos and
persist downloaded assets for review.

**Epic:** E06 Ingestion  
**Roadmap:** R3 — M3 ingestion (`docs/superpowers/plans/2026-07-02-r3-ingestion.md`)

## Relevant Product Docs

- `docs/product/workflows.md` — M3 ingestion lifecycle
- `docs/superpowers/specs/2026-07-02-videoscout-workflow-design.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- New schema adds `video_assets` and `download_jobs`
- Download service wraps yt-dlp with test-friendly injection
- Bulk worker fetches up to 5 recent videos per channel in 7 days
- Duplicate `youtube_video_id` rows are skipped
- Cascade flow creates a bulk download job automatically after subscribe
- API exposes download job status and video asset listing

## Validation

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/ -v
```

## Harness Delta

- Story registered in Harness as high-risk
- Matrix evidence updated after full API suite run
