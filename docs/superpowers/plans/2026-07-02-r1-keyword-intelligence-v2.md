# R1 — Keyword Intelligence v2 (M1 Complete) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Module M1 — keyword inbox with enriched TikTok agent scoring, PostgreSQL-backed experiments, performance reports feeding the knowledge base, and web UI for report submission.

**Architecture:** Extend existing FastAPI + PostgreSQL stack (`videoscout/`). Port US-001 experiment/pattern logic from `videoscout/agents/learn_agent.py` into `videoscout/core_engine/experiments.py`. Store KB in PostgreSQL (`keyword_experiments`, `keyword_patterns`, `performance_reports`). Enrich `SuggestionEngine.score_keywords()` with full TikTok search stats. Add API routes + extend web `/insights`.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, Alembic, PostgreSQL, pytest (`videoscout/tests_api/`), Next.js 16, TanStack Query

## Global Constraints

- **Harness workflow:** Feature intake + story packet before code (`AGENTS.md`)
- **Stories:** US-010, US-011, US-012, US-013 (E04)
- **Product contract:** `docs/product/workflows.md`
- **No R2+ scope:** No channel cascade, download, merge in this plan
- **Desktop PyQt6:** Do not extend; port logic only
- **Proof:** `python -m pytest videoscout/tests_api/ -v` + `cd web && npm run build && npm run lint`
- **Harness update after each story:** `scripts/bin/harness-cli story update`

---

## File Structure (R1)

| File | Responsibility |
| --- | --- |
| `alembic/versions/0002_keyword_experiments.py` | New tables |
| `videoscout/db/models.py` | Experiment + pattern + report models |
| `videoscout/core_engine/experiments.py` | Ported US-001 logic (patterns, scoring formulas) |
| `videoscout/core_engine/knowledge_base.py` | Query performance_reports for agent context |
| `videoscout/core_engine/engine.py` | TikTok stats enrichment in scoring |
| `videoscout/api/experiments.py` | CRUD experiments |
| `videoscout/api/performance.py` | Submit/list performance reports |
| `videoscout/schemas.py` | Pydantic models |
| `videoscout/tests_api/test_experiments_api.py` | API tests |
| `videoscout/tests_api/test_performance_api.py` | API tests |
| `videoscout/tests_api/test_tiktok_scoring.py` | Scoring unit tests |
| `web/src/lib/api/client.ts` | New API methods |
| `web/src/lib/api/types.ts` | New types |
| `web/src/components/insights/performance-report-form.tsx` | Report UI |
| `docs/stories/US-010-*.md` … `US-013-*.md` | Story packets |

---

### Task 1: Story packets + harness registration (US-010–013)

**Files:**
- Create: `docs/stories/US-010-port-experiments-postgresql.md`
- Create: `docs/stories/US-011-tiktok-stats-scoring.md`
- Create: `docs/stories/US-012-performance-knowledge-base.md`
- Create: `docs/stories/US-013-web-experiments-insights.md`
- Modify: `docs/stories/backlog.md` (status → in_progress)

**Interfaces:**
- Produces: story IDs US-010–013 registered in harness-cli

- [ ] **Step 1: Create minimal story files from `docs/templates/story.md`**

Each story references `docs/product/workflows.md` M1 section and spec R1 scope.

- [ ] **Step 2: Register stories**

```bash
scripts/bin/harness-cli intake --type spec-slice \
  --summary "R1 M1: keyword intelligence v2" --lane normal --story US-010

scripts/bin/harness-cli story add --id US-010 \
  --title "Port keyword experiments to PostgreSQL" --lane normal \
  --verify "python -m pytest videoscout/tests_api/test_experiments_api.py -v"

scripts/bin/harness-cli story add --id US-011 \
  --title "TikTok search stats in agent scoring" --lane normal \
  --verify "python -m pytest videoscout/tests_api/test_tiktok_scoring.py -v"

scripts/bin/harness-cli story add --id US-012 \
  --title "Performance report knowledge base" --lane normal \
  --verify "python -m pytest videoscout/tests_api/test_performance_api.py -v"

scripts/bin/harness-cli story add --id US-013 \
  --title "Web performance report UI" --lane normal \
  --verify "cd web && npm run build && npm run lint"
```

