# US-002 Design Document

## Architecture

### Request Flow

```text
Web UI (US-003)
    ↓ HTTP JSON
FastAPI routers (videoscout/api/*)
    ↓
Application handlers + Pydantic schemas
    ↓
core_engine / services / db session
    ↓
PostgreSQL
```

### Background Scan Flow

```text
POST /api/v1/scan/run  OR  APScheduler cron
    ↓
For each enabled channel:
    YouTubeService.get_recent_videos()
    ↓
SuggestionEngine.extract_keywords() + score_keywords()
    ↓
Upsert suggestions (dedupe by keyword)
    ↓
Update scan_jobs progress
```

### Learning Flow

```text
Rejections + reports → learning_events
    ↓
POST /api/v1/learning/cycle
    ↓
LearningEngine analyzes patterns
    ↓
learning_reports + optional weight suggestions
    ↓
GET /api/v1/learning/insights
```

## Data Models

See `videoscout/db/models.py` and `alembic/versions/0001_initial_schema.py`.

| Table | Purpose |
| --- | --- |
| `suggestions` | Keyword inbox lifecycle (pending → approved/rejected → reported) |
| `learning_events` | Rejection/report feedback for learning |
| `learning_reports` | Cycle output (patterns, weight adjustments) |
| `channels` | YouTube sources to scan |
| `settings` | Scoring weights, niche, LLM/TikTok/scheduler config (single row) |
| `scan_jobs` | Background scan progress tracking |

### Suggestion Lifecycle

```text
pending → approved | rejected
approved → reported (with actual_views, outcome)
```

Status values: `pending`, `approved`, `rejected`, `reported`.

Component scores JSON: `relevance`, `specificity`, `saturation`, `trend`, `video_performance`.

## API Surface

Prefix: `/api/v1`

| Method | Path | Module |
| --- | --- | --- |
| GET | `/suggestions` | suggestions.py |
| POST | `/suggestions/bulk-approve` | suggestions.py |
| POST | `/suggestions/bulk-reject` | suggestions.py |
| POST | `/suggestions/{id}/report` | suggestions.py |
| POST | `/suggestions/improve` | suggestions.py |
| POST | `/scan/run` | scan.py |
| GET | `/scan/status/{job_id}` | scan.py |
| GET | `/scan/history` | scan.py |
| GET | `/sources/channels` | sources.py |
| POST | `/sources/channels` | sources.py |
| PUT | `/sources/channels/{channel_id}` | sources.py |
| DELETE | `/sources/channels/{channel_id}` | sources.py |
| GET | `/settings` | settings.py |
| PUT | `/settings` | settings.py |
| GET | `/learning/insights` | learning.py |
| POST | `/learning/cycle` | learning.py |

Health: `GET /health`

## Key Modules

| Path | Role |
| --- | --- |
| `videoscout/api_main.py` | App factory, CORS, lifespan, router mount |
| `videoscout/schemas.py` | Request/response Pydantic models |
| `videoscout/core_engine/engine.py` | Keyword extract + score |
| `videoscout/core_engine/learning.py` | Learning cycle logic |
| `videoscout/services/youtube.py` | YouTube Data API |
| `videoscout/services/tiktok.py` | TikTok saturation heuristic |
| `videoscout/scheduler.py` | APScheduler cron |
| `videoscout/db/__init__.py` | Session factory, `get_db` dependency |

## Error Contract

HTTP exceptions return JSON:

```json
{
  "error": {
    "code": "...",
    "message": "...",
    "details": null,
    "timestamp": "ISO8601"
  }
}
```

## Dependency Rules

- API routes parse input via Pydantic; no raw dicts in handlers
- DB access through SQLAlchemy session (FastAPI `Depends(get_db)`)
- Engine/services must not import FastAPI
- Background tasks use `get_session()` (separate from request-scoped session)

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/videoscout` | DB connection |
| `SCHEDULER_ENABLED` | `true` | Disable cron in tests |
| `SCHEDULE_TIME` | `09:00` | Fallback cron time |
| `YOUTUBE_API_KEY` | — | YouTube API |
| `OPENAI_API_KEY` | — | LLM scoring |

Tests override `DATABASE_URL=sqlite://` with JSONB→JSON shim in `tests_api/conftest.py`.
