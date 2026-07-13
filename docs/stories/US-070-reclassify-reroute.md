# US-070 — Reclassify reroute (discovery recall fix)

## Status

implemented

## Lane

tiny

## Product Contract

When post-score `classify_keyword_type` disagrees with the scorer track, route the
candidate to the other track instead of dropping it silently.

## Acceptance Criteria

- Nurture-scored candidates reclassified as beta are scored on the beta track.
- Beta-scored candidates reclassified as nurture are scored on the nurture track.
- Filter `nurture` / `beta` still drops cross-track mismatches (no reroute).
- Reroute emits an info log with keyword, from/to track, and score.
- Regression tests cover nurture→beta and beta→nurture reroute.

## Validation

| Layer | Expected proof |
| --- | --- |
| unit | `videoscout/tests_api/test_scoring_reroute.py` |
| integration | reroute tests in keyword/nurture scorer modules |
