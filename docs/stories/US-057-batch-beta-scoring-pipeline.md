# US-057: Batch Beta Scoring Pipeline

## Status

implemented

## Lane

normal

## Product Contract

Refactor TrendDiscovery to collect TikTok gates for all candidates first, then score
beta keywords in one (or chunked) LLM batch call instead of per-keyword LLM requests.

**Epic:** E09  
**Depends on:** US-055  
**Amends:** worker collect → score phases

## Acceptance Criteria

- Worker phase A: extract + dedupe + TikTok gate all candidates
- Worker phase B: nurture heuristic inline; beta via `score_beta_candidates_batch()`
- Single LLM call per batch (max 25 keywords); chunk if larger
- Batch output maps back to keywords; post-rules unchanged
- LLM batch failure skips chunk, does not fail entire job
- `score_beta_candidate()` preserved for tests (delegates to batch of 1)

## Validation

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/test_keyword_scorer.py videoscout/tests_api/test_discovery.py -v
```
