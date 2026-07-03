# US-064: Dual-Source Discovery + Ranker (Sprint 3)

## Status

in_progress

## Lane

normal

## Product Contract

Sprint 3 per ADR 0013 — dual YouTube sources (mostPopular + velocity emergence),
history prior on TrendEvidence, LifecycleClassifier wired into final ranking.

**ADR:** `docs/decisions/0013-trend-evidence-discovery-pipeline.md`  
**Depends:** US-062, US-063

## Acceptance Criteria

- [x] Source A (`youtube_most_popular`) and B (`youtube_velocity`) fetched separately
- [x] Provenance `confidence_type`: `popularity` vs `emergence`
- [x] `derived.history_prior` from suggestion approve/reject/report history
- [x] `LifecycleClassifier` applied at rank time (not persisted on evidence)
- [x] Final ranking after enrichment uses lifecycle + history + supply pressure
- [x] `platform_signals` includes `lifecycle_stage` (derived metadata)

## Validation

```bash
python -m pytest videoscout/tests_api/test_candidate_generator.py \
  videoscout/tests_api/test_discovery_ranker.py \
  videoscout/tests_api/test_history_prior.py \
  videoscout/tests_api/test_discovery.py -v
```
