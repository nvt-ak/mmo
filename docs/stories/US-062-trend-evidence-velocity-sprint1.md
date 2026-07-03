# US-062: TrendEvidence Schema + Velocity Percentile (Sprint 1)

## Status

in_progress

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

- [ ] `TrendEvidence` dataclass/TypedDict with `schema_version`, `metadata`, `provenance`, `raw`, `derived`
- [ ] `raw` / `derived` / `metadata` never mixed (unit tested)
- [ ] `LifecycleClassifier` stub returns stage from evidence — **not** persisted on suggestion
- [ ] Evidence serialized to DB on each suggestion (column TBD: extend `trend_signals` or `trend_evidence` JSONB)

### Velocity (Sprint 1 core signal)

- [ ] `get_trending_videos` returns `published_at`, `view_count`, `category_id`
- [ ] `derived.velocity.raw` = `log(views) / sqrt(hours_since_publish)` (hours ≥ 1)
- [ ] `derived.velocity.percentile_region_category` computed from in-job batch or cached baseline
- [ ] Scorers read percentile for trend component, not raw velocity

### Pipeline wiring (minimal — no Top-N yet)

- [ ] `EvidenceBuilder` module builds TrendEvidence from source video + candidate keyword
- [ ] `trend_discovery` worker uses EvidenceBuilder before nurture/beta scoring
- [ ] `platform_signals` built from TrendEvidence (backward compatible shape)
- [ ] `trend_source_region` from discovery run config (default `DE`, not hardcoded in service)

### Observability

- [ ] Discovery job logs evidence snapshot count + schema_version
- [ ] Replay helper: load evidence JSON from suggestion row for debug (script or API field)

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
