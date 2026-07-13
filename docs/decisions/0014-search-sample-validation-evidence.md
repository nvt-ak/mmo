# 0014 Search-Sample Evidence, Validation, and Opportunity Ontology

Date: 2026-07-03

## Status

Accepted

## Context

ADR 0013 introduced TrendEvidence v1, dual YouTube sources, tier-0/1/2 enrichment,
and rank-time lifecycle. Implementation (US-062–064) still leaves a structural gap:

```text
Source video → LLM score → top-10 enrich → rank adjust (−0.04)
```

Problems confirmed in production code review (2026-07-03):

1. **Keyword-level evidence arrives too late** — YouTube/TikTok search only on top-N
   after initial LLM score; no validation pass.
2. **Average-only metrics** — `avg_views` hides single-viral-outlier bias
   (`tiktok.py`, `evidence_enrichment.py`).
3. **Merged cross-platform supply** — `compute_supply_pressure` blends YouTube +
   TikTok creator diversity into one score; platforms have different lifecycles.
4. **Search sample treated as population** — 20–25 API results are a
   **ranking-biased sample**, not keyword corpus; `pageInfo.totalResults` not persisted.
5. **Keyword as scored object** — title n-grams conflate multiple content patterns;
   operator approves **opportunities**, not strings.

Design review consensus: do **not** rewrite rubric or replace scorer. Extend evidence,
add a **validation pass**, and document long-term ontology (Pattern, Opportunity).

## Decision

### Ontology (stable across future ADRs)

| Concept | Role |
| --- | --- |
| **Keyword** | UI / inbox handle; dedup key (`SuggestionModel.keyword`) |
| **Pattern** | Latent content phenomenon the system infers (dance format, sound, event hook) |
| **Opportunity** | Long-term decision object: is this worth investing content effort? |

ADR sentence:

> **We estimate content opportunities. Keywords are the handle, patterns are the
> latent phenomenon, and evidence exists to quantify confidence—not certainty.**

Phase 1 ships keyword rows. Phase 2+ may introduce Trend Cluster. Phase 3 adds
Opportunity Model dimensions (Durability, Dependency Risk). Philosophy is fixed now;
scope is phased.

### Evidence is not independent

Tiers are **compositional**, not statistically independent. High Representation Quality
on a sound-tied pattern (e.g. one track) correlates with high Generalizability **and**
high **Dependency Risk** (single asset). Validation and future Opportunity Assessment
must surface correlated signals explicitly—not collapse them into one score.

**Deferred (Phase 3):** `dependency_risk`, `durability` as explanatory assessment
fields—not backend-compressed scores in Phase 1.

### Five evidence tiers (TrendEvidence schema v2)

Extend v1; bump `schema_version` to `"2"`. Rules from 0013 still apply: raw / derived /
metadata separation; lifecycle and validation results not persisted on evidence (agent
metadata on `platform_signals` instead).

```text
Tier 0 — Source Evidence
  raw.youtube + derived.velocity (existing)

Tier 1 — Gate Evidence
  TikTok gate stats on every candidate (existing; saturation tier)

Tier 2 — Search Sample (top-N only, per platform — never merged for LLM)
  raw.youtube_search, raw.tiktok (extend video lists)
  derived.search_sample.youtube { distribution stats }
  derived.search_sample.tiktok  { distribution stats }

Tier 3 — Population Context (metadata per query × platform)
  sample_size, estimated_result_count, query_used, search_order,
  time_window, ranking_bias, newest_upload, oldest_upload

Tier 4 — Representation Quality (metadata — not a single score)
  query_coherence, pattern_purity, fragmentation, alias_density,
  representation_confidence (high | mixed | low)
```

#### Search sample distribution (per platform)

Store **search sample** statistics, not "keyword population" statistics:

| Field | Meaning |
| --- | --- |
| `median_views`, `p75_views`, `p90_views`, `max_views` | View distribution in sample |
| `view_variance`, `top_video_ratio` | Outlier detection |
| `creator_count`, `creator_diversity` | Supply-side spread |
| `uploads_per_day` | Cadence in sample window |
| `viral_outlier` | Boolean; `top_contribution_pct` when true |

Label in prompts and UI: **"recency-ranked search sample (N=…)"**, not population.

#### Population Context

Persist YouTube `pageInfo.totalResults` (and TikTok analogous fields where available)
as `estimated_result_count`. Document as **population estimate**, biased by API and
query—not ground truth.

#### Representation Quality (Tier 4)

Answers: *Does this keyword represent one content pattern in the search sample?*

