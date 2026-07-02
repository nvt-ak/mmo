# 0008 Web-Only FastAPI PostgreSQL Stack

Date: 2026-07-02

## Status

Accepted (retroactive)

## Context

VideoScout started as a PyQt6 desktop app with SQLite. Phase 2 work added a
Next.js web UI and FastAPI backend with PostgreSQL without a prior story packet
or ADR. Session agents produced code-first, then dumped summary markdown at repo
root — bypassing harness intake, decisions, and validation tracking.

Product needs a single operator surface (browser inbox) and a durable API for
suggestion workflow, channel scanning, settings, and learning cycles.

## Decision

Adopt a **web-only** architecture:

- **Frontend:** Next.js (App Router) in `web/` on port 3000
- **Backend:** FastAPI in `videoscout/` (`api_main.py`, `api/*`) on port 8000
- **Database:** PostgreSQL 14+ via SQLAlchemy + Alembic migrations
- **Scheduler:** APScheduler for background scan jobs

**Deprecate:**

- PyQt6 desktop UI (`videoscout/ui/`, `videoscout/main.py`) — keep for reference only
- SQLite as primary app database for the web workflow

## Alternatives Considered

1. **Hybrid PyQt6 + Next.js** — rejected: dual UI maintenance, data sync complexity
2. **Separate `backend/` package** — rejected: reuse existing `videoscout/` agents/services
3. **Keep SQLite for web** — rejected: concurrent API access, production deployment

## Consequences

Positive:

- Single source of truth (PostgreSQL)
- REST API enables web UI and future clients
- Existing agent/service logic stays in `videoscout/`

Tradeoffs:

- Desktop users must migrate to web UI
- Requires PostgreSQL in dev and prod
- Retro harness alignment needed (stories US-002, US-003)

## Follow-Up

- Story US-002: backend API + DB + scheduler (implemented, retro validation)
- Story US-003: web frontend (implemented, manual E2E pending)
- Update `docs/ARCHITECTURE.md` when stack changes again
- Record future stack changes as ADRs before implementation
