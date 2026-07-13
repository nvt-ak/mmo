# US-073 — Discovery inbox qualification gates

## Status

implemented

## Lane

tiny

## Product Contract

Each discovery job still saves at most 10 keywords, but only after final ranking
and only if they pass configurable quality floors (score + beta component mins).

## Acceptance Criteria

- Post-ranking filter drops rows below `min_score_threshold` before save.
- Beta rows also require `min_specificity` and minimum relevance (0.30).
- Settings UI exposes min score threshold.
- Default min score for new installs: 0.55.
