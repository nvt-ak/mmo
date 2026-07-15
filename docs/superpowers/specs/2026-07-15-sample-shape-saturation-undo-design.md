# VideoScout — Sample-Shape Saturation Undo (Validation Audit)

**Date:** 2026-07-15  
**Status:** Approved (brainstorm 2026-07-15)  
**Lane:** normal (validation heuristic only; no auth/stack change)  
**Story:** US-080  
**Related:** US-065 (validation pass), US-077 (score breakdown transparency), ADR 0014  
**Approach:** **X** — audit/breakdown accuracy only (no ranking claim)

---

## 1. Problem

Hit-driven TikTok/YouTube search samples (one outlier video dominates views) inflate
`avg_views`. Operators and UI breakdowns can then misread saturation as “crowded
high-performance market” when the signal is sample shape, not true competition.

`compute_distribution_stats()` already flags `viral_outlier` on enriched top-N
evidence (`derived.search_sample.{youtube,tiktok}`). `_heuristic_validation()`
already reacts with `video_performance` / `confidence` −0.12 and often
`weakened` (×0.95 haircut), but leaves `adjustments["saturation"]` at **0.0**
even though the schema clamp slot exists (`[-0.10, +0.05]`).

Separately: `apply_validation_result()` updates `component_scores` from
adjustments but **does not recompute `final_score`** from those components.
`final_score` only changes via status haircuts (×0.85 / ×0.95). Therefore any
saturation delta in this layer is **display/audit**, not ranking — by current
pipeline design.

## 2. Goal

When search-sample evidence shows a reliable viral outlier, populate the existing
saturation adjustment so LLM/heuristic **component breakdown** reflects
“do not read this as market saturation,” aligned with US-077 transparency.

**Explicit non-claim:** this packet does **not** change ranking, inbox thresholds,
or haircut policy.

## 3. Decisions (locked)

| Topic | Decision |
| --- | --- |
| Packet approach | **X** — audit/breakdown only |
| Placement | `_heuristic_validation()` in `validation_pass.py` |
| Source of truth | `derived.search_sample.{tiktok,youtube}` only — same object as `viral_outlier` |
| N threshold | `sample_size >= 5` on the platform block that triggered the outlier |
| Undo magnitude | `adjustments["saturation"] = +0.05` (schema high clamp) |
| VP / confidence | Keep −0.12 each when outlier fires (unchanged) |
| Status / haircut | Unchanged (`weakened` / ×0.95 rules as today) |
| Initial scoring | Do **not** change `compute_saturation`, `calculate_saturation`, or `tiktok_stats` |
| Dual flags | Do **not** compute a second `viral_outlier` at gate fetch time |
| Recompute final | Do **not** recompute `final_score` from adjusted components (**reject Y**) |
| Soft haircut | Do **not** change haircut in this packet (**reject Z** for US-080) |

### 3.1 Why not Y (recompute final from components)

Recompute would make **all** validation component deltas ranking-active for the
first time, including VP −0.12. Magnitude check for this story’s intended undo:

- sat +0.05 × 0.25 ≈ +0.0125
- VP −0.12 × 0.10 ≈ −0.012

Net ≈ **+0.0005** — nearly cancels the undo while expanding behavior risk.
Rejected for US-080.

### 3.2 Why not initial-scorer suppress (earlier Approach A)

Two independent TikTok fetches (gate vs enrichment) can yield two divergent
`viral_outlier` values. Prefer one source (enrichment sample) even though
coverage is top-N only. Initial sat penalty’s max blend impact is ~0.6pp —
smaller than haircut leverage; deferred until single-sample SSO follow-up.

### 3.3 Dual-concern coexistence (documented)

| Signal | Meaning |
| --- | --- |
| VP / confidence −0.12 (+ weakened when rules say so) | Distrust performance read from concentrated sample |
| saturation +0.05 (this story) | Do not display saturation as “hot crowded market” from the same shape |

Intentional, not contradictory — different operator questions.

## 4. Behavior

In `_heuristic_validation()`, after existing outlier VP/confidence adjustments:

```text
if (tt.viral_outlier and tt.sample_size >= 5)
   or (yt.viral_outlier and yt.sample_size >= 5):
    adjustments["saturation"] = +0.05
```

Rules:

- Use `tt.get("sample_size")` / `yt.get("sample_size")` — **never**
  `tiktok_stats.video_count_7d` (different fetch).
- If only one platform is outlier with n≥5, still apply +0.05 once (not stacked).
- If outlier but n&lt;5: leave saturation at 0.0 (flag may still set VP/confidence).
- Extend `validation_rationale` with a short clause when undo applies
  (e.g. sample-shape saturation undo, n=…).

`apply_validation_result()` unchanged: still adds adj into `component_scores`
and still only mutates `final_score` via status haircuts.

## 5. Out of scope / follow-ups

| ID (placeholder) | Topic |
| --- | --- |
| US-081 (planned) | **Ranking leverage for reliable outliers** — open choice between (Z) softer haircut when `viral_outlier + n≥5`, vs remove / narrow `elif yt.get("viral_outlier"): status = "weakened"` so weakened only from confidence/fragmented gates. Decide at that packet. |
| Later | Single TikTok sample source of truth (gate ↔ enrichment) before any initial-scorer suppress. |
| Later | `compute_video_performance` median/p75 (semantic change to avg). |
| Later | Personality/moment candidate type; channel breakout velocity (M2). |
| Later | Audit whether `engine.py` scoring path is still production-live vs nurture/keyword scorers (code-doc drift). |

## 6. Testing

- Unit `_heuristic_validation`:
  - outlier + n≥5 → `adjustments["saturation"] == 0.05`; VP/confidence still −0.12
  - outlier + n=4 → saturation `0.0`
  - no outlier → saturation `0.0`
- Regression: existing weakened / YT-outlier status tests still pass
- Optional: rationale string contains undo mention when applied

Verify command (expected):

```bash
PYTHONPATH=. pytest videoscout/tests_api/test_validation_pass.py -v
```

## 7. Success criteria

- Top-N validated rows with reliable sample-shape outliers show saturation
  component reflecting +0.05 undo in stored `component_scores` /
  `platform_signals.agent.validation.adjustments`.
- `final_score` and haircut behavior unchanged vs pre-US-080 for identical fixtures
  (apart from component field values).
- Story and UI/copy never claim ranking fix for this packet.
