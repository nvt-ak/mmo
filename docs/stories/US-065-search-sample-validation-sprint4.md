# US-065 Search-Sample Evidence and Validation Pass (Sprint 4)

Status: done  
ADR: 0014  
Intake: normal (evidence pipeline extension; no new external services)

## Goal

Close the viral-riding gap: after initial keyword score, enrich top-N with search-sample
distributions + population context + representation quality, then run LLM **validation**
(delta-only) before inbox persist.

## Scope (Phase 1 per ADR 0014)

### In scope

- [x] TrendEvidence `schema_version: "2"` — Tier 2–4 fields
- [x] YouTube search: persist `pageInfo.totalResults` → Population Context
- [x] Per-platform `derived.search_sample.{youtube,tiktok}` distribution stats
- [x] Tier 4 Representation Quality heuristics
- [x] Query normalization: literal + de-generic + source-title entity phrase
- [x] Configurable `TOP_N_VALIDATION` (default 15; env)
- [x] Validation LLM pass + `platform_signals.agent.validation` block
- [x] Rubric markdown `validation_v1.md`
- [x] Tests: distribution math, outlier detection, validation merge, schema v2 serialize
- [x] Do **not** merge YT+TT distributions for LLM payload

### Out of scope

- Trend Cluster model, Opportunity Model, durability, dependency_risk
- Inbox UI redesign (follow-up story)
- Semantic / embedding query expansion
- Scheduled discovery

## Validation evidence (2026-07-03)

- `PYTHONPATH=. pytest videoscout/tests_api/test_search_sample_evidence.py videoscout/tests_api/test_validation_pass.py videoscout/tests_api/test_evidence_enrichment.py videoscout/tests_api/test_trend_evidence.py videoscout/tests_api/test_discovery_ranker.py` — 27 passed

## Files touched

- `videoscout/core_engine/search_sample.py` (new)
- `videoscout/core_engine/validation_pass.py` (new)
- `videoscout/core_engine/rubrics/validation_v1.md` (new)
- `videoscout/core_engine/trend_evidence.py`
- `videoscout/core_engine/evidence_enrichment.py`
- `videoscout/core_engine/platform_signals.py`
- `videoscout/core_engine/discovery_progress.py`
- `videoscout/services/youtube.py`
- `videoscout/workers/trend_discovery.py`
- `videoscout/tests_api/test_search_sample_evidence.py` (new)
- `videoscout/tests_api/test_validation_pass.py` (new)
