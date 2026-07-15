# US-082: Keyword experiment ↔ suggestion FK (traceability)

## Status

implemented

## Lane

normal

## Product Contract

`keyword_experiments` supports durable, **prediction-time** linkage to the
inbox suggestion that motivated a test:

1. Optional FK `suggestion_id` → `suggestions.id`.
2. Required snapshot `prediction_signals` at create time — because live
   `suggestions.platform_signals` is overwritten on rediscovery upsert and is
   therefore not stable between create and outcome report.

Design:
`docs/superpowers/specs/2026-07-15-keyword-experiment-suggestion-fk-design.md`  
Plan:
`docs/superpowers/plans/2026-07-15-keyword-experiment-suggestion-fk.md`

Standalone rationale: general learning/infra traceability — **not** justified
solely by US-081 (that gate already works via `performance_reports` ⨝
`suggestions`).

## Intake

| Field | Value |
| --- | --- |
| Type | spec-slice |
| Lane | normal |
| Risk | Bounded migration + create API; no ranking change |

## Locked decisions

| Topic | Decision |
| --- | --- |
| Scope | Schema + API only (no web UI, no backfill) |
| Snapshot | Merged `agent.risk_flags` + whole `agent.validation` dict |
| Columns | `suggestion_id` UUID FK nullable + `prediction_signals` JSONB nullable |
| Create logic | Valid id → fill FK+snapshot; bad id → 400; no id → both null |
| Migration | `0020_keyword_experiment_suggestion_fk.py`, `down_revision="0019"` |

## Acceptance Criteria

### Schema

- [x] Alembic `0020`: add `suggestion_id` (FK `suggestions.id`, `ON DELETE SET NULL`,
      nullable) + `prediction_signals` (JSONB, nullable); index on `suggestion_id`
- [x] SQLAlchemy `KeywordExperimentModel` updated to match

### API

- [x] `ExperimentCreate` / `Experiment` schemas include optional
      `suggestion_id`, `prediction_signals`
- [x] `POST /experiments` with valid `suggestion_id` populates both columns from
      `platform_signals.agent`
- [x] Unknown `suggestion_id` → 400
- [x] Omit `suggestion_id` → both columns null (manual path)

### Tests

- [x] Unit/API coverage for the three create paths above
- [x] Existing experiment report/list tests still pass

## Non-goals

- Ranking / haircut / validation policy (US-081)
- Web create-from-suggestion UI
- Historical keyword-match backfill
- Changing `_upsert_scored_suggestion` overwrite behavior
- Full `platform_signals.agent` / blend snapshot
- Mandatory GIN indexes

## Validation

```bash
PYTHONPATH=. pytest videoscout/tests_api/test_experiments_api.py -v
```

Evidence (2026-07-15): **6 passed**.

## Related

- Spec / plan above
- US-080 / US-081 (consumers of risk/validation concepts; independent)
