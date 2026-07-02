# Architecture

VideoScout — web-only keyword suggestion & learning system for YouTube → TikTok DE reup pipeline.

**Decision:** Web-only (Next.js + FastAPI). PyQt6 desktop UI deprecated.

See `docs/decisions/0008-web-only-fastapi-postgresql.md`.

See also: `docs/product/PRD.md`, `docs/decisions/`.

## System Overview

```text
┌─────────────────────────────────────────────┐
│  Frontend (Next.js + TypeScript)            │
│  Port: 3000                                 │
│  - Inbox (pending/approved suggestions)     │
│  - Sources (channel management)             │
│  - Settings (weights, niche, LLM config)      │
│  - Insights (learning analytics)            │
└──────────────┬──────────────────────────────┘
               │ HTTP REST + JSON
┌──────────────▼──────────────────────────────┐
│  Backend (FastAPI + Python)                 │
│  Port: 8000  —  videoscout/api_main.py      │
│  - API routes (suggestions, scan, etc.)     │
│  - Suggestion engine (LLM + scoring)        │
│  - Learning agent (patterns + weights)      │
│  - Services (YouTube, TikTok)               │
│  - Background tasks (APScheduler)           │
└──────────────┬──────────────────────────────┘
               │ SQL
┌──────────────▼──────────────────────────────┐
│  Database (PostgreSQL 14+)                  │
│  - suggestions, learning_events, channels   │
│  - settings                                 │
└─────────────────────────────────────────────┘
```

## Repository Layout

```text
videoscout/           # Backend (FastAPI, engine, services, agents)
  api_main.py         # API entry point
  api/                # Route handlers
  core_engine/        # Suggestion engine + learning
  services/           # YouTube, TikTok integrations
  db/                 # SQLAlchemy models
web/                  # Frontend (Next.js App Router)
docs/product/         # Product contract (PRD, domain docs)
docs/stories/         # Story packets
docs/decisions/       # ADRs
```

**Deprecated:** `videoscout/ui/` (PyQt6 desktop), `videoscout/main.py` (desktop entry).

## Product Modules (M1–M5)

Canonical workflow: `docs/product/workflows.md`. ADR: `docs/decisions/0009-keyword-led-content-factory.md`.
Dual-track amendment (R7): ADR `docs/decisions/0011-dual-track-nurture-beta.md`.

| Module | Responsibility | Phase |
| --- | --- | --- |
| M1 Keyword Intelligence | TrendDiscovery, dual inbox, agent score, learning | R1 (partial); R7 amends discovery |
| M2 Channel Discovery | Keyword → channels → subscribe (post-approve cascade) | R2 |
| M3 Ingestion | Download + watcher | R3 |
| M3b Batch Review | Keep/Skip daily UI | R4 |
| M4 Production | Merge → `data/finals/` | R5 |
| M5 Feedback | TikTok reports → KB (beta-primary) | R6 |
| M7 Profile Distribution | Typed pools → nurture/beta profile bulk post | R7b–c |

### M1 Discovery (R7)

```text
TrendDiscovery (YouTube / social / web)
  → classify keyword_type (nurture | beta)
  → TikTokEvaluator (gate only — not discovery)
  → dual inbox (pending)
```

Channel-first `api/scan` deprecated as primary path. TikTok is evaluation layer only.

### M7 Profile Distribution (R7)

```text
approve → cascade → download → batch → typed media pool
  → profile_media_assignments → nurture | beta TikTok profiles
```

Tables: `tiktok_profiles`, `pool_type` / `pool_status` on assets, `profile_media_assignments`.

**Planned additions:** `videoscout/workers/trend_discovery.py`, `api/discovery.py`, tables above.

## Tech Stack

| Layer | Technology | Port |
| --- | --- | --- |
| Frontend | Next.js + TypeScript + Tailwind | 3000 |
| Backend | FastAPI + Python | 8000 |
| Database | PostgreSQL 14+ | 5432 |
| State | TanStack React Query | — |

## Development

```bash
# Terminal 1: backend
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/videoscout
python -m uvicorn videoscout.api_main:app --reload --port 8000

# Terminal 2: frontend
cd web && npm install && npm run dev
# → http://localhost:3000
```

See `videoscout/README.md` and `web/README.md` for full setup.

## Layering & Boundary Rules

```text
domain
  <- application
      <- infrastructure
          <- interface
              <- app surfaces
```

### Dependency Rule

Inner layers must not depend on outer layers.

| Layer | May depend on | Must not depend on |
| --- | --- | --- |
| domain | nothing project-external except tiny pure utilities | framework, database, UI, provider, process/env |
| application | domain | framework, UI, provider, database concrete clients |
| infrastructure | domain, application | interface controllers or UI |
| interface | all backend layers | UI state or platform shell assumptions |
| app surfaces | API contracts and app-facing clients | domain internals directly |

### Parse-First Boundary Rule

Unknown data must be parsed at boundaries before it enters inner code.

Boundaries include HTTP request bodies, env vars, database rows, provider webhooks.

```text
unknown input → parser → typed DTO → use case → domain object
```

### Observability

Emit one canonical JSON log line per request with: timestamp, level, request_id,
user_id (when known), action, duration_ms, status_code, message.

Audit logs are product records. Application logs are operational records.
