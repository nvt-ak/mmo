# US-020: Discover Channels by Keyword

## Status

implemented

## Lane

high-risk

## Product Contract

Implement Module **M2 (Channel Discovery)** keyword-to-channel discovery using the
YouTube API. For each approved keyword, discover and score relevant channels,
then expose linked channels for operator visibility.

**Epic:** E05 Channel Cascade  
**Roadmap:** R2 — M2 cascade (`docs/superpowers/plans/2026-07-02-r2-channel-cascade.md`)

## Relevant Product Docs

- `docs/product/workflows.md` — Step 2 auto discovery and subscribe
- `docs/superpowers/plans/2026-07-02-r2-channel-cascade.md`
- `docs/ARCHITECTURE.md`
- `docs/decisions/0009-keyword-led-content-factory.md`
- `docs/decisions/0010-channel-cascade-discovery-subscribe.md`

## Acceptance Criteria

- `videoscout/core_engine/channel_discovery.py` provides keyword discovery using
  YouTube API (`get_youtube_service`) and deterministic score calculation
- Discovery returns ranked channel candidates with score and channel metadata
- Worker path upserts discovered channels into `channels` table with
  `scan_enabled=True`
- Links are persisted between suggestion and discovered channels
- `GET /api/v1/suggestions/{id}/channels` returns linked channels for an approved
  suggestion
- Scope excludes download/yt-dlp (R3)

## Validation

```bash
python -m pytest videoscout/tests_api/test_channel_cascade.py -v
```

## Harness Delta

- Story registered in Harness as high-risk
- Proof command recorded via story update after implementation
