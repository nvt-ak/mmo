# VideoScout — Dual-Track Keyword Discovery (Nurture + Beta)

**Date:** 2026-07-02  
**Status:** Approved (2026-07-02)  
**Scope:** Keyword discovery model, profile lifecycle, media pools, learning loop split  
**Amends:** `docs/superpowers/specs/2026-07-02-videoscout-workflow-design.md` (M1 discovery + distribution)  
**Related ADR:** `docs/decisions/0011-dual-track-nurture-beta.md`

---

## 1. Problem

The current implementation has a **channel-first scan** (`videoscout/api/scan.py`): keyword suggestions require pre-seeded YouTube channels. On a fresh install this yields **0 keywords** even when the scan job completes successfully.

This contradicts both:

1. The **keyword-led product model** (ADR 0009) — channels appear *after* keyword approve via cascade, not before.
2. The **operator's actual two-phase TikTok workflow** — nurture accounts (trend/idol clone) vs beta-eligible accounts (rigorous keyword selection for Creator Rewards).

Additionally, TikTok is currently used inside `SuggestionEngine` for scoring only, not as a discovery source — but the M1 spec diagram incorrectly implies TikTok search as a scan input. This spec corrects the discovery vs evaluation boundary.

---

## 2. Business Context

| Phase | Goal | Keyword style | TikTok role |
| --- | --- | --- | --- |
| **Nurture** | Grow channel — clone hot trend/idol content quickly | Broad, trend-driven, 2–3 word phrases | **Gate (light)** — basic volume/saturation check |
| **Beta** | Creator Rewards DE — selective, ROI-focused posting | Long-tail, niche-specific, 3–5 word phrases | **Gate (full)** — insight + agent score + KB + feedback rules |

**Discovery sources (both types):** YouTube trends, social media trending signals, niche websites — **not TikTok**. TikTok is exclusively the evaluation/gate layer for beta (and light gate for nurture).

**Distribution model:** Approve keyword → cascade → download → quality gates → **typed media pool** → bulk assign/post per TikTok profile. Approve does **not** bind a keyword to a profile immediately.

---

## 3. North Star (updated)

> Operator reviews **two daily keyword inboxes** (nurture + beta) sourced from external trends → approves → system builds a **typed media pool** → operator bulk-posts from the correct pool to **nurture or beta TikTok profiles**.

**Primary value units:**

- **Nurture keyword** → Nurture media pool → Nurture profiles
- **Beta keyword** → Beta media pool → Beta profiles

Profile promotion (nurture → beta) is manual; pool content does not auto-migrate.

---

## 4. Decisions (locked in brainstorming 2026-07-02)

| # | Topic | Decision |
| --- | --- | --- |
| 1 | Architecture approach | **Dual pipeline, shared core** — single suggestion model with `keyword_type`; separate gate configs; shared cascade/download infra |
| 2 | Profile registry | `tiktok_profiles` table; `stage: nurture \| beta`; manual `beta_eligible` tick promotes nurture → beta list |
| 3 | Daily split | Two keyword types in separate inboxes — not a global mode toggle |
| 4 | Discovery input | YouTube/social/web trends — **not TikTok** |
| 5 | Nurture TikTok gate | **Light** — volume/saturation only; unverified badge if TikTok unreachable |
| 6 | Beta TikTok gate | **Full** — agent score + KB + historical rules; block if unverified |
| 7 | Approve outcome | Populate typed media pool (not profile assignment) |
| 8 | Nurture posting | Same bulk-post pattern as beta — `/profiles/nurture` from Nurture pool |
| 9 | Beta posting | `/profiles/beta` bulk post from Beta pool only |
| 10 | Channel scan | **Deprecated as primary path** — channels come from post-approve cascade only |
| 11 | Upload automation | v1: assign + export/handoff queue; v2: in-app TikTok upload API |

---

## 5. Mental Model

VideoScout = **keyword → media factory → profile distribution hub**.

