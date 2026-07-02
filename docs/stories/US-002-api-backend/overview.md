# US-002: FastAPI Backend & PostgreSQL — Overview

## Current Behavior (before)

- PyQt6 desktop app with SQLite (`videoscout/database/`)
- No REST API; UI talks to DB directly
- Agent logic in `videoscout/agents/` not exposed to web clients

## Target Behavior (after)

- FastAPI app on port 8000 serves `/api/v1/*` for web UI
- PostgreSQL persists suggestions, channels, settings, learning events
- APScheduler runs daily channel scans in background
- Suggestion engine + learning agent callable via HTTP
- CORS open for `localhost:3000`

## Problem Statement

Web frontend (US-003) needs a stable API contract. Desktop SQLite cannot serve concurrent HTTP clients or production deployment.

## Solution

Port domain logic into `videoscout/api/*`, SQLAlchemy models in `videoscout/db/`, Alembic migrations, reuse existing services and core engine.

## Scope

### In Scope

- FastAPI entry (`api_main.py`) + health check
- Routes: suggestions, scan, sources, learning, settings
- PostgreSQL schema (6 tables) + Alembic `0001_initial_schema`
- APScheduler daily scan
- Pydantic schemas (`videoscout/schemas.py`)
- API test suite (`videoscout/tests_api/`)

### Out of Scope

- JWT auth (future story)
- Production deploy / Docker
- Migrating US-001 keyword_experiments tables to PostgreSQL
- Real TikTok API (heuristic/mock remains)

## Success Criteria

| Criterion | Target |
| --- | --- |
| API starts | `uvicorn videoscout.api_main:app` |
| CRUD suggestions | list, bulk approve/reject, report, improve |
| Scan workflow | run job, poll status, history |
| Channel management | list, add, update, delete |
| Settings | get/put weights + niche |
| Learning | insights + cycle trigger |
| Automated proof | 63+ tests passing |

## Stakeholders

- **Operator** — uses web UI via API
- **US-003 frontend** — typed client consumer
- **Agents** — must follow story packet for future API changes

## Non-Goals

- PyQt6 UI maintenance
- SQLite as primary store for web workflow
- Separate `backend/` package
