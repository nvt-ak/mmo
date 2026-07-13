# US-062: TrendEvidence Schema + Velocity Percentile (Sprint 1)

## Status

implemented

> Doc sync 2026-07-13: status/checkboxes were stale (marked in_progress with
> all boxes unchecked) despite downstream US-063/US-064/US-065 depending on
> this work shipping. Verified against code:
> `trend_evidence.py::compute_velocity_percentiles`,
> `velocity_percentile_from_evidence` (consumed by `candidate_generator.py`,
> `nurture_scorer.py`, `platform_signals.py`), and
> `videoscout/tests_api/test_trend_evidence.py`.

## Lane

normal

## Product Contract

Shift discovery from keyword scoring to **evidence scoring**. TrendEvidence v1 is
the versioned API contract for the entire discovery pipeline (ADR 0013).

**Epic:** E09 Dual-Track Discovery (evidence layer)  
**ADR:** `docs/decisions/0013-trend-evidence-discovery-pipeline.md`  
**Supersedes:** extends R7a; does not change nurture/beta classification rules

## Intake

| Field | Value |
| --- | --- |
| Type | spec-slice |
| Lane | normal |
| Risk | Bounded — extends discovery worker; adds YouTube API fields; no auth change |

## Acceptance Criteria

### TrendEvidence contract

- [x] `TrendEvidence` dataclass/TypedDict with `schema_version`, `metadata`, `provenance`, `raw`, `derived`
- [x] `raw` / `derived` / `metadata` never mixed (unit tested)
- [x] `LifecycleClassifier` stub returns stage from evidence — **not** persisted on suggestion
- [x] Evidence serialized to DB on each suggestion (column TBD: extend `trend_signals` or `trend_evidence` JSONB)

### Velocity (Sprint 1 core signal)

- [x] `get_trending_videos` returns `published_at`, `view_count`, `category_id`
- [x] `derived.velocity.raw` = `log(views) / sqrt(hours_since_publish)` (hours ≥ 1)
- [x] `derived.velocity.percentile_region_category` computed from in-job batch or cached baseline
- [x] Scorers read percentile for trend component, not raw velocity

### Pipeline wiring (minimal — no Top-N yet)

- [x] `EvidenceBuilder` module builds TrendEvidence from source video + candidate keyword
- [x] `trend_discovery` worker uses EvidenceBuilder before nurture/beta scoring
- [x] `platform_signals` built from TrendEvidence (backward compatible shape)
- [x] `trend_source_region` from discovery run config (default `DE`, not hardcoded in service)

### Observability

- [x] Discovery job logs evidence snapshot count + schema_version
- [x] Replay helper: load evidence JSON from suggestion row for debug (script or API field)

### Out of scope (Sprint 2–3)

- Top-10 YouTube/TikTok round-trip enrichment
- Tier-1 channel cache enrichment
- Dual-source velocity feed
- History prior
- CandidateGenerator refactor (ngram-last)
- A/B framework (log fields only in Sprint 1)

## Validation

```bash
python -m pytest videoscout/tests_api/test_discovery.py \
  videoscout/tests_api/test_trend_evidence.py -v
```

Manual:

```bash
curl -X POST http://localhost:8000/api/v1/discovery/run \
  -H 'Content-Type: application/json' \
  -d '{"keyword_type_filter":"both","region_code":"DE"}'
# Inspect suggestion row: trend_evidence.schema_version == "1"
# derived.velocity.percentile_region_category present
```

## Harness Delta

```bash
scripts/bin/harness-cli intake --type spec-slice \
  --summary "TrendEvidence v1 + velocity percentile" --lane normal --story US-062

scripts/bin/harness-cli story add --id US-062 \
  --title "TrendEvidence schema and velocity percentile" --lane normal \
  --verify "python -m pytest videoscout/tests_api/test_trend_evidence.py -v"
```