```text
TrendDiscovery (YouTube / social / web)
    │
    ├─ classify: nurture | beta
    ├─ TikTok gate: light (nurture) | full (beta)
    └─ dual inbox (pending)
            │
            │ approve [HARD GATE]
            ▼
    Keyword cascade → YouTube channels → download
            │
            ▼
    Batch review (Keep | Skip) → optional merge
            │
            ▼
    Media pool (pool_type: nurture | beta, pool_status: ready)
            │
            ├─ Nurture profiles → bulk post from Nurture pool
            └─ Beta profiles → bulk post from Beta pool
            │
            ▼ (async, beta-primary)
    Performance report → KB → agent rules → smarter beta scoring
```

**Profile lifecycle:**

```text
tiktok_profiles.stage = nurture
    │
    │ operator ticks "ready for beta"
    ▼
tiktok_profiles.stage = beta  (moves to beta profiles list)
```

Promoting a profile does **not** migrate existing pool assignments. Beta accounts only consume Beta pool content.

---

## 6. Discovery Architecture

### 6.1 TrendDiscoveryJob

Replaces channel-first `POST /scan/run` as the primary keyword generation path.

**Inputs (configurable in Settings):**

- YouTube Trending / niche topic feeds
- Social signals (X, Reddit, niche sites — phased)
- Operator seed topics (niche list in Settings)

**Pipeline:**

```text
TrendDiscoveryJob
    → KeywordCandidateExtractor (LLM + heuristics)
    → classify keyword_type (nurture | beta)
    → TikTokEvaluator (gate only)
    → upsert suggestions (pending, tagged keyword_type)
```

### 6.2 Classification heuristics (v1, tunable)

| Signal | Nurture | Beta |
| --- | --- | --- |
| Phrase length | 2–3 words, broad appeal | 3–5 words, specific |
| Trend source | YouTube trending, viral social | Niche topic + low competition |
| TikTok saturation | moderate–saturated acceptable | prefer fresh–moderate |
| Min agent score | ≥ 0.25 | ≥ 0.40 (+ min specificity/saturation) |

### 6.3 TikTok gate profiles

| Type | Checks | On TikTok failure |
| --- | --- | --- |
| Nurture (light) | `video_count_7d`, saturation tier | Surface with `tiktok_unverified` badge; operator decides |
| Beta (full) | Full stats + component scores + KB context | Do not surface in inbox until verified |

---

## 7. Daily Operator Workflow

| Step | Action | Time target |
| --- | --- | --- |
| 1 | Review **Nurture inbox** — quick approve/reject; trend source + light TikTok stats | ~3 min |
| 2 | Review **Beta inbox** — full agent breakdown, TikTok insight, KB context | ~5 min |
| 3 | Check **media pools** when downloads complete; batch Keep/Skip; optional merge | ~5 min |
| 4 | **Nurture profiles** — bulk assign/post from Nurture pool | as needed |
| 5 | **Beta profiles** — bulk assign/post from Beta pool | as needed |
| 6 | (Async) Report beta performance → learning cycle | non-blocking |

**Quality gate before pool entry:**

```text
download → review_status: pending
batch Keep → review_status: in_pool, pool_status: ready
bulk assign → pool_status: assigned
post confirm → pool_status: posted
```

Nurture: merge optional (single-clip clone acceptable). Beta: merge same-keyword as existing rules.

---

## 8. UI Routes (v1)

| Route | Purpose |
| --- | --- |
| `/today/nurture` | Nurture keyword inbox |
| `/today/beta` | Beta keyword inbox |
| `/pool/nurture` | Nurture media pool (ready assets) |
| `/pool/beta` | Beta media pool (ready assets) |
| `/profiles/nurture` | Nurture TikTok accounts + bulk post + promote action |
| `/profiles/beta` | Beta TikTok accounts + bulk post |
| `/settings` | Trend sources, niche topics, gate thresholds per type |

Existing routes retained with filters:

- `/batch` — filter by `pool_type`
- `/merge` — beta default; nurture optional
- `/feedback` — beta-primary
- `/sources` — read-only cascade output; not primary onboarding path

---

## 9. Data Model

### 9.1 Extend `suggestions`

