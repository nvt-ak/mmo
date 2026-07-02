# 0012 Beta LLM Scoring + Keyword Knowledge Graph

Date: 2026-07-02

## Status

Accepted

## Context

R7a TrendDiscovery scores **both** nurture and beta keywords with the same heuristic
(`build_scored_candidate` in `videoscout/core_engine/trend_discovery.py`):

- `final_score = 0.5 × word-count specificity + 0.5 × TikTok saturation`
- `component_scores` are stubs (`relevance=0.5`, `trend=0.7`, …)

Dual-track spec §6.3 requires **beta full gate**: real component scores + KB context.
§10 requires beta learning loop to adjust `specificity`, `saturation`, `relevance` weights
from performance reports.

Existing pieces (not wired for beta scoring):

| Piece | Location | Gap |
| --- | --- | --- |
| Flat KB text | `KnowledgeBase.get_context()` | No patterns, no graph, no beta filter |
| Patterns table | `keyword_patterns` | Desktop learn_agent; not queried at score time |
| Scoring weights | `SettingsModel.weight_*` | Used by legacy `score_keywords`, not TrendDiscovery |
| LLM extract | `SuggestionEngine.extract_keywords` | Scan path only; not scoring |

Nurture must stay fast and heuristic (spec §6.2, §10). Beta needs evidence-backed LLM scoring.

## Decision

Adopt a **3-layer beta scoring pipeline**: Rules → Knowledge Context → LLM → Rules.

```text
Candidate + tiktok_stats
    → pre_rules (hard block/cap)
    → KeywordContextBuilder.build(keyword, keyword_type=beta)
    → score_beta_candidate() — structured LLM prompt
    → post_rules (clamp, recompute weighted sum, min_score gate)
    → suggestion with real component_scores
```

### 1. Knowledge graph (v1 — PostgreSQL, not external graph DB)

Logical graph stored in existing tables + a new context builder:

| Node | Source |
| --- | --- |
| Keyword | candidate + similar keywords from reports |
| Report | `performance_reports` (beta-linked) |
| Pattern | `keyword_patterns` |
| NicheTopic | `settings.niche_topics` |
| SaturationTier | TikTok gate output |

| Edge | Meaning |
| --- | --- |
| Keyword → Report | past outcomes for same/similar phrase |
| Pattern → KeywordTrait | e.g. "3-word + saturated" → false_positive |
| Pattern → WeightHint | `suggested_adjustment` JSONB |
| NicheTopic → Keyword | relevance boost context |

**Module:** `videoscout/core_engine/keyword_context.py` — `KeywordContextBuilder`

Output: compact JSON (~500 token cap) injected into LLM prompt.

Extend `KnowledgeBase` to delegate to builder; keep backward-compatible `get_context()`.

### 2. Rules (deterministic)

**Pre-LLM (beta):**

- TikTok unverified → block (existing gate)
- Phrase &lt; 3 words → block or reclassify nurture
- Saturated tier → cap saturation component ≤ 0.3

**Post-LLM:**

- Clamp each component to [0, 1]
- Recompute `final_score = Σ(component × beta_weight)` — LLM final_score is advisory only
- `final_score < beta_min_score` (default 0.40) → do not surface
- LLM unreachable → job `failed`, inbox unchanged (spec §11)

Rules live in code (`keyword_scorer.py`), not in prompt.

### 3. LLM prompt (structured)

**Module:** `videoscout/core_engine/keyword_scorer.py` — `score_beta_candidate()`

Input bundle: candidate, tiktok_stats, `ScoringWeights` (beta profile from settings),
niche definition, KB context JSON, rules summary (§6.2 beta row).

Output schema (JSON mode, temperature 0.2–0.3):

```json
{
  "component_scores": {
    "relevance": 0.0,
    "specificity": 0.0,
    "saturation": 0.0,
    "trend": 0.0,
    "video_performance": 0.0
  },
  "rationale": "string",
  "risk_flags": ["saturated"],
  "confidence": 0.0
}
```

`final_score` computed server-side from components × weights.

**Transition (first 4 weeks, &lt;20 beta reports):**

Blend `0.6 × LLM + 0.4 × heuristic` until `linked_suggestions ≥ 20`; expose both in UI.

### 4. Nurture unchanged

Nurture path keeps `build_scored_candidate()` heuristic. No LLM call.

### 5. Learning loop (R7c — separate stories)

Beta performance reports → patterns → **human-approved** weight adjustments in settings.
No blind auto-apply of weight changes (current learn cycle is too aggressive).

Primary weight levers for beta: `specificity`, `saturation`, `relevance` (spec §10).

## Alternatives Considered

| # | Alternative | Kill reason |
| --- | --- | --- |
| 1 | LLM scores both nurture and beta | Nurture needs &lt;3 min/day; LLM cost/latency unacceptable |
| 2 | Heuristic beta forever | Violates §6.3 full gate; beta inbox shows fake component breakdown |
| 3 | Neo4j / vector DB day-1 | Over-engineering; &lt;1k reports initially; PostgreSQL + JSONB sufficient |
| 4 | LLM picks weights per keyword | Unstable, un-auditable; weights are operator/settings config |
| 5 | Reuse legacy `score_keywords` math + LLM extract only | No KB/pattern context; doesn't improve with feedback |
| 6 | Full GraphRAG crawl | No corpus to crawl; evidence is internal reports only |

## ICE Rationale

| Idea | Impact | Conf | Ease | ICE | Biggest risk |
| --- | --- | --- | --- | --- | --- |
| **3-layer beta pipeline (chosen)** | 8 | 6 | 5 | 240 | LLM uncalibrated until reports accumulate |
| Heuristic beta only | 4 | 9 | 9 | 324 | Spec mismatch; operator distrust |
| Neo4j + LLM | 7 | 5 | 3 | 105 | Ops burden, slow to ship |

## Pre-Mortem (12 months, beta scoring failed)

1. **LLM hallucination** — high scores for saturated broad terms; operator stops trusting beta inbox.
2. **Empty KB** — fresh install LLM scores same as heuristic; no perceived value.
3. **Prompt drift** — model change breaks JSON schema; discovery jobs fail silently.
4. **Weight chaos** — auto-adjusted weights oscillate; success rate drops.
5. **Cost blowup** — 50 keywords/day × LLM calls; operator disables LLM.

**Riskiest assumption:** LLM component scores correlate with beta post performance.

**Cheap experiment:** Score 30 historical keywords with known outcomes offline;
measure rank correlation vs heuristic before wiring production path.

## Consequences

Positive:

- Beta inbox shows real agent breakdown aligned with spec §7 step 2.
- KB + patterns improve scores as reports accumulate.
- Nurture stays cheap; clear track separation at scoring layer.
- Server-side weighted sum = auditable, settings-driven.

Tradeoffs:

- Beta discovery job latency increases (1 LLM call per candidate).
- Requires LLM configured; beta inbox empty on LLM failure (by design).
- v1 graph is logical (SQL joins), not visual graph UI.
- Transition blend adds complexity until calibration threshold met.

## Implementation Stories

| Story | Scope |
| --- | --- |
| US-054 | `KeywordContextBuilder` + extend `KnowledgeBase` |
| US-055 | `score_beta_candidate()` + wire TrendDiscovery beta path |
| US-056 (R7c) | Human-approved beta weight suggestions from learning cycle |

## Follow-Up

- Update `docs/ARCHITECTURE.md` when US-055 lands.
- Add offline calibration script before enabling 100% LLM weight in production.
- Beta inbox UI: show `confidence`, `risk_flags`, blend indicator during transition.
