# US-071 — Scoring reliability (beta heuristic + LLM validation + spread guard)

## Status

implemented

## Lane

normal

## Product Contract

Beta blend heuristic uses the same multi-signal component functions as nurture (not
constants). Post-LLM saturation/specificity are reconciled against server-side
bands. Batch spread only runs when relevance scores are also flat (lazy-cluster
proxy).

## Acceptance Criteria

- `_heuristic_components` derives all five components from title/TikTok signals.
- `heuristic_final_score` uses weighted sum with scoring weights.
- LLM saturation/specificity outside heuristic bands are pulled toward server truth.
- `enforce_batch_spread` skips when relevance std indicates genuine differentiation.
- Calibration blend ramps linearly before report threshold (no step cliff).

## Validation

| Layer | Expected proof |
| --- | --- |
| unit | `videoscout/tests_api/test_scoring_reliability.py` |
| integration | existing keyword/nurture scorer tests |
