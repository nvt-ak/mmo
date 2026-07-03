/** Ship defaults — keep in sync with videoscout/core_engine/rubrics/*.md */
export const NURTURE_RUBRIC_DEFAULT = `# Nurture keyword scoring rubric (v1)

Score **relative to other keywords in this batch**, not in absolute terms.

## Components (0.0–1.0 each)

### relevance
- How well the phrase matches the YouTube **source_title** and channel niche.
- Cite overlap: "N/M keyword tokens in title".
- Generic tail words only → cap at 0.55.

### specificity
- 2 words: 0.35–0.50 | 3 words: 0.55–0.70 | 4+ words: 0.70–0.85.
- Penalize vague phrases ("viral trend", "new video") even if title overlap is high.

### saturation
- Inverse of TikTok competition. Use \`saturation_tier\` + \`video_count_7d\` from tiktok_stats.
- fresh (≤5 videos/7d): 0.75–0.95 | moderate: 0.50–0.75 | saturated: 0.15–0.40.
- **component_reasons must cite tier and count.**

### trend
- From YouTube trending title: 0.60–0.80 only if phrase is the **core hook**, not filler.
- Same score for every keyword in batch is wrong — differentiate by title position.

### video_performance
- Use avg_views bands: <1K → 0.30–0.45 | 1K–10K → 0.45–0.60 | 10K–100K → 0.60–0.75 |
  100K–1M → 0.75–0.90 | 1M+ → 0.90–0.98.
- Cite avg_views number in component_reasons.

## Batch rules

1. Spread matters: top keyword should score ≥0.12 higher than weakest viable keyword.
2. Do not assign identical component_scores to multiple keywords.
3. Compare candidates using \`heuristic_components\` and \`tiktok_stats\` — do not ignore them.
4. \`component_reasons\` must reference platform numbers when available.
5. Do **not** compute final_score — post-processing applies weights.

## Risk flags (optional)

- \`generic_phrase\`, \`saturated\`, \`weak_title_overlap\`, \`low_views\`, \`duplicate_of_batch_peer\`
`;

export const BETA_RUBRIC_DEFAULT = `# Beta keyword scoring rubric (v1)

Score **relative to other keywords in this batch**, not in absolute terms.

## Components (0.0–1.0 each)

### relevance
- Match channel niche topics and historical beta winners in \`kb_context\`.
- Generic viral phrases without niche fit → cap at 0.50.

### specificity
- Prefer **3–5 word** niche phrases.
- 3 words: 0.55–0.70 | 4 words: 0.65–0.80 | 5+ words: 0.75–0.90.
- Penalize vague 2-word generics.

### saturation
- Inverse of TikTok competition. Use \`saturation_tier\` + \`video_count_7d\`.
- fresh: 0.75–0.95 | moderate: 0.50–0.75 | saturated: cap ≤ 0.30.
- Cite tier and count in rationale.

### trend
- YouTube trending source adds context only if phrase is the actionable hook.
- Do not give identical trend scores across the batch.

### video_performance
- Use avg_views bands from tiktok_stats; cite numbers in rationale.

## Batch rules

1. Use \`kb_context\` per keyword when present — past false positives should lower relevance.
2. Spread scores: top keyword ≥0.12 above weakest viable peer.
3. Do not assign identical component_scores to multiple keywords.
4. Do **not** compute final_score — post-processing applies weights.

## Risk flags (optional)

- \`generic_phrase\`, \`saturated\`, \`kb_false_positive\`, \`low_views\`, \`too_short\`
`;