| Column | Type | Notes |
| --- | --- | --- |
| `keyword_type` | `nurture \| beta` | NOT NULL, indexed |
| `discovery_source` | string | `youtube_trend`, `social`, `niche_web`, `manual` |
| `trend_signals` | JSONB | velocity, source URL, detected_at |
| `gate_profile` | string | `light` \| `full` |

Dedupe remains on `keyword` (unique). Same keyword cannot be both types simultaneously in v1; reclassify is manual operator action.

### 9.2 New `tiktok_profiles`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | PK |
| `label` | string | Display name |
| `handle` | string | TikTok handle |
| `stage` | `nurture \| beta` | Current list membership |
| `beta_eligible` | bool | Operator tick "ready for beta" |
| `promoted_at` | datetime | When moved nurture → beta |
| `notes` | text | Optional |

### 9.3 Extend `video_assets` and `final_videos`

| Column | Type | Notes |
| --- | --- | --- |
| `pool_type` | `nurture \| beta` | Inherited from `suggestion.keyword_type` |
| `pool_status` | enum | `pending_review`, `ready`, `assigned`, `posted` |

### 9.4 New `profile_media_assignments`

Tracks bulk assign/post from pool to profile.

| Column | Type | Notes |
| --- | --- | --- |
| `profile_id` | FK | `tiktok_profiles.id` |
| `final_video_id` | FK nullable | Post-merge asset |
| `video_asset_id` | FK nullable | Nurture may skip merge |
| `pool_type` | enum | Must match profile stage |
| `post_status` | enum | `queued`, `posted`, `failed` |
| `tiktok_post_url` | string nullable | After post confirm |

Constraint: nurture profile cannot assign beta pool content and vice versa.

### 9.5 Extend `discovery_jobs` (or evolve `scan_jobs`)

| Column | Type | Notes |
| --- | --- | --- |
| `job_type` | enum | `trend_discovery`, `channel_rescan` |
| `keyword_type_filter` | enum | `nurture`, `beta`, `both` |
| `sources_scanned` | int | Progress counter |
| `keywords_generated` | int | New suggestions count |

### 9.6 Extend `settings`

```json
{
  "nurture_gates": { "min_score": 0.25, "tiktok_check": "light" },
  "beta_gates": { "min_score": 0.40, "min_specificity": 0.4, "min_saturation": 0.3, "tiktok_check": "full" },
  "trend_sources": [{ "type": "youtube_trend", "enabled": true }]
}
```

---

## 10. Learning Loop Split

| Aspect | Nurture | Beta |
| --- | --- | --- |
| Primary signal | Views spike, engagement velocity | `views_vs_baseline`, ROI |
| Feedback required | Optional, lightweight | Required for agent improvement |
| Pattern extraction | Trend timing, broad-term false positives | Long-tail accuracy, saturation mistakes |
| Weight adjustments | `trend`, `video_performance` | `specificity`, `saturation`, `relevance` |
| KB ingestion | Aggregate only, low priority | Full — feeds `KnowledgeBase.get_context()` |
| Experiments track | `suggestion_source=nurture` | Existing experiment flow |

**Beta self-improvement loop:**

```text
Beta approve → post → performance report
    → performance_reports + learning_events
    → POST /learning/cycle
    → keyword_patterns + weight suggestions (human-approved)
    → next beta TrendDiscovery candidates scored smarter
```

Shared tables (`learning_events`, `keyword_patterns`, `performance_reports`) gain `keyword_type` filter support.

---

## 11. Error Handling

| Failure | Behavior |
| --- | --- |
| Trend source unavailable | Partial job completion; log failed source; continue others |
| LLM unreachable | Job `failed`; inbox unchanged; manual retry |
| TikTok gate timeout (nurture) | Surface with `tiktok_unverified` badge |
| TikTok gate timeout (beta) | Block from inbox until verified |
| Cascade finds 0 channels | Suggestion stays `approved`; job `failed` + operator notify |
| Download failure | Per-video error; successful downloads continue |
| Duplicate keyword cross-type | First discovery wins; manual reclassify in v1 |
| Profile promoted nurture→beta | Cancel nurture pool assignments in `assigned` (not `posted`) state |

