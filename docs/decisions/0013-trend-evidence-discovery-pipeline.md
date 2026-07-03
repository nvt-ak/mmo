# 0013 TrendEvidence Discovery Pipeline

Date: 2026-07-03

## Status

Accepted

## Context

R7a TrendDiscovery (`videoscout/workers/trend_discovery.py`) optimizes **trend
detection**, not **predictive ranking**. Current flow:

```text
YouTube mostPopular → title n-gram extract → TikTok gate → LLM/heuristic score
```

Gaps:

- No view velocity, upload age, or channel authority on source video
- TikTok saturation only; no YouTube supply-side signal
- Scattered objects (`trend_signals`, `platform_signals`, `tiktok_gate`) — hard to
  extend, replay, or version
- Product goal is **precision** (approve rate, post rate), not recall

Design review (2026-07-03) approved shift from **keyword scoring** to **evidence
scoring**: enrich input data; keep rubric stable.

## Decision

Adopt a **3-stage discovery architecture** with **TrendEvidence** as the versioned
API contract for every stage (extractor, enrichment, scorer, logger, replay, A/B).

```text
CandidateGenerator → EvidenceBuilder → Ranker
```

| Stage | Responsibility |
| --- | --- |
| **CandidateGenerator** | Produce keyword candidates from sources (MostPopular, later Velocity) |
| **EvidenceBuilder** | Attach raw platform facts; compute derived scores; optional Top-N enrichment |
| **Ranker** | LifecycleClassifier (derived, not persisted) + LLM/heuristic + final order |

TrendEvidence is **not** an LLM DTO only — it is the durable contract between all
pipeline components.

### TrendEvidence schema (v1)

```json
{
  "schema_version": "1",
  "keyword": "example keyword phrase",
  "metadata": {
    "created_at": "2026-07-03T08:00:00Z",
    "pipeline_run_id": "uuid",
    "enrichment_tier": 0
  },
  "provenance": {
    "source": "youtube_most_popular",
    "confidence_type": "popularity",
    "region": "DE",
    "detected_at": "2026-07-03T08:00:00Z"
  },
  "raw": {
    "youtube": {
      "source_video_id": "...",
      "source_title": "...",
      "channel_id": "...",
      "published_at": "...",
      "view_count": 120000,
      "category_id": "20"
    },
    "youtube_search": null,
    "tiktok": null,
    "channel": null
  },
  "derived": {
    "velocity": {
      "raw": 2.41,
      "percentile_region_category": 0.82
    },
    "supply_pressure": null,
    "history_prior": null
  }
}
```

Rules:

1. **raw / derived / metadata** — never mix. Changing `log(views)/sqrt(hours)` does
   not require re-fetching API data.
2. **Lifecycle stage** (`early_accelerating`, `stable`, `late`, `noise`) — computed
   by `LifecycleClassifier` at rank time; **not persisted**. Only evidence persists.
3. **Velocity** — store `raw` + `percentile_region_category`. Scorers read
   **percentile**, not raw (music/sports/gaming/news bias otherwise).
4. **Supply pressure** (Sprint 2) — include **creator diversity** (unique creators /
   total videos), not just upload count.
5. **schema_version** — required from day one; bump on breaking field moves.

### Provenance normalization

All sources map to `provenance.source` + `provenance.confidence_type`:

| Source | `source` | `confidence_type` |
| --- | --- | --- |
| YouTube Most Popular | `youtube_most_popular` | `popularity` |
| YouTube velocity feed (Sprint 3) | `youtube_velocity` | `emergence` |
| Future: RSS, Reddit, Google Trends, TikTok Discover | `rss_*`, etc. | per source |

Scorer does not branch on fetch implementation — only on normalized provenance.

### Enrichment tiers (quota-aware)

| Tier | When | Data |
| --- | --- | --- |
| **0** | Every candidate | Raw YouTube source video stats + derived velocity percentile |
| **1** | Channel in DB | subs, upload frequency from `ChannelModel` → `raw.channel` |
| **2** | Top-N after initial rank (default N=10) | YouTube search round-trip + TikTok deep stats → `raw.youtube_search`, `raw.tiktok` |

Latency budget: 60s → 90–120s acceptable if precision improves.

`trend_source_region` — config (not hardcoded DE).

### Storage mapping

- Persist full TrendEvidence JSON on `suggestions` (extend `trend_signals` or new
  `trend_evidence` JSONB column — implementation choice in US-062).
- `platform_signals` remains agent-facing scoring metadata; built from TrendEvidence
  at rank time.
- Log + replay: discovery job stores evidence snapshots for A/B comparison.

### A/B evaluation

| Arm | Description |
| --- | --- |
| A (control) | Current pipeline |
| B (treatment) | TrendEvidence + velocity percentile + Top-N enrichment |

Metrics (priority order):

1. **Precision@10** — of top 10 surfaced, operator keeps how many (fast)
2. Approve rate
3. Post rate
4. Performance after 7 days (slow feedback)

Randomize per discovery **job**, not per keyword.

## Alternatives Considered

1. **More rubric rules** — rejected; evidence enrichment improves ranking without
   prompt churn (design review consensus).
2. **Persist lifecycle stage** — rejected; definitions will change; evidence is stable.
3. **Raw velocity in scorer** — rejected; percentile by region + category required.
4. **Enrich all candidates with YouTube search** — rejected; Top-N only for quota.

## Consequences

Positive:

- Add Google Trends / Reddit later by writing `raw.*` + provenance — no scorer rewrite
- Replay/debug from stored evidence
- Clear separation: generation vs enrichment vs ranking

Tradeoffs:

- Schema migration discipline required (`schema_version`)
- Percentile baselines need periodic refresh per region/category
- Sprint 1 does not fix candidate generation noise (Sprint 3 CandidateGenerator split)

## Follow-Up

| Sprint | Scope | Story |
| --- | --- | --- |
| 1 | TrendEvidence v1, velocity raw + percentile, logging/replay | US-062 |
| 2 | Top-10 enrichment, Tier-1 channel, supply pressure + creator diversity | US-063 (draft) |
| 3 | Dual-source velocity feed, LifecycleClassifier, history prior | US-064 |

Cheap pre-code experiment: backfill velocity on 50 trending videos; manual label
30 keywords; check velocity percentile vs early/stable/late/noise before wiring scorer.