Heuristic v1 (backend); LLM refines in validation pass. Low RQ **caps confidence**,
does not reduce Trend (source velocity / freshness).

### Pipeline change (Phase 1)

```text
Extract → Gate → Initial Assessment (existing LLM/heuristic scorer)
     ↓
Top-N by initial score (config default 15–20; was 10)
     ↓
Keyword search (literal + normalized queries; dedupe video_id)
     ↓
Aggregate Tier 2–4 into TrendEvidence v2
     ↓
Validation pass (LLM — delta only, NOT full rescore)
     ↓
Final ranking + inbox persist (max keywords unchanged)
```

#### Validation pass contract

Second LLM call is **validation**, not re-grading.

**Locked after pass 1:** `trend`, `relevance`, `specificity` (unless explicit
contradiction flagged).

**Adjustable:** `generalizability` (inference), `video_performance` (outlier fix),
`confidence`, `saturation` (only if gate vs deep sample materially diverges).

Validation question:

> Does new search-sample evidence confirm the keyword represents one reproducible
> pattern, or weaken confidence (fragmentation, outlier, low representation quality)?

Output (on `platform_signals.agent.validation`, not persisted on evidence):

```json
{
  "validation_status": "confirmed | weakened | contradicted",
  "pattern_assessment": "single_pattern | mixed | fragmented",
  "adjustments": {
    "generalizability": 0.0,
    "video_performance": 0.0,
    "confidence": 0.0
  },
  "risk_flags": ["pattern_fragmented", "low_representation_quality", "single_viral_source"],
  "validation_rationale": "..."
}
```

Keep existing rank-time lifecycle / history / supply adjustments or reduce weight
after validation ships—implementation choice in US-065.

### Query normalization (Phase 1, minimal)

Per keyword, run multiple queries; union results with dedupe:

1. Literal keyword
2. Strip generic tokens (`viral`, `trending`, … — reuse nurture generic set)
3. Proper-noun / entity phrase from source title when present

Each query gets its own Population Context; aggregated distribution uses deduped
video set. `search_queries_used[]` on evidence metadata.

Semantic / embedding query expansion → Phase 2 (aliases, Trend Cluster).

### What we explicitly do not do in Phase 1

- Trend Cluster entity or DB model
- Opportunity Model (`durability`, `dependency_risk` assessment block)
- Full rescore of all five rubric components
- Crawl beyond API search limits
- Merge YouTube + TikTok distributions for LLM reasoning

## Alternatives Considered

1. **Backend Repeatability = 0–100** — rejected; compresses distribution; LLM reads
   stats better than opaque composite (design review 2026-07-03).
2. **Full LLM rescore on pass 2** — rejected; unstable; conflates Trend with
   Generalizability.
3. **Treat 20 search results as keyword population** — rejected; ranking bias;
   Population Context required.
4. **Score Trend Cluster in Phase 1** — rejected scope; keyword remains inbox entity;
   cluster is Phase 2.

## Consequences

Positive:

- Fixes viral-riding false positives without more source videos or rubric churn
- Evidence contract supports replay, A/B, and future Opportunity Model
- Operator-facing language can evolve toward Trend × Generalizability × Confidence
  without schema break

Tradeoffs:

- Second LLM pass on top-N adds latency (~30–60s budget still acceptable per 0013)
- Representation Quality heuristics v1 will be coarse; must label low confidence
- `schema_version: "2"` migration for stored `trend_evidence` JSONB

## Roadmap

| Phase | Scope | Story |
| --- | --- | --- |
| **1** | Search sample stats, Population Context, RQ heuristics, Validation pass, query normalization, top-N config | US-065 |
| **2** | Suggested aliases, multi-query polish, Trend Cluster entity | US-066 (draft) |
| **3** | Opportunity Assessment: Trend, Generalizability, Durability, Dependency Risk (explanatory) | US-067 (draft) |

## Relationship to ADR 0013

- Extends TrendEvidence; does not replace CandidateGenerator / EvidenceBuilder / Ranker
- Validation pass sits **after** EvidenceBuilder tier-2 enrichment, **before** final
  rank persist
- LifecycleClassifier unchanged; may consume `search_sample` outliers later

## Follow-Up

- Implement US-065 before changing inbox UI copy
- Backfill experiment: 50 keywords with search-sample stats; manual label
  viral-riding vs reproducible; measure precision@10 before enabling validation in prod
- Inbox UI (Phase 1.5): show validation_status, pattern_assessment, sample bias label