- [ ] **Step 3: Mark US-010 in_progress**

```bash
scripts/bin/harness-cli story update --id US-010 --status in_progress
```

---

### Task 2: PostgreSQL schema — experiments + patterns + performance_reports (US-010)

**Files:**
- Create: `alembic/versions/0002_keyword_experiments.py`
- Modify: `videoscout/db/models.py`
- Create: `videoscout/tests_api/test_experiments_api.py`
- Test: `videoscout/tests_api/test_experiments_api.py`

**Interfaces:**
- Produces: `KeywordExperimentModel`, `KeywordPatternModel`, `PerformanceReportModel`
- Produces: SQLAlchemy models importable from `videoscout.db.models`

- [ ] **Step 1: Write failing test**

```python
# videoscout/tests_api/test_experiments_api.py
def test_create_experiment(client, db_session):
    resp = client.post("/api/v1/experiments", json={
        "keyword": "aespa winter fancam",
        "suggestion_source": "agent_suggested",
        "agent_suggested_score": 78,
        "channel_id": "UC_test",
        "channel_subscribers": 23000,
        "creator_avg_views": 2000,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["keyword"] == "aespa winter fancam"
    assert data["test_status"] == "in_progress"
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest \
  videoscout/tests_api/test_experiments_api.py::test_create_experiment -v
```

Expected: FAIL (404 or route missing)

- [ ] **Step 3: Add Alembic migration `0002_keyword_experiments.py`**

Tables (port from `videoscout/database/db.py` US-001 schema):

```python
# keyword_experiments: id UUID PK, keyword, channel_id nullable, channel_subscribers,
#   creator_avg_views, views_vs_baseline, suggestion_source CHECK, agent_suggested_score,
#   predicted_score, actual_views, actual_engagement, actual_score, test_status CHECK,
#   user_rating, accuracy, outcome_type, reported_at, created_at

# keyword_patterns: id UUID PK, pattern_type, keyword_trait, outcome_type, insight,
#   occurrence_count, confidence, suggested_adjustment JSONB, experiment_ids JSONB

# performance_reports: id UUID PK, keyword, suggestion_id FK nullable,
#   actual_views, actual_likes, actual_comments, actual_shares, followers_gained,
#   engagement_rate, outcome CHECK, reported_at, notes
```

Run: `alembic upgrade head`

- [ ] **Step 4: Add models to `videoscout/db/models.py`**

Match migration columns. Add relationships to `SuggestionModel` where applicable.

- [ ] **Step 5: Create `videoscout/api/experiments.py`**

```python
router = APIRouter()

@router.post("/experiments", status_code=201)
async def create_experiment(body: ExperimentCreate, db: Session = Depends(get_db)):
    ...

@router.get("/experiments")
async def list_experiments(status: str | None = None, db: Session = Depends(get_db)):
    ...

@router.post("/experiments/{id}/report")
async def report_experiment(id: UUID, body: ExperimentReport, db: Session = Depends(get_db)):
    ...
```

Register in `videoscout/api_main.py`:

```python
from videoscout.api import experiments
app.include_router(experiments.router, prefix="/api/v1", tags=["experiments"])
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest \
  videoscout/tests_api/test_experiments_api.py -v
```

- [ ] **Step 7: Harness proof**

```bash
scripts/bin/harness-cli story update --id US-010 --status implemented \
  --unit 1 --integration 1 --e2e 0 --platform 0 \
  --verify "python -m pytest videoscout/tests_api/test_experiments_api.py -v"
```

---

### Task 3: Port experiment logic — patterns + formulas (US-010 continued)

**Files:**
- Create: `videoscout/core_engine/experiments.py`
- Modify: `videoscout/tests/test_keyword_schema.py` (or move tests to `tests_api/test_experiments_engine.py`)
- Source reference: `videoscout/agents/learn_agent.py` (functions `_extract_patterns`, `compute_actual_score`, `classify_outcome`)

