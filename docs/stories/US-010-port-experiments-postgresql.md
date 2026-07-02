# US-010: Port Keyword Experiments to PostgreSQL

## Status

in_progress

## Lane

normal

## Product Contract

Complete Module **M1 (Keyword Intelligence)** by porting US-001 keyword experiment
tracking from desktop SQLite/PyQt6 to PostgreSQL-backed REST API. Operators can
start experiments, report TikTok outcomes, and trigger pattern analysis — all
persisted in PostgreSQL and accessible to the web stack.

**Epic:** E04 Keyword Intelligence v2  
**Roadmap:** R1 — M1 complete (`docs/superpowers/plans/2026-07-02-r1-keyword-intelligence-v2.md`)

## Relevant Product Docs

- `docs/product/workflows.md` — Module M1 (Keyword Intelligence), object lifecycle `PerformanceReport: submitted → ingested`
- `docs/product/keyword-experiments.md` — experiment start/report workflow (port to web)
- `docs/superpowers/plans/2026-07-02-r1-keyword-intelligence-v2.md` — Tasks 2–3
- `docs/decisions/0009-keyword-led-content-factory.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- Alembic migration `0002_keyword_experiments` creates `keyword_experiments`, `keyword_patterns`, `performance_reports` tables
- SQLAlchemy models in `videoscout/db/models.py` match migration columns
- API routes: `POST /api/v1/experiments`, `GET /api/v1/experiments`, `POST /api/v1/experiments/{id}/report`, `POST /api/v1/experiments/analyze`
- `videoscout/core_engine/experiments.py` ports US-001 formulas: `compute_actual_score`, `classify_outcome`, `extract_patterns`, `suggest_weight_adjustments`
- Pattern extraction requires min 3 occurrences, min 0.6 confidence; weight adjustments capped 0.5x–2.0x, no auto-apply
- No file I/O to legacy `strategy.json`; adjustments returned via API only
- PyQt6 desktop UI not extended — logic port only

## Design Notes

- **Commands:** `alembic upgrade head`
- **Queries:** CRUD on `keyword_experiments`; pattern rows in `keyword_patterns`
- **API:** `videoscout/api/experiments.py` registered in `videoscout/api_main.py`
- **Tables:** `keyword_experiments`, `keyword_patterns`, `performance_reports` (schema shared with US-012)
- **Domain rules:** Port from `videoscout/agents/learn_agent.py` — locked US-001 validation formulas
- **UI surfaces:** Web experiment list deferred to US-013; this story is API + engine only

## Validation

```bash
python -m pytest videoscout/tests_api/test_experiments_api.py -v
python -m pytest videoscout/tests_api/test_experiments_engine.py -v
```

| Layer | Expected proof |
| --- | --- |
| Unit | `test_experiments_engine.py` — formula parity with US-001 |
| Integration | `test_experiments_api.py` — create, list, report, analyze |
| E2E | Manual via US-013 web UI |
| Platform | PostgreSQL + `alembic upgrade head` |
| Release | Harness story update with verify command |

Harness update on completion:

```bash
scripts/bin/harness-cli story update --id US-010 --status implemented \
  --unit 1 --integration 1 --e2e 0 --platform 0 \
  --verify "python -m pytest videoscout/tests_api/test_experiments_api.py -v"
```

## Harness Delta

- Registered via Task 1 intake: `spec-slice` "R1 M1: keyword intelligence v2"
- Verify command: `python -m pytest videoscout/tests_api/test_experiments_api.py -v`

## Evidence

_Add commands, reports, or links after validation exists._