All async jobs expose status + history endpoints (same pattern as existing `scan_jobs`).

---

## 12. Migration from Current Code

| Existing | Change |
| --- | --- |
| `videoscout/api/scan.py` channel-first | Primary path → `discovery.py` trend-first; channel rescan post-cascade only |
| `/today` single inbox | Split → `/today/nurture` + `/today/beta` |
| `SuggestionEngine.extract_keywords` from channel videos | TrendDiscovery uses trend sources; channel extraction remains in cascade context |
| `/sources` "add channel to scan" | Secondary/manual; primary path is approve → cascade |
| Cascade, batch, merge, feedback | Retained; filtered/tagged by `keyword_type` |

---

## 13. Rollout Phases

### R7a — Foundation

- `keyword_type` on suggestions
- TrendDiscovery worker (YouTube trending v1)
- Dual inbox UI
- Light vs full TikTok gate
- Deprecate channel-first scan as primary

### R7b — Profiles + Pools

- `tiktok_profiles` CRUD + nurture→beta promote
- `pool_type` / `pool_status` on assets
- `/pool/nurture`, `/pool/beta`, `/profiles/nurture`, `/profiles/beta`

### R7c — Distribution + Learning Split

- Bulk assign pool → profile
- Export/handoff queue (v1: file path list)
- Learning loop filter by `keyword_type`

### R7d — Trend Sources Expansion

- Social/web sources in Settings
- Classification tuning from pattern data

Each phase: feature intake → story packet → harness matrix → tests. No big-bang release.

---

## 14. Success Metrics

| Metric | Target |
| --- | --- |
| Bootstrap | Fresh install → ≥5 nurture + ≥3 beta keywords after first discovery (no manual channel) |
| Nurture inbox review | < 3 min/day |
| Beta inbox review | < 5 min/day |
| Approve → pool ready | < 30 min async (either type) |
| Beta agent accuracy | Improves over 4 weeks with performance reports |
| Pool separation | 0 cross-type assignments (nurture content → beta profile) |
| Profile promote | Manual only; no auto-migrate pool content |

---

## 15. Testing Strategy

- **Unit:** nurture vs beta classification; gate thresholds; `pool_type` inheritance from suggestion
- **API:** discovery job lifecycle; dual inbox filters; profile promote; bulk assign constraints
- **Integration:** approve nurture keyword → cascade → nurture pool → assign nurture profile (no beta leak)
- **Regression:** existing beta cascade, batch review, merge, feedback flows unchanged

---

## 16. Out of Scope (v1)

- TikTok upload API automation (assign + handoff only)
- Multi-user auth
- Auto-promote nurture profile to beta without operator tick
- Cloud storage for media pools

---

## 17. Related Docs to Update at Implementation

| Doc | Action |
| --- | --- |
| `docs/product/workflows.md` | Done — v0.3 dual-track daily flow |
| `docs/superpowers/specs/2026-07-02-videoscout-workflow-design.md` | Done — §15 M1 amendment |
| `docs/decisions/0011-dual-track-nurture-beta.md` | Done — ICE, pre-mortem, rejected alts |
| `docs/ARCHITECTURE.md` | Done — M1 discovery + M7 profile distribution |

---

## Appendix A — Rejected Alternatives (brainstorm retroactive, 2026-07-02)

Divergent-phase artifacts recorded after brainstorm review. Full rationale + ICE in ADR 0011.

