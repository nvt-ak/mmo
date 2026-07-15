# US-080: Sample-shape saturation undo (validation audit)

## Status

planned

## Lane

normal

**Risk flags:**
- Touches validation heuristic only; must not change haircut / `final_score` recompute.
- Easy to mis-claim as ranking fix — intent must stay audit/breakdown (US-077 spirit).
- Wrong `sample_size` source (gate `video_count_7d` vs enrichment) would reintroduce dual-fetch drift.

## Product Contract

After US-065 enrichment, top-N rows carry `derived.search_sample.{youtube,tiktok}` with
`viral_outlier` and `sample_size`. Validation already distrusts performance on outliers
(VP/confidence −0.12) but leaves saturation adjustment at 0, so breakdown can still read
like market saturation when the real issue is sample shape.

**This story:** populate existing `adjustments["saturation"] = +0.05` when outlier is
reliable (`sample_size >= 5` on the same platform block), for **component accuracy /
audit** only.

**Non-claim:** does not change ranking. `apply_validation_result` does not recompute
`final_score` from components; only status haircuts move `final_score`.

Relevant: `docs/product/workflows.md` (discovery → enrich → validate → inbox),
`docs/superpowers/specs/2026-07-15-sample-shape-saturation-undo-design.md`.

## Relevant Product Docs

- Design: `docs/superpowers/specs/2026-07-15-sample-shape-saturation-undo-design.md`
- US-065, US-077
- ADR 0014

## Intake

| Field | Value |
| --- | --- |
| Type | spec-slice |
| Lane | normal |
| Risk | Bounded — one function in `validation_pass.py` + unit tests |

## Acceptance Criteria

### Behavior

- [ ] When `tt.viral_outlier` and `tt.sample_size >= 5` **or** `yt.viral_outlier` and
      `yt.sample_size >= 5`, `_heuristic_validation` sets
      `adjustments["saturation"] = 0.05`.
- [ ] `sample_size` always read from `derived.search_sample` platform dict — never from
      `tiktok_stats.video_count_7d`.
- [ ] Outlier with `sample_size < 5` → saturation adjustment remains `0.0`.
- [ ] Existing outlier VP −0.12 and confidence −0.12 unchanged.
- [ ] Status / haircut rules unchanged (no soften, no remove `elif yt viral_outlier`).
- [ ] Rationale mentions saturation undo when applied.

### Explicit non-goals

- [ ] No change to `compute_saturation` / `calculate_saturation` / `tiktok_stats` shape.
- [ ] No recompute of `final_score` from adjusted components.
- [ ] No haircut magnitude or weakened-policy change (→ US-081).

### Tests

- [ ] Unit cases for n≥5 undo, n=4 no-undo, no-outlier; VP/confidence regression.

## Validation

```bash
PYTHONPATH=. pytest videoscout/tests_api/test_validation_pass.py -v
```

## Follow-ups (required elsewhere)

- **US-081** (placeholder): ranking leverage for `viral_outlier + n≥5` — open choice
  between softer haircut (Z) vs narrowing/removing
  `elif yt.get("viral_outlier"): status = "weakened"`. Decide in that packet.
- Single TikTok sample SSO before any initial-scorer suppress.
- Channel breakout velocity (M2); personality/moment candidates; median/p75
  `video_performance` — separate backlogs.

## Harness Delta

```bash
scripts/bin/harness-cli intake --type spec-slice \
  --summary "Sample-shape saturation undo (validation audit only)" --lane normal --story US-080

scripts/bin/harness-cli story add --id US-080 \
  --title "Sample-shape saturation undo (validation audit)" --lane normal \
  --verify "PYTHONPATH=. pytest videoscout/tests_api/test_validation_pass.py -v"
```
