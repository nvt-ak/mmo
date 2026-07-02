# US-055: Beta LLM Keyword Scoring

## Status

implemented

## Lane

normal

## Product Contract

Replace heuristic `build_scored_candidate()` for **beta** keywords with LLM scoring
using KB context, settings weights, and deterministic rule guardrails.

**Epic:** E09  
**ADR:** `docs/decisions/0012-beta-llm-scoring-knowledge-graph.md`  
**Depends on:** US-054, US-053 (TikTok gate)  
**Blocks:** US-056 (learning weight UI)

## Acceptance Criteria

- New module `videoscout/core_engine/keyword_scorer.py`:
  - `score_beta_candidate(candidate, tiktok_gate, *, db, settings) -> dict | None`
  - Pre-rules: unverified block, min phrase length, saturation cap
  - LLM call: JSON schema output (5 components + rationale + risk_flags + confidence)
  - Post-rules: clamp components, server-side `final_score = Σ(c × weight)`
  - Transition blend: `0.6 LLM + 0.4 heuristic` when linked beta reports &lt; 20
- `workers/trend_discovery.py`: beta filter path calls `score_beta_candidate`; nurture keeps heuristic
- LLM failure → discovery job marks failed; beta suggestions not upserted (spec §11)
- Persist real `component_scores`, `rationale` (new JSONB field or reuse existing), `confidence` in suggestion metadata
- Tests: mock LLM; rule block paths; weighted sum recomputation; blend math

## Settings

- Beta weights use existing `ScoringWeights` columns (defaults per spec §10 emphasis)
- Optional: `beta_min_score` in settings JSON (default 0.40) — defer if not in schema yet

## Out of Scope

- Nurture LLM scoring
- Human-approved weight adjustment UI (US-056)
- Beta inbox UI for confidence/risk_flags (follow-up web story)

## Validation

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/test_keyword_scorer.py videoscout/tests_api/test_discovery.py -v
```
