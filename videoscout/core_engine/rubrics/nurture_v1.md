# Nurture keyword scoring rubric (v1)

Score **relative to other keywords in this batch**, not in absolute terms.

**Hard cap:** no single component may exceed **0.98**. Reserve headroom for stronger peers.

## Components (0.0–0.98 each)

### relevance
How well the phrase matches the YouTube **source_title** and channel niche.

Base from token overlap: `0.35 + 0.55 × (matched_tokens / keyword_tokens)`.

Adjustments (additive, then clip to 0.98):
- **Exact contiguous phrase** in normalized title: +0.05
- **Early title position** (phrase starts in first 40% of title tokens): +0.03
- **Generic tail only** (e.g. "viral trend", "new video", "funny clip"): cap at **0.55**

Cite overlap in reason: `"N/M keyword tokens in title"`.

**Relevance bands (pick one, do not exceed 0.98):**
- **0.98** — exact contiguous phrase representing the video's primary subject
- **0.95–0.97** — high overlap with minor normalization or contiguous with context gap
- **0.90–0.94** — strong overlap but partially incomplete phrase
- **0.55–0.89** — moderate to weak overlap (scale by matched token ratio)

### specificity
Word-count base bands:
- 2 words: 0.35–0.50 | 3 words: 0.55–0.70 | 4+ words: 0.70–0.85

Adjustments (additive, clip 0.98):
- **Named entity / proper noun** in phrase: +0.08
- **Distinctive numeric identifier** (percentages, counts, scores): +0.07
- **Generic filler token** (`viral`, `trend`, `video`, `new`, `funny`, `best`, `top`, `clip`, `challenge`): −0.08 per token (max −0.16)
- **Vague phrase** even with title overlap: cap at **0.50**

Cite modifiers in reason when present (e.g. "named entity", "numeric identifier").

### saturation
Inverse of TikTok competition. Use `saturation_tier` + `video_count_7d` only.

Tier base (before competition adjustment using avg_views internally):
- **fresh** (≤10 videos/7d): 0.75–0.95 — fewer videos → higher end
- **moderate** (11–30): 0.50–0.75
- **saturated** (>30): 0.15–0.40

Competition adjustment within tier (when `video_count_7d ≥ 3`):
- High `avg_views` (≥100K) with low count → subtract 0.02–0.06 (winners already established)
- Low `avg_views` (<1K) with fresh tier → add up to +0.03 (underserved niche)

**component_reasons cite tier + count only** — do not mention avg_views here (belongs in video_performance).

Example: `"TikTok tier=moderate with 11 videos published in the last 7 days."`

### trend
From YouTube trending title — **differentiate by hook strength**, not flat score.

**Primary hook (0.82–0.90)** — assign when contiguous phrase match AND any of:
- Keyword covers **≥50%** of title tokens (short-title rule: keyword IS the title hook)
- Phrase starts in **first 40%** of title tokens
- Title has **≤4 tokens** and keyword covers **≥40%** of them

Example: `"xhoni 100"` in `"DON XHONI - 100%"` → primary (2/3 title tokens).

**Secondary hook (0.68–0.78)** — contiguous phrase in middle third of a longer title, coverage <50%.

**Supporting phrase (0.55–0.65)** — partial overlap or contiguous tail phrase.

**Filler / single generic word (0.45–0.52)** — e.g. `"blind"`, `"2026"` alone.

**No YouTube trend source:** 0.50

Same score for every keyword in batch is wrong — vary by coverage and position.

### video_performance
Base from TikTok `avg_views` bands:
- <1K → 0.30–0.45 | 1K–10K → 0.45–0.60 | 10K–100K → 0.60–0.75 |
  100K–1M → 0.75–0.90 | 1M+ → 0.90–0.96

Engagement bonus (additive, clip 0.98):
- `(avg_likes + avg_comments) / avg_views × 25`, capped at **+0.10**

Cite avg_views and bonus in component_reasons.

## Confidence (0.0–1.0)

Data coverage score — not quality of keyword:
- YouTube source_title present: +0.20
- TikTok stats verified (not unverified): +0.25
- `video_count_7d ≥ 3`: +0.15
- `avg_views > 0`: +0.10
- Multiple discovery signals: +0.10

Typical path with title + TikTok + views: **0.75–0.85**.

## Batch rules

1. Spread matters: top keyword should score ≥0.12 higher than weakest viable keyword (final_score post-processing may enforce ≥0.15).
2. Do not assign identical component_scores to multiple keywords.
3. Compare candidates using `heuristic_components` and `tiktok_stats` — do not ignore them.
4. `component_reasons` must reference platform numbers when available (avg_views only in video_performance).
5. Do **not** compute final_score — post-processing applies weights.
6. **Tie-break:** if relevance differs by less than 0.03 within the batch, prefer separating candidates using trend, specificity, and saturation rather than assigning identical relevance scores.

## Risk flags (optional)

- `generic_phrase` — mostly filler tokens
- `saturated` — tier=saturated or video_count_7d > 30
- `weak_title_overlap` — <50% token overlap with source_title
- `low_views` — avg_views < 1K
- `duplicate_of_batch_peer` — Jaccard token similarity >0.80 or normalized Levenshtein >0.90 vs another batch keyword

When duplicate detected, lower specificity by 0.05 and note in risk_flags.
