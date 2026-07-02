# US-031: Channel New-Video Watcher

## Status

implemented

## Lane

normal

## Product Contract

Implement M3 channel watcher that scans subscribed channels periodically and
queues downloads for newly uploaded videos not already stored in `video_assets`.

**Epic:** E06 Ingestion  
**Roadmap:** R3 — M3 ingestion (`docs/superpowers/plans/2026-07-02-r3-ingestion.md`)

## Relevant Product Docs

- `docs/product/workflows.md` — M3 ingestion and auto-monitoring
- `docs/superpowers/specs/2026-07-02-videoscout-workflow-design.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- New watcher worker scans channels with `scan_enabled=true`
- Detects new uploads since `last_scan_at` and skips known `youtube_video_id`
- Creates watcher `download_jobs` and runs ingestion for those new video IDs
- APScheduler registers watcher task every 6 hours

## Validation

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/ -v
```

## Harness Delta

- Story registered in Harness as normal lane
- Matrix evidence updated after full API suite run
