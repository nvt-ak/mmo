# US-075 Channel Content Relevance Gate

## Status

planned

## Lane

high-risk

**Risk flags:**
- External systems — requires additional YouTube Data API calls (`playlistItems` + `videos`) per candidate channel.
- Existing behavior — changes which channels get subscribed on keyword approve; may reduce cascade success rate.
- Public contracts — additive `KeywordCascadeJobModel.status` value possible.
- Weak proof — needs new mocked-API integration tests for relevance pass/fail paths.
- Multi-domain — touches channel discovery, cascade worker, and quota/accounting.

Scope narrowed to: after discovering channels by keyword, verify keyword appears in recent video titles/descriptions before subscribing.

## Product Contract

When a keyword is approved, VideoScout discovers YouTube channels and subscribes top candidates. The current `_score_channel()` only measures channel size/engagement (subs, avg views, lifetime video count, view/sub ratio); it does not verify that the channel actually publishes content related to the keyword. This story adds a **content relevance gate**: for each candidate channel, fetch recent videos and check whether the keyword (or a normalized variant) appears in titles/descriptions. Only channels that pass both the existing `discovery_score` threshold and the new relevance threshold are subscribed.

Relevant product contract: `docs/product/workflows.md` (M2 Channel Discovery, M3 Ingestion).

## Relevant Product Docs

- `docs/product/workflows.md`
- `docs/stories/US-020-discover-channels-by-keyword.md`
- `docs/stories/US-021-keyword-approve-cascade.md`
- `docs/stories/US-074-channel-discovery-min-score-threshold.md`

## Acceptance Criteria

- [ ] `channel_discovery.py` provides a helper to fetch a channel's recent video metadata (title + description) and compute keyword relevance.
- [ ] Relevance is computed by checking if keyword tokens appear contiguously or with high token overlap in recent video titles/descriptions (reuse existing normalization helpers from `nurture_scorer.py` where appropriate).
- [ ] A minimum `CHANNEL_RELEVANCE_THRESHOLD` constant (default 0.5) is defined and documented.
- [ ] `keyword_cascade.py` applies the relevance gate to each candidate **after** the `discovery_score` gate; only channels passing both gates are subscribed.
- [ ] `channels_discovered` remains the raw count from YouTube search; `channels_subscribed` counts channels passing both gates.
- [ ] If zero channels pass both gates, cascade job status is set to `"completed_no_relevant_source"` and no download job is created.
- [ ] A new Alembic migration expands the `keyword_cascade_jobs.status` CHECK constraint to include `'completed_no_relevant_source'`.
- [ ] Model and schema updated consistently.
- [ ] Integration tests cover: (a) channel with high `discovery_score` but low content relevance is filtered, (b) channel with high `discovery_score` and matching recent content is subscribed, (c) zero relevant channels produces `completed_no_relevant_source`.

## Design Notes

- **Commands:** None.
- **Queries:**
  - Reuse `YouTubeService.get_recent_videos(channel_id, days=30, max_results=10)` to fetch recent content.
  - Consider caching per-channel recent videos to avoid duplicate API calls when multiple keywords cascade near the same time.
- **API:** Additive enum value `"completed_no_relevant_source"` on `KeywordCascadeJobModel.status`; `CascadeJobResponse` already exposes `status` so no schema change required.
- **Tables:**
  - `keyword_cascade_jobs.status` CHECK constraint expanded via new Alembic migration.
  - `videoscout/db/models.py` updated to match.
- **Domain rules:**
  - Relevance gate runs **after** discovery-score gate to minimize unnecessary API calls.
  - A channel is relevant if at least one recent video title/description matches the keyword with token overlap ≥ threshold or contiguous phrase match.
  - Generic tokens (e.g., "viral", "trend", "video") should not count toward relevance.
  - If a channel has zero recent videos (e.g., dormant channel), relevance = 0.
- **UI surfaces:** Dashboard already shows cascade job status; new status renders distinctly.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-075 --unit 0 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Tests for relevance helper: exact match, partial match, generic-token exclusion, no recent videos → 0. |
| Integration | `test_channel_cascade.py` (or new module) tests the full cascade with mocked YouTube responses: high-score/irrelevant channel rejected; high-score/relevant channel subscribed; all rejected → `completed_no_relevant_source`. |
| E2E | Not required. |
| Platform | Not required. |
| Release | None. |

## Harness Delta

- New story added to `docs/stories/backlog.md` under Epic E05 (Channel Cascade).
- Builds on US-074 (min discovery score threshold); consider combining tuning of both thresholds once operational data is available.

## Evidence

To be added after implementation.
