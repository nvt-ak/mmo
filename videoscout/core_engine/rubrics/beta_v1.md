# Beta keyword scoring rubric (v1)

Score **relative to other keywords in this batch**, not in absolute terms.

## Components (0.0–1.0 each)

### relevance
- Match channel niche topics and historical beta winners in `kb_context`.
- Generic viral phrases without niche fit → cap at 0.50.

### specificity
- Prefer **3–5 word** niche phrases.
- 3 words: 0.55–0.70 | 4 words: 0.65–0.80 | 5+ words: 0.75–0.90.
- Penalize vague 2-word generics.

### saturation
- Inverse of TikTok competition. Use `saturation_tier` + `video_count_7d`.
- fresh: 0.75–0.95 | moderate: 0.50–0.75 | saturated: cap ≤ 0.30.
- Cite tier and count in rationale.

### trend
- YouTube trending source adds context only if phrase is the actionable hook.
- Do not give identical trend scores across the batch.

### video_performance
- Use avg_views bands from tiktok_stats; cite numbers in rationale.

## Batch rules

1. Use `kb_context` per keyword when present — past false positives should lower relevance.
2. Spread scores: top keyword ≥0.12 above weakest viable peer.
3. Do not assign identical component_scores to multiple keywords.
4. Do **not** compute final_score — post-processing applies weights.

## Risk flags (optional)

- `generic_phrase`, `saturated`, `kb_false_positive`, `low_views`, `too_short`
