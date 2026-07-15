# Keyword Experiment Suggestion FK (US-082) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add nullable `suggestion_id` FK and immutable `prediction_signals` JSONB snapshot on keyword experiment create.

**Architecture:** Alembic 0020 + model/schema updates; `create_experiment` loads suggestion when id provided, copies `agent.risk_flags` + whole `agent.validation` into `prediction_signals`, returns 400 on missing suggestion.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest, PostgreSQL JSONB.

## Global Constraints

- Schema + API only — no web UI, no backfill, no ranking changes.
- Snapshot required when linked; SQL NULL when manual.
- Migration `0020`, `down_revision = "0019"`.
- Spec: `docs/superpowers/specs/2026-07-15-keyword-experiment-suggestion-fk-design.md`.

## File map

| File | Role |
| --- | --- |
| `alembic/versions/0020_keyword_experiment_suggestion_fk.py` | Add columns |
| `videoscout/db/models.py` | `KeywordExperimentModel` columns |
| `videoscout/schemas.py` | `ExperimentCreate` / `Experiment` fields |
| `videoscout/api/experiments.py` | Create handler + snapshot helper |
| `videoscout/tests_api/test_experiments_api.py` | New create-path tests |
| `docs/stories/US-082-*.md` | Mark done after verify |

---

### Task 1: Failing API tests

**Files:** Modify `videoscout/tests_api/test_experiments_api.py`

- [ ] Add tests: linked create snapshots flags; bad id 400; manual both null
- [ ] Run suite — expect FAIL until model/API exist

### Task 2: Migration + model + schemas + API

**Files:** Create `0020_...py`; modify models, schemas, `experiments.py`

- [ ] Migration add `suggestion_id`, `prediction_signals`
- [ ] Helper `build_prediction_signals(suggestion) -> dict | None`
- [ ] Wire create endpoint
- [ ] Tests PASS

### Task 3: Story + harness evidence

- [ ] Checkbox US-082; `harness-cli story update`

---