**Interfaces:**
- Consumes: `KeywordExperimentModel` rows from DB
- Produces:
  - `compute_actual_score(views_vs_baseline, engagement) -> float`
  - `classify_outcome(predicted, test_status) -> str`
  - `extract_patterns(experiments: list) -> list[dict]` (min 3 occurrences, min 0.6 confidence)
  - `suggest_weight_adjustments(patterns) -> list[dict]` (0.5x–2.0x cap, no auto-apply)

- [ ] **Step 1: Write failing unit test**

```python
# videoscout/tests_api/test_experiments_engine.py
from videoscout.core_engine.experiments import compute_actual_score

def test_compute_actual_score_doc_example():
    # views_vs_baseline=2.0, engagement=12% → ~89.4 per US-001 validation
    score = compute_actual_score(views_vs_baseline=2.0, engagement_rate=12.0)
    assert 88.0 <= score <= 90.0
```

- [ ] **Step 2: Implement `videoscout/core_engine/experiments.py`**

Copy formulas from US-001 validation.md (locked). No file I/O to `strategy.json` — store adjustments as suggestions returned via API only.

- [ ] **Step 3: Wire `POST /experiments/{id}/report` to compute actual_score, accuracy, outcome_type**

- [ ] **Step 4: Add `POST /experiments/analyze` → patterns + suggestions**

- [ ] **Step 5: Run tests**

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest \
  videoscout/tests_api/test_experiments_engine.py videoscout/tests_api/test_experiments_api.py -v
```

---

### Task 4: TikTok stats enrichment in agent scoring (US-011)

**Files:**
- Modify: `videoscout/core_engine/engine.py`
- Modify: `videoscout/services/tiktok.py`
- Modify: `videoscout/schemas.py` (add `TikTokSearchStats` to suggestion response)
- Create: `videoscout/tests_api/test_tiktok_scoring.py`

**Interfaces:**
- Consumes: `TikTokService.search_videos(keyword) -> dict`
- Produces: Each scored keyword includes:

```python
{
  "tiktok_stats": {
    "video_count_7d": int,
    "avg_views": float,
    "avg_likes": float,
    "avg_comments": float,
    "saturation_tier": "fresh" | "moderate" | "saturated"
  }
}
```

- [ ] **Step 1: Write failing test**

```python
# videoscout/tests_api/test_tiktok_scoring.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_score_keywords_includes_tiktok_stats():
    from videoscout.core_engine.engine import SuggestionEngine
    mock_tiktok = AsyncMock()
    mock_tiktok.search_videos.return_value = {
        "total_count": 15,
        "avg_views": 12000.0,
        "videos": [{"views": 10000, "likes": 500, "comments": 30}],
    }
    engine = SuggestionEngine()
    engine.tiktok = mock_tiktok
    # ... call score_keywords with one candidate, assert tiktok_stats present
```

- [ ] **Step 2: Extend `TikTokService.search_videos` return shape**

Ensure `avg_likes`, `avg_comments` computed from video list when API returns them.

- [ ] **Step 3: Update `calculate_saturation()` to return tier + attach stats dict**

Store on suggestion: `tiktok_status`, `tiktok_count_at_suggest`, extend `component_scores` or add JSON field `tiktok_stats` in DB if needed (Alembic `0003` only if required — prefer JSONB on suggestions).

- [ ] **Step 4: Run tests + full suite**

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/ -v
```

- [ ] **Step 5: Harness update US-011**

```bash
scripts/bin/harness-cli story update --id US-011 --status implemented \
  --unit 1 --integration 0 --e2e 0 --platform 0
```

---

### Task 5: Performance reports → knowledge base (US-012)

**Files:**
- Create: `videoscout/core_engine/knowledge_base.py`
- Create: `videoscout/api/performance.py`
- Create: `videoscout/tests_api/test_performance_api.py`
- Modify: `videoscout/core_engine/engine.py` (inject KB context into LLM prompt)

