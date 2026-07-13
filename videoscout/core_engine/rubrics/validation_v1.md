# Keyword evidence validation rubric (v1)

Second-pass **validation** — not a full rescore.

## Purpose

Given initial component scores and new **search-sample evidence**, determine whether the
keyword reliably represents one reproducible content pattern.

Search-sample stats are from a **ranking-biased API sample**, not the full keyword
population. Use `population_context` and `representation_quality` when interpreting
distributions.

## Locked components (do not change unless explicit contradiction)

- `trend`
- `relevance`
- `specificity`

## Adjustable via validation deltas only

- `confidence` (−0.25 to +0.05)
- `video_performance` (−0.20 to +0.05) — especially when `viral_outlier` is true
- `saturation` (−0.10 to +0.05) — only if gate vs deep TikTok sample materially diverges

Do **not** output new full component_scores. Output **adjustments** only.

## Pattern assessment

| Value | When |
| --- | --- |
| `single_pattern` | High pattern_purity; coherent titles; low fragmentation |
| `mixed` | Moderate purity or mixed representation_confidence |
| `fragmented` | Low purity; generic query; unrelated titles in sample |

## Validation status

| Status | When |
| --- | --- |
| `confirmed` | Sample supports initial assessment; no major outlier |
| `weakened` | Outlier, low representation quality, or fragmented pattern |
| `contradicted` | Sample clearly contradicts reproducibility (rare) |

## Risk flags (non-exhaustive)

- `single_viral_source` — top video dominates views (`viral_outlier`)
- `pattern_fragmented` — mixed/fragmented pattern_assessment
- `low_representation_quality` — representation_confidence is low
- `search_sample_bias` — remind operator sample is recency-ranked

## Output rules

- Cite median_views, top_contribution_pct, creator_diversity from **youtube** and **tiktok**
  search samples separately — never merge platforms.
- Explain confidence changes in `validation_rationale`.
- Do not compute `final_score`.
