# US-077 — Score breakdown transparency (blend + ranking)

**Lane:** tiny  
**Epic:** E09 Dual-Track Discovery  
**Status:** implemented

## Problem

Inbox "Score breakdown" shows only LLM `component_scores`, but beta `final_score`
also includes heuristic blend and ranking adjustments. Additionally:

- `_finalize_beta_score` omitted `blend` from `platform_signals.agent`
- `enforce_batch_spread` (nurture ladder 0.45–0.92) ran on beta batches, inflating
  scores (e.g. 0.746 → 0.92 → 0.884)
- Over-optimistic heuristic relevance (title token match) inflated blend when LLM
  scored much lower

## Fixes

1. Pass `blend=blend_meta` into `build_platform_signals` for beta
2. Skip `enforce_batch_spread` on beta batch finalize
3. `reconcile_heuristic_components_for_blend` before heuristic blend weight
4. Persist `ranking_adjustments`; UI shows full composition

## Acceptance

1. `apply_final_ranking()` persists `ranking_adjustments` on `platform_signals.agent`.
2. Inbox insight panel shows blend weights + heuristic final + ranking deltas when present.
3. Tests cover ranking metadata persistence.

## Verify

```bash
python -m pytest videoscout/tests_api/test_discovery_ranker.py -v
cd web && npm run lint && npm run build
```
