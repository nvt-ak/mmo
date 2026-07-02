# US-002: FastAPI Backend & PostgreSQL

## Story Packet

| Doc | Purpose |
| --- | --- |
| [overview.md](US-002-api-backend/overview.md) | Problem, scope, success criteria |
| [design.md](US-002-api-backend/design.md) | Architecture, models, API surface |
| [execplan.md](US-002-api-backend/execplan.md) | Implementation phases |
| [validation.md](US-002-api-backend/validation.md) | Proof plan + results |
| [CHANGELOG.md](US-002-api-backend/CHANGELOG.md) | History |

## Status

implemented

## Lane

high-risk

## Product Contract

VideoScout exposes a REST API for keyword suggestion inbox workflow: scan YouTube
channels, score keywords, approve/reject suggestions, report outcomes, trigger
learning cycles, and manage settings. Data persists in PostgreSQL. Background
scan jobs run via APScheduler.

## Relevant Product Docs

- `docs/product/PRD.md` — sections 4-6 (workflow, scoring, learning)
- `docs/decisions/0008-web-only-fastapi-postgresql.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- FastAPI app starts via `videoscout.api_main:app` on port 8000
- Alembic migration creates suggestions, learning_events, channels, settings, scan_jobs
- API routes: suggestions, scan, sources, learning, settings
- Suggestion engine scores keywords (LLM + component weights)
- Learning agent processes feedback and suggests weight adjustments
- YouTube and TikTok service integrations wired
- APScheduler runs periodic channel scans
- CORS allows `localhost:3000`

## Design Notes

**Entry:** `videoscout/api_main.py`

**Routes:** `videoscout/api/{suggestions,scan,sources,learning,settings}.py`

**Engine:** `videoscout/core_engine/`

**Services:** `videoscout/services/youtube.py`, `videoscout/services/tiktok.py`

**DB:** `videoscout/db/models.py`, `alembic/versions/0001_initial_schema.py`

**Scheduler:** `videoscout/scheduler.py`

## Validation

```bash
python -m pytest videoscout/tests_api/ -v
```

| Layer | Expected proof |
| --- | --- |
| Unit | Per-route handler tests in `tests_api/test_*_api.py` |
| Integration | `tests_api/test_integration.py` — scan → approve → report → improve |
| E2E | Manual: web UI against live API (US-003) |
| Platform | PostgreSQL required; `alembic upgrade head` |

Harness update:

```bash
scripts/bin/harness-cli story update --id US-002 --status implemented \
  --unit 1 --integration 1 --e2e 0 --platform 0 \
  --verify "python -m pytest videoscout/tests_api/ -v"
```

## Harness Delta

- ADR 0008 records stack decision retroactively
- `docs/ARCHITECTURE.md` updated with web-only layout
- `videoscout/README.md` documents API entry (desktop deprecated)

## Evidence

- `videoscout/tests_api/` — 9 test modules
- `alembic/versions/0001_initial_schema.py`
- Retro alignment: 2026-07-02
