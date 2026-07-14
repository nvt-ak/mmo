# US-078 Google Trends YouTube Discovery (R7d)

Status: done  
ADR: 0013, 0014  
Intake: normal (new free discovery source; replaces YouTube emergence search)

## Goal

Add Google Trends `gprop=youtube` as a free candidate source (pytrends, no API key).
Default geo **Worldwide**. Optionally replace YouTube emergence `search.list` (~300 quota/job).

## Scope

- [x] `GoogleTrendsService` — rising queries via pytrends, cache, pacing
- [x] `TrendEvidence.raw.google_trends` + provenance `google_trends` / `search_interest`
- [x] Discovery worker: trends keyword feed + rank boost
- [x] `GOOGLE_TRENDS_REPLACE_EMERGENCE=true` skips YouTube emergence search
- [x] Env: `GOOGLE_TRENDS_GEO` default empty (Worldwide), `GOOGLE_TRENDS_GPROP=youtube`
- [x] Tests with mocked pytrends

## Out of scope

- Official Google Trends API (alpha)
- Per-keyword interest lookup on every video-extracted keyword (rate limit)
- UI insight panel for Trends block (follow-up)

## Validation

- `PYTHONPATH=. pytest videoscout/tests_api/test_google_trends.py videoscout/tests_api/test_candidate_generator.py videoscout/tests_api/test_discovery_ranker.py` — 13 passed (2026-07-14)
