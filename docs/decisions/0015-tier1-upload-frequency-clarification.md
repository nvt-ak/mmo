# 0015 Tier-1 Upload Frequency Clarification (ADR 0013 Amendment)

Date: 2026-07-13

## Status

Accepted

## Context

ADR 0013 Tier-1 enrichment table states:

> Channel in DB → subs, **upload frequency** from `ChannelModel` → `raw.channel`

US-063 shipped Tier-1 as `load_tier1_channel()` reading `ChannelModel`, but implementation only exposes:

- `subscriber_count`
- `last_video_count`
- `scan_enabled`

There is **no** `upload_frequency` column or derived field on `ChannelModel`, and `raw.channel` in TrendEvidence never includes cadence. US-063 acceptance criteria required `raw.channel` from DB when the source channel exists — not explicitly upload frequency — so the story is implemented per AC while ADR text over-promised.

Empirical review (2026-07-13) also confirmed **layer mismatch**: per-channel upload cadence is the wrong signal for M1 keyword ranking because:

1. Tier-1 only applies when the source channel is **already subscribed** — most new inbox candidates have `channel_raw = None`.
2. A trending keyword is not represented by a single channel; M1 uses **multi-creator** `supply_pressure` and search-sample `uploads_per_day` (ADR 0014 Tier-2), not one channel's cadence.
3. Adding per-channel cadence for all M1 candidates would require extra YouTube API calls at rank time — rejected in ADR 0013 ("Enrich all candidates with YouTube search — Top-N only for quota").

## Decision

1. **Amend ADR 0013 Tier-1 row** — effective contract is:
   - `subscriber_count`, `last_video_count`, `scan_enabled` from `ChannelModel` when channel exists in DB.
   - **Upload frequency is not a Tier-1 / M1 rank signal** in Phase 1.

2. **Per-channel short cadence belongs at M2** — when a specific channel is a subscribe candidate after keyword approve (`evaluate_channel_relevance` / US-076b), using `get_recent_videos` data already fetched for relevance.

3. **Search-sample `uploads_per_day`** (ADR 0014, `compute_distribution_stats`) remains the correct **keyword-level** cadence proxy — aggregate across creators in the search sample, labeled as sample bias not population truth.

4. **Optional future:** persist `shorts_per_day` on `ChannelModel` after M2 subscribe + channel watcher scans — would enable Tier-1 cache for **repeat** keywords sharing a known channel, not first-time M1 candidates. Tracked under US-076c, not US-063 retrofit.

## Alternatives Considered

1. **Add `upload_frequency` to `ChannelModel` now for Tier-1** — rejected; without M2 cadence computation and scan pipeline write, field would be stale or null for most rows.
2. **Use channel cadence in M1 Ranker** — rejected; layer mismatch and quota (see Context).
3. **Rewrite ADR 0013 silently** — rejected; explicit amendment preserves audit trail.

## Consequences

Positive:

- Closes doc/code drift flagged in US-074/075 review pattern (ADR promises vs shipped fields).
- Clear separation: M1 opportunity signals vs M2 source durability signals.

Tradeoffs:

- Operators cannot see source-channel cadence in inbox insights until US-076b ships on cascade path.
- Tier-1 remains thin until optional `ChannelModel` persist (US-076c).

## Follow-Up

| Item | Story |
| --- | --- |
| M2 short cadence bonus | US-076b |
| Discover-time cadence + `_score_channel` fix | US-076c (draft) |
| Aggregate durability / dependency | US-067 (R7g, draft) |

## Relationship to ADR 0013

Supersedes the "upload frequency" phrase in the Tier-1 table for implementation purposes. All other ADR 0013 tiers and quota rules unchanged.