**Interfaces:**
- Produces:
  - `POST /api/v1/performance/reports` — submit TikTok stats for keyword
  - `GET /api/v1/performance/reports?keyword=` — history
  - `KnowledgeBase.get_context(keyword: str) -> str` — formatted snippet for LLM prompt

- [ ] **Step 1: Write failing test**

```python
def test_submit_performance_report(client):
    resp = client.post("/api/v1/performance/reports", json={
        "keyword": "aespa winter",
        "actual_views": 4500,
        "actual_likes": 320,
        "actual_comments": 45,
        "followers_gained": 12,
        "outcome": "success",
    })
    assert resp.status_code == 201
```

- [ ] **Step 2: Implement API + `KnowledgeBase`**

`get_context()` returns last N reports for keyword + aggregate stats for agent prompt in `extract_keywords()`.

- [ ] **Step 3: Link to learning — `PerformanceReport` also creates `LearningEventModel` type=`report`**

- [ ] **Step 4: Run tests**

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest \
  videoscout/tests_api/test_performance_api.py -v
```

- [ ] **Step 5: Harness update US-012**

---

### Task 6: Web UI — performance report + experiment list (US-013)

**Files:**
- Create: `web/src/components/insights/performance-report-form.tsx`
- Modify: `web/src/components/insights/insights-page.tsx`
- Modify: `web/src/lib/api/client.ts`
- Modify: `web/src/lib/api/types.ts`

**Interfaces:**
- Consumes: `POST /api/v1/performance/reports`, `GET /api/v1/experiments`

- [ ] **Step 1: Add API client methods**

```typescript
submitPerformanceReport: (payload: PerformanceReportPayload) =>
  apiFetch("/api/v1/performance/reports", { method: "POST", body: JSON.stringify(payload) }),

listExperiments: (status?: string) =>
  apiFetch<ExperimentListResponse>(`/api/v1/experiments${status ? `?status=${status}` : ""}`),
```

- [ ] **Step 2: Add form to `/insights`**

Fields: keyword (select from approved suggestions or free text), views, likes, comments, followers_gained, outcome.

- [ ] **Step 3: Show recent experiments table (in_progress / reported)**

- [ ] **Step 4: Verify frontend**

```bash
cd web && npm run build && npm run lint
```

- [ ] **Step 5: Harness update US-013 + E04 complete**

```bash
scripts/bin/harness-cli story update --id US-013 --status implemented \
  --unit 0 --integration 0 --e2e 0 --platform 1 \
  --verify "cd web && npm run build && npm run lint"
```

---

### Task 7: Docs + product alignment (R1 closeout)

**Files:**
- Modify: `docs/product/agent-learning-system.md` — PostgreSQL + web flow
- Modify: `docs/product/keyword-experiments.md` — web UI steps, remove PyQt6-only
- Modify: `docs/TEST_MATRIX.md` — add US-010–013 rows

- [ ] **Step 1: Update product docs to match implemented behavior**

- [ ] **Step 2: Run full proof**

```bash
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m pytest videoscout/tests_api/ -v
cd web && npm run build && npm run lint
scripts/bin/harness-cli query matrix
```

- [ ] **Step 3: Record intake completion**

```bash
scripts/bin/harness-cli intake --type change-request \
  --summary "R1 M1 complete" --lane normal --story US-013 \
  --notes "Experiments on PostgreSQL, TikTok stats, performance KB, web report UI"
```

---

## Self-Review

| Spec requirement | Task |
| --- | --- |
| Port US-001 to PostgreSQL | Task 2, 3 |
| TikTok stats in scoring | Task 4 |
| KB from performance reports | Task 5 |
| Web report UI | Task 6 |
| Harness stories | Task 1, 7 |
| No R2 cascade/download | Excluded ✓ |

No TBD placeholders. Types consistent across API/schemas/client.

---

## Execution Handoff

Plan saved to `docs/superpowers/plans/2026-07-02-r1-keyword-intelligence-v2.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks
2. **Inline Execution** — execute in this session with checkpoints

Which approach?
