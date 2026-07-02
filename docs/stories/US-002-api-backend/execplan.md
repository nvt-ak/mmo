# US-002 Execution Plan

Retroactive plan — phases reflect work already implemented (2026-06-30 → 2026-07-02).

## Phase 1: Database & Models (DONE)

- SQLAlchemy models for 6 tables
- Alembic migration `0001_initial_schema.py`
- Session factory + `get_db` dependency

**Files:**

- `videoscout/db/models.py`
- `videoscout/db/__init__.py`
- `alembic/versions/0001_initial_schema.py`
- `alembic.ini`, `alembic/env.py`

**Acceptance:**

- `alembic upgrade head` creates all tables
- Models match migration columns

## Phase 2: FastAPI Shell (DONE)

- App entry with lifespan (DB init + scheduler)
- CORS for localhost:3000
- Health endpoint
- Standard error JSON handler
- Pydantic schemas for all DTOs

**Files:**

- `videoscout/api_main.py`
- `videoscout/schemas.py`

**Acceptance:**

- `GET /health` returns 200
- Routers mount under `/api/v1`

## Phase 3: API Routes (DONE)

Implement all route modules:

| Module | Endpoints |
| --- | --- |
| `api/suggestions.py` | list, bulk-approve, bulk-reject, report, improve |
| `api/scan.py` | run, status, history |
| `api/sources.py` | channels CRUD |
| `api/settings.py` | get, put |
| `api/learning.py` | insights, cycle |

**Acceptance:**

- Each endpoint returns schema-valid JSON
- Suggestion lifecycle enforced in DB

## Phase 4: Engine & Services (DONE)

- Port/wire suggestion engine (`core_engine/engine.py`)
- Learning engine (`core_engine/learning.py`)
- YouTube + TikTok services
- Scan background task integration

**Files:**

- `videoscout/core_engine/*`
- `videoscout/services/youtube.py`, `tiktok.py`

**Acceptance:**

- Scan produces scored suggestions
- Learning cycle writes report record

## Phase 5: Scheduler (DONE)

- APScheduler daily cron from settings or env
- `scan_jobs` progress tracking
- Graceful shutdown on app lifespan exit

**Files:**

- `videoscout/scheduler.py`

**Acceptance:**

- Scheduler starts when `SCHEDULER_ENABLED=true`
- Disabled in test conftest

## Phase 6: Validation (DONE)

- Test fixtures: in-memory SQLite shim + TestClient
- Per-route tests + full integration workflow

**Files:**

- `videoscout/tests_api/conftest.py`
- `videoscout/tests_api/test_*.py`
- `pytest.ini`

**Acceptance:**

- `python -m pytest videoscout/tests_api/ -v` — 63 passed (2026-07-02)

## Phase 7: Harness Alignment (DONE)

- ADR 0008, story packet, matrix proof
- This execplan + design + overview (retro doc completion)

**Pending (follow-up stories):**

- US-004: browser E2E against live API
- Auth middleware
- Production PostgreSQL ops runbook
