# R3 — Ingestion (M3) Implementation Plan

**Goal:** Bulk download latest videos from subscribed channels after keyword cascade; monitor channels for new uploads.

**Architecture:** `services/download.py` (yt-dlp wrapper), `workers/bulk_download.py`, extend cascade to enqueue download job, APScheduler watcher job every 6h.

**Storage:** `{VIDEOSCOUT_DATA_DIR}/downloads/{channel_id}/{video_id}.mp4`

**Stories:** US-030, US-031

**Out of scope:** batch review UI (R4), merge (R5)

## Tasks

1. Stories + harness US-030/031
2. Alembic 0005: `video_assets`, `download_jobs`
3. `services/download.py` — yt-dlp with mock-friendly interface
4. `workers/bulk_download.py` — fetch recent videos, download, persist VideoAsset
5. Extend `keyword_cascade` → enqueue bulk download after subscribe
6. Scheduler: `channel_watcher` cron (6h) — new videos → download queue
7. API: `GET /downloads/jobs/{id}`, `GET /videos`
8. Tests mock download + watcher logic
9. Docs + harness proof
