# US-061 — Runtime scoring rubric + batch spread

**Lane:** normal  
**Epic:** E09 Dual-Track Discovery  
**Status:** implemented

## Goal

Fix nurture score clustering (~85% flat batch) with runtime rubric instructions,
LLM+heuristic blend (ADR 0012 pattern), and batch spread safety net.

## Context

US-060 added real component scores + platform_signals, but LLM batch still returns
similar absolute scores when keywords share the same trending title. Rubric layer
was missing; nurture path did not blend LLM with deterministic heuristics.

## Acceptance

1. Runtime rubric doc (`rubrics/nurture_v1.md`) loaded and injected into nurture LLM prompt
2. Nurture LLM `final_score` = 60% LLM components + 40% heuristic (same as beta pre-calibration)
3. `platform_signals.agent.blend` records llm/heuristic finals when LLM path used
4. Batch spread safety net: if chunk std dev `< 0.08`, rescale by heuristic rank to `[0.45, 0.92]`
5. Golden-set pytest: clustered LLM mock → spread ≥ 0.08 and top-bottom gap ≥ 0.15
6. Settings UI exposes nurture/beta rubrics with override + reset to ship default

## Out of scope

- Historical calibration from performance_reports
- UI changes beyond settings rubric editors

## Verify

```bash
python -m pytest videoscout/tests_api/test_nurture_scorer.py -v
```
