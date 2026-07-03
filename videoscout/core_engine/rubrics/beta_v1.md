# Beta keyword scoring rubric (v1)

Score **relative to other keywords in this batch**, not in absolute terms.

**Hard cap:** no single component may exceed **0.98**. Reserve headroom for stronger peers.

**Core principle:** historical niche evidence should outweigh generic popularity. A keyword that previously failed within this niche should usually rank below a moderately trending keyword with strong niche alignment.

## Components (0.0–0.98 each)

### relevance
Measures how well the keyword matches the **channel niche** — not global virality.

**Primary signals (in priority order when kb_context exists):**
1. `kb_context` historical winners and niche patterns
2. Semantic similarity to channel niche topics
3. Keyword overlap with `source_title` (when available)

**Adjust downward when:**
- Similar keywords historically underperformed in `kb_context`
- Marked as false positive in `kb_context`
- Generic viral phrase without niche fit → cap at **0.50**

**Fallback when `kb_context` unavailable:**
- Use `source_title` overlap + niche similarity from `trend_signals`
- Do not assume high relevance from TikTok views alone

Strong historical performance should influence relevance, but should not override obvious semantic mismatch (e.g. kb winner "AI tools" does not justify high relevance for "AI girlfriend prank" on a non-prank channel).

Cite evidence in component_reasons: kb wins/failures, title overlap, or fallback used.

### specificity
Prefer **3–5 word** niche phrases that a creator can act on.

Word-count base bands:
- 2 words: 0.35–0.50 (vague generics penalized)
- 3 words: 0.55–0.70 | 4 words: 0.65–0.80 | 5+ words: 0.75–0.90

Adjust **upward** for:
- Named entities tied to niche
- Technical terminology
- Unique combinations unlikely to appear in generic content

Adjust **downward** for:
- Generic modifiers (`viral`, `trend`, `best`, `new`)
- Broad concepts without niche anchor
- Vague wording even if title overlap is high → cap at **0.50**

Cite modifiers in component_reasons when present.

### saturation
Inverse of TikTok competition. Use `saturation_tier` + `video_count_7d` only.

Tier ranges:
- **fresh** (≤10 videos/7d): 0.75–0.95
- **moderate** (11–30): 0.50–0.75
- **saturated** (>30): cap ≤ **0.30**

**Differentiate within tier using `video_count_7d`:**
- fresh, 1 video → ~0.95 | fresh, 5 videos → ~0.78 | fresh, 10 videos → ~0.75
- moderate, 11 videos → ~0.72 | moderate, 25 videos → ~0.55
- saturated → scale down as count rises above 30

**component_reasons cite tier + count only** — avg_views belongs in video_performance.

Example: `"TikTok tier=fresh with 3 videos published in the last 7 days."`

### trend
Measures whether the keyword captures the video's **primary attention hook** — not just category context.

**Higher scores (0.75–0.90):**
- Challenge, reveal, surprise, controversy, emotional event
- Phrase appears early in `source_title`
- Actionable hook a creator can replicate in niche format

**Mid scores (0.58–0.74):**
- Secondary hook from title — relevant but not the main draw
- Trending format with clear niche angle

**Lower scores (0.45–0.57):**
- Category labels without hook
- Names without context
- Supporting phrases / tail words

**If no YouTube trend source exists:**
- Assign a neutral score around **0.50–0.60** using available niche signals (`kb_context`, keyword semantics)
- Do not default to 0.50 when strong kb_context indicates a clear hook pattern

Do not assign identical trend scores across the batch.

### video_performance
Base from TikTok `avg_views` bands:
- <1K → 0.30–0.45 | 1K–10K → 0.45–0.60 | 10K–100K → 0.60–0.75 |
  100K–1M → 0.75–0.90 | 1M+ → 0.90–0.96

Engagement bonus (heuristic, additive, clip 0.98):
- Use engagement rate as a **supporting signal** relative to batch peers
- Typical bonus: **0.00–0.10** — higher engagement vs peers → larger bonus
- Never exceed **+0.10** (do not apply a fixed formula; judge qualitatively)

Cite avg_views and bonus in component_reasons.

## component_reasons

Each component_reason should explain:
- **Evidence used** (kb_context, title, tiktok_stats)
- **Why the score is not higher**
- **Why the score is not lower**

Cite platform numbers whenever available.

## Confidence (0.0–1.0)

Reflects scoring **reliability**, not keyword quality.

**Increase confidence when** (calibration guidance — not additive arithmetic):
- `kb_context` present with historical data → high reliability
- TikTok stats verified → strong platform signal
- `source_title` present → title context available
- `video_count_7d ≥ 3` → stable saturation read

**Decrease confidence when:**
- Missing supporting signals (no kb, no title, unverified TikTok)
- Conflicting evidence (high views but kb false positives)

Treat the above as guidance, not an exact formula. **Clip confidence to 1.00.**

Typical beta path with kb + TikTok + title: **0.75–0.90**.

## Calibration

Scores are relative to **this batch only**.

- Avoid clustering — spread component scores across the batch
- Avoid exact ties on any component
- Component scores should rarely equal **0.00** or **0.98**
- Compare against peer keywords before assigning final component values

## Batch rules

1. Use `kb_context` per keyword when present — past false positives must lower relevance.
2. Spread scores: top keyword ≥0.12 above weakest viable peer (post-processing may enforce ≥0.15).
3. Do not assign identical `component_scores` to multiple keywords.
4. Do **not** compute `final_score` — post-processing applies weights.
5. **Tie-break:** if relevance differs by less than 0.03, separate candidates using specificity, saturation, and trend — not identical relevance scores.
6. **Historical evidence rule:** niche-aligned keyword with moderate signals beats high-virality keyword with kb false-positive history.

## Risk flags (optional)

- `generic_phrase` — mostly filler / viral-generic wording
- `saturated` — tier=saturated or video_count_7d > 30
- `kb_false_positive` — kb_context marks similar keyword as underperformer
- `low_views` — avg_views < 1K
- `too_short` — 1–2 word keyword that lacks niche specificity (not merely word count; only flag when brevity materially hurts actionability)
- `duplicate_of_batch_peer` — near-duplicate of another batch keyword

When `kb_false_positive` detected, lower relevance by at least 0.10 and note in risk_flags.
