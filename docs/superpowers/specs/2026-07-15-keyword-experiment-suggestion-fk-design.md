# VideoScout — Keyword Experiment ↔ Suggestion FK + Prediction Snapshot

**Date:** 2026-07-15  
**Status:** Approved (brainstorm 2026-07-15)  
**Lane:** normal (schema + API; no auth/stack change)  
**Story:** US-082  
**Related:** US-081 (deferred ranking; evidence via `performance_reports` ⨝ `suggestions` — independent), US-080 (sat undo lives under `validation.adjustments`)

---

## 1. Problem

`keyword_experiments` has no link to `suggestions`. Analysis that needs
discovery-time risk/validation context must join by keyword string (works only
while `suggestions.keyword` stays unique and unchanged).

Worse: even a live FK join to `suggestions.platform_signals` is **not**
prediction-time accurate. `_upsert_scored_suggestion()` overwrites
`platform_signals` when a later discovery pass raises `final_score` (or
reactivates). Outcomes are often reported days/weeks later — enough for one or
more rediscovery cycles — so a live join can return **current** flags, not the
flags present when the experiment was created.

## 2. Goal

1. Durable FK: `keyword_experiments.suggestion_id` → `suggestions.id` (nullable
   for manual experiments).
2. Required snapshot at create time: freeze merged `risk_flags` + full
   `validation` dict into `prediction_signals` JSONB so later analysis does not
   depend on mutable live `platform_signals`.

## 3. Decisions (locked)

| Topic | Decision |
| --- | --- |
| Scope | Schema + API only |
| Web create UI | Out — no `createExperiment` client today; separate story if needed |
| Historical backfill | Out — near-zero value (≈1 in_progress row); manual if ever needed |
| Snapshot content | Merged `agent.risk_flags` + **whole** `agent.validation` object (not cherry-picked fields) |
| Full `platform_signals.agent` copy | Rejected — pulls `component_reasons` / `blend` bloat; redundant with live suggestion via FK |
| Column shape | `suggestion_id` + single `prediction_signals` JSONB blob |
| Separate `risk_flags` / `validation` columns | Rejected — more nullable columns, no query advantage (`->'risk_flags' ?` still works) |
| Snapshot optional | Rejected — FK-only would promise “prediction-time” but deliver “current-time” |
| Ranking / haircut | Out of scope (US-081) |
| `performance_reports` | Unchanged (already has `suggestion_id`) |

## 4. Schema

Migration: `alembic/versions/0020_keyword_experiment_suggestion_fk.py`  
`down_revision = "0019"` (`0019_discovery_region_codes`).

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `suggestion_id` | UUID FK → `suggestions.id` | yes | `ON DELETE SET NULL`; index recommended |
| `prediction_signals` | JSONB | yes | Shape below, or SQL `NULL` |

### 4.1 `prediction_signals` shape

When linked:

```json
{
  "risk_flags": ["single_viral_source", "..."],
  "validation": {
    "validation_status": "weakened",
    "pattern_assessment": "mixed",
    "adjustments": {
      "generalizability": 0.0,
      "video_performance": -0.12,
      "confidence": -0.12,
      "saturation": 0.05
    },
    "risk_flags": ["..."],
    "validation_rationale": "..."
  }
}
```

Rules:

- `risk_flags` = copy of `platform_signals.agent.risk_flags` (already merge of
  scorer + validation flags after `apply_validation_result`).
- `validation` = copy of `platform_signals.agent.validation` if present; if agent
  has no `validation` key, store `"validation": null` inside the blob (still a
  non-null `prediction_signals` object when linked).
- Manual / no `suggestion_id`: column `prediction_signals` is SQL `NULL` (do not
  invent empty `{}`).

Query example later:

```sql
prediction_signals->'risk_flags' ? 'single_viral_source'
```

GIN/expression indexes deferred until needed.

## 5. API

### 5.1 `ExperimentCreate`

Add optional `suggestion_id: UUID | null`.

### 5.2 `POST /api/v1/experiments`

| Input | Behavior |
| --- | --- |
| `suggestion_id` present and row exists | Set FK; build `prediction_signals` from that suggestion’s agent block |
| `suggestion_id` present and missing | **HTTP 400** |
| omitted / null | `suggestion_id` and `prediction_signals` both SQL `NULL` |

Do **not** require `payload.keyword == suggestion.keyword` in this packet
(optional log/warn later).

### 5.3 Response (`Experiment`)

Expose `suggestion_id` and `prediction_signals` on read schemas.

## 6. Out of scope

- Web UI create-from-suggestion
- Backfill existing experiments by keyword match
- Snapshot of full `agent` / `blend` / `component_reasons`
- US-081 ranking policy
- Changing discovery upsert mutability (separate if ever desired)

## 7. Testing

- Create with valid `suggestion_id` → FK set; snapshot contains expected
  `risk_flags` and `validation` (incl. nested `adjustments` when present)
- Unknown `suggestion_id` → 400
- Create without `suggestion_id` → both new fields null
- Existing report/list experiment tests still pass

```bash
PYTHONPATH=. pytest videoscout/tests_api/test_experiments_api.py -v
```

## 8. Success criteria

- New experiments can carry immutable prediction-time risk/validation context.
- Live `suggestions.platform_signals` overwrite no longer silently corrupts
  experiment analytics that use `prediction_signals`.
- Manual experiments remain creatable without a suggestion.
