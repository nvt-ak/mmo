# US-081: Viral-outlier weakened / haircut policy (ranking)

## Status

planned (placeholder — do not implement until US-080 done + dedicated brainstorm)

## Lane

normal (behavior change to ranking — treat as normal with explicit review)

## Intent (open — decide at packet time)

US-080 only fixes saturation **display** in validation adjustments. Real ranking
leverage for concentrated samples is `validation_status` → haircut (×0.95), not
saturation ±0.05.

Choose **one** philosophy when writing this packet:

| Option | Change | Philosophy |
| --- | --- | --- |
| Z | Soften haircut when `viral_outlier` and `sample_size >= 5` (e.g. ×0.98 instead of ×0.95) | Outlier still suspicious, less so when sample large enough |
| Narrow status | Remove or gate `elif yt.get("viral_outlier"): status = "weakened"` so weakened only from `confidence <= -0.15` or fragmented pattern | Large reliable outlier sample is not enough alone to mark weakened |

Do **not** default to “recompute `final_score` from all component adjustments” (Y)
without a separate epic — activates VP −0.12 as a ranking delta for the first time
and nearly cancels a +0.05 saturation undo under current weights.

## Depends on

- US-080 (audit saturation undo)
- Design note in `docs/superpowers/specs/2026-07-15-sample-shape-saturation-undo-design.md` §5

## Non-goals until brainstorm

- Implementation details, exact constants, LLM validation merge precedence
