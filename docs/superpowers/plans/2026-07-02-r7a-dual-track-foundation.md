# R7a — Dual-Track Foundation Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans. Track steps with `- [ ]`.

**Goal:** R7a foundation — trend-first keyword discovery, `keyword_type` nurture/beta, dual inbox UI, light vs full TikTok gate. Deprecate channel-first scan as primary.

**Architecture:** Extend FastAPI + PostgreSQL. New `TrendDiscoveryJob` worker replaces channel-first `POST /scan/run` as primary path. Shared `SuggestionEngine` with gate profiles. Classifier agreement experiment (Appendix B) gates auto-classify ship.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, Alembic, PostgreSQL, pytest, Next.js 16, TanStack Query

**Spec:** `docs/superpowers/specs/2026-07-02-dual-track-keyword-discovery-design.md`  
**ADR:** `docs/decisions/0011-dual-track-nurture-beta.md`  
**Story:** US-051

## Global Constraints

- Harness: intake + story before code (`AGENTS.md`)
- **No R7b–d scope:** no `tiktok_profiles`, typed pools UI, bulk assign
- Classifier: ship auto-classify only if Appendix B ≥80%; else operator-picks-type fallback
- Channel scan retained as `job_type=channel_rescan` secondary path
- Proof: `pytest videoscout/tests_api/ -v` + `cd web && npm run build && npm run lint`

---

## File Structure (R7a)

| File | Responsibility |
| --- | --- |
| `alembic/versions/0009_keyword_type_discovery.py` | `keyword_type`, discovery columns on suggestions; `discovery_jobs` |
| `videoscout/db/models.py` | Extend `SuggestionModel`; `DiscoveryJobModel` |
| `videoscout/core_engine/keyword_classifier.py` | §6.2 nurture/beta heuristics |
| `videoscout/core_engine/trend_discovery.py` | Candidate extract + classify + gate orchestration |
| `videoscout/workers/trend_discovery.py` | Background job runner |
| `videoscout/services/youtube.py` | `get_trending_videos(region_code)` |
| `videoscout/api/discovery.py` | `POST /discovery/run`, progress/history |
| `videoscout/api/suggestions.py` | Filter by `keyword_type` |
| `videoscout/core_engine/engine.py` | Light vs full TikTok gate profiles |
| `videoscout/schemas.py` | Discovery + dual-inbox types |
| `web/src/app/today/nurture/page.tsx` | Nurture inbox |
| `web/src/app/today/beta/page.tsx` | Beta inbox |
| `web/src/components/inbox/inbox-page.tsx` | Shared inbox w/ `keywordType` prop |
| `scripts/run_classifier_experiment.py` | Appendix B day-run tooling |
| `docs/superpowers/validation/*-classifier-agreement.md` | Experiment results |

---

### Task 1: Story packet + harness (US-051)

**Files:**
- Create: `docs/stories/US-051-dual-track-discovery-foundation.md`
- Modify: `docs/stories/backlog.md`

- [ ] **Step 1: Create story US-051**

- [ ] **Step 2: Register intake + story**

```bash
scripts/bin/harness-cli intake --type spec-slice \
  --summary "R7a dual-track discovery foundation" --lane normal --story US-051

scripts/bin/harness-cli story add --id US-051 \
  --title "Dual-track trend discovery foundation" --lane normal \
  --verify "python -m pytest videoscout/tests_api/test_discovery.py videoscout/tests_api/test_keyword_classifier.py -v"
```

- [ ] **Step 3: Mark in_progress**

```bash
scripts/bin/harness-cli story update --id US-051 --status in_progress
```

---

### Task 2: Schema — keyword_type + discovery_jobs (US-051)

**Files:**
- Create: `alembic/versions/0009_keyword_type_discovery.py`
- Modify: `videoscout/db/models.py`

- [ ] **Step 1: Failing test** — suggestion requires `keyword_type`; discovery job lifecycle

- [ ] **Step 2: Migration columns on `suggestions`**

```text
keyword_type      VARCHAR NOT NULL DEFAULT 'beta'  -- backfill existing
discovery_source  VARCHAR nullable
trend_signals     JSONB nullable
gate_profile      VARCHAR nullable  -- light | full
```

- [ ] **Step 3: `discovery_jobs` table**

```text
id, status, job_type (trend_discovery|channel_rescan), keyword_type_filter,
sources_scanned, keywords_generated, error_message, started_at, completed_at
```

- [ ] **Step 4: `alembic upgrade head` + models**

---

### Task 3: Keyword classifier (US-051)

**Files:**
- Create: `videoscout/core_engine/keyword_classifier.py`
- Create: `videoscout/tests_api/test_keyword_classifier.py`

**Interfaces:**

```python
def classify_keyword_type(
    keyword: str,
    *,
    trend_source: str,  # youtube_trend | social | niche_web | manual
    saturation_tier: str | None = None,  # fresh | moderate | saturated
    agent_score: float | None = None,
) -> Literal["nurture", "beta"]
```