| # | Alternative | Lens | Description | Kill reason |
| --- | --- | --- | --- | --- |
| 1 | Keep channel-first scan | Reverse | Status quo — seed channels, extract keywords from channel videos | Fresh install → 0 keywords; contradicts ADR 0009 |
| 2 | Single inbox + `keyword_type` badge/filter | SCAMPER/Eliminate | One `/today` with nurture/beta tabs or filters | Fast nurture review + deep beta review conflict on same surface; ICE UX risk |
| 3 | Global mode toggle | Persona (CFO) | Settings switch: "nurture day" vs "beta day" — one pipeline active | Operator runs both tracks daily; toggle hides half the factory |
| 4 | Discovery fix only (no profiles/pools) | Extremes/$0 | TrendDiscovery + dual gate; defer `tiktok_profiles` and typed pools to later | Highest ICE (~567) but doesn't solve nurture/beta distribution split |
| 5 | Operator picks type at approve | Reverse | All candidates land in one inbox; operator selects nurture or beta on approve | Kills classifier risk v1; extra click per approve; can't pre-sort inboxes |
| 6 | Profile-bound keywords | Anti-problem | Approve keyword → immediately bind to specific TikTok profile | Breaks media pool + bulk-post model; pool_type separation harder |
| 7 | TikTok as discovery source | First-principles | Use TikTok search/trending to generate keyword candidates | Circular with TikTok gate layer; M1 diagram error, not product intent |
| 8 | Nurture-only v1 | Extremes/constraint | Ship trend discovery + nurture track; beta stays on current beta inbox | Fastest bootstrap fix; delays Creator Rewards (beta) value |
| 9 | Two separate apps | SCAMPER/Substitute | Nurture app + Beta app, shared DB | Duplicates cascade, download, merge, feedback infra |
| 10 | Auto-promote profile nurture→beta | Persona (scrappy) | When nurture metrics hit threshold, auto-move profile to beta list | Operator loses control; pool assignment rules become ambiguous (out of scope v1) |

**Chosen:** Dual inbox + typed pools + shared core (spec §4 decisions 1–11).

**Validate before R7a lock:** 7-day manual tagging experiment — see Appendix B.

---

## Appendix B — Classifier Agreement Experiment (7-day)

**Goal:** Validate §6.2 auto-classify heuristics before R7a ships classifier.  
**Gate:** ≥80% operator agreement with proposed nurture/beta label.  
**If fail:** Fall back to alternative #5 (operator picks type at approve) for R7a; defer auto-classify to R7d.

### Prerequisites

- TrendDiscovery prototype OR manual export of 20–40 keyword candidates/day from YouTube trending + niche topics
- Spreadsheet or lightweight form — not production UI required
- Operator (1 person) who runs nurture + beta accounts daily

### Daily protocol (7 days)

| Step | Action |
| --- | --- |
| 1 | Collect candidates from trend sources (same inputs R7a will use) |
| 2 | Record: `keyword`, `phrase_length`, `trend_source`, `tiktok_video_count_7d`, `saturation_tier` |
| 3 | **Blind tag:** operator labels `nurture` or `beta` without seeing proposed classifier output |
| 4 | **Apply §6.2 rules:** compute proposed `keyword_type` from heuristics table |
| 5 | Mark `agree` if blind tag = proposed; note disagreements in `reason` column |

### Columns (spreadsheet)

```text
date | keyword | phrase_words | trend_source | tiktok_7d | saturation | operator_tag | proposed_tag | agree | reason
```

### Success criteria

| Metric | Target |
| --- | --- |
| Overall agreement | ≥80% (agree / total) |
| Beta agreement | ≥75% (beta is higher-stakes) |
| Nurture agreement | ≥80% |
| Sample size | ≥140 tagged rows (20/day × 7) |

### Disagreement triage

After day 3, cluster `reason` values:

- **Length boundary** — adjust word-count cutoffs
- **Saturation mismatch** — tune nurture "moderate OK" vs beta "prefer fresh"
- **Source ambiguity** — YouTube trending → nurture bias? niche topic → beta bias?
- **Operator inconsistency** — same operator re-tags conflicting → tighten tag definitions in prompt

### Outcomes

| Result | Action |
| --- | --- |
| ≥80% agreement | Ship auto-classifier in R7a; log `classification_confidence` for low-margin cases |
| 70–79% | Ship with operator override on inbox card (one-click reclassify before approve) |
| <70% | R7a uses operator-picks-type at approve; revisit heuristics in R7d with pattern data |

### Artifacts

Store results in `docs/decisions/` or story validation evidence:

```text
docs/superpowers/validation/2026-07-XX-classifier-agreement.md  (post-run summary)
```

Harness: `scripts/bin/harness-cli story update` with experiment metrics when linked to R7 story.