Rules per spec §6.2:
- phrase length 2–3 + youtube_trend/social → nurture bias
- phrase length 4–5 + niche_web → beta bias
- saturation moderate/saturated + short phrase → nurture
- saturation fresh + long phrase → beta
- agent_score thresholds 0.25 nurture / 0.40 beta when present

- [ ] Unit tests for boundary cases (2 vs 3 vs 4 words, each source, saturation tiers)

---

### Task 4: YouTube trending source (US-051)

**Files:**
- Modify: `videoscout/services/youtube.py`
- Create: `videoscout/tests_api/test_youtube_trending.py` (mocked)

- [ ] **Add `get_trending_videos(region_code="DE", max_results=50)`**

Uses `videos().list(chart="mostPopular", regionCode=...)`.

- [ ] **Extract keyword candidates from titles** — heuristic in `trend_discovery.py`:
  strip stopwords, emit 2–5 word phrases, dedupe

---

### Task 5: TrendDiscovery worker + API (US-051)

**Files:**
- Create: `videoscout/core_engine/trend_discovery.py`
- Create: `videoscout/workers/trend_discovery.py`
- Create: `videoscout/api/discovery.py`
- Create: `videoscout/tests_api/test_discovery.py`
- Modify: `videoscout/api_main.py`

**Pipeline:**

```text
TrendDiscoveryJob
  → fetch youtube_trend
  → extract candidates
  → classify keyword_type (or defer if experiment <80%)
  → TikTokEvaluator gate (light|full)
  → upsert suggestions (pending)
```

- [ ] `POST /api/v1/discovery/run` body: `{ keyword_type_filter: nurture|beta|both }`
- [ ] `GET /api/v1/discovery/jobs/{id}` progress
- [ ] `GET /api/v1/discovery/jobs` history
- [ ] Mark `scan/run` deprecated in OpenAPI description; keep functional

**Classifier fallback (if experiment <80%):**
- Set `keyword_type` null on insert; operator picks on approve UI
- Or env `CLASSIFIER_MODE=manual|auto`

---

### Task 6: TikTok gate profiles (US-051)

**Files:**
- Modify: `videoscout/core_engine/engine.py`
- Modify: `videoscout/schemas.py`

| Profile | Behavior |
| --- | --- |
| `light` (nurture) | `video_count_7d`, saturation; on failure → `tiktok_unverified` badge, still surface |
| `full` (beta) | Full stats + component scores + KB; on failure → exclude from inbox |

- [ ] Extend suggestion response: `gate_profile`, `tiktok_unverified: bool`
- [ ] Tests: mock TikTok timeout → nurture surfaces, beta blocked

---

### Task 7: Dual inbox API filters (US-051)

**Files:**
- Modify: `videoscout/api/suggestions.py`

- [ ] `GET /api/v1/suggestions?status=pending&keyword_type=nurture`
- [ ] `GET /api/v1/suggestions?status=pending&keyword_type=beta`
- [ ] Default `/today` redirect or keep with filter param (deprecation notice)

---

### Task 8: Web dual inbox (US-051)

**Files:**
- Create: `web/src/app/today/nurture/page.tsx`
- Create: `web/src/app/today/beta/page.tsx`
- Modify: `web/src/components/inbox/inbox-page.tsx`
- Modify: `web/src/components/layout/app-shell.tsx` nav
- Modify: `web/src/lib/api/client.ts`, `types.ts`

- [ ] Nurture inbox: compact cards, light TikTok stats, `tiktok_unverified` badge
- [ ] Beta inbox: full agent breakdown (existing card depth)
- [ ] Nav: Today → Nurture | Beta sub-links
- [ ] `KeywordScanButton` → `POST /discovery/run` (replace channel scan CTA on inbox)

---

### Task 9: Classifier experiment validation (gate)

**Files:**
- `scripts/run_classifier_experiment.py` (exists from prep)
- `docs/superpowers/validation/2026-07-02-classifier-agreement-day1.md`

- [ ] Run 7 days per Appendix B OR minimum day 1 + operator tag fill
- [ ] If ≥80% → `CLASSIFIER_MODE=auto` default
- [ ] If <70% → implement operator-picks-type on approve (Task 8 add-on)

---

### Task 10: Docs + harness closeout

- [ ] Update `docs/stories/backlog.md` R7 row
- [ ] Full proof:

```bash
python -m pytest videoscout/tests_api/ -v
cd web && npm run build && npm run lint
scripts/bin/harness-cli story update --id US-051 --status implemented \
  --unit 1 --integration 1 --e2e 0 --platform 1
scripts/bin/harness-cli query matrix
```

---

## Self-Review

| Spec § | Task |
| --- | --- |
| R7a keyword_type | Task 2 |
| TrendDiscovery YouTube v1 | Task 4, 5 |
| Dual inbox UI | Task 7, 8 |
| Light vs full gate | Task 6 |
| Deprecate channel-first | Task 5, 8 |
| Appendix B gate | Task 9 |
| No profiles/pools (R7b) | Excluded ✓ |

---

## Execution Handoff

Plan: `docs/superpowers/plans/2026-07-02-r7a-dual-track-foundation.md`

1. **Subagent-Driven** — one task per subagent
2. **Inline** — sequential in session
