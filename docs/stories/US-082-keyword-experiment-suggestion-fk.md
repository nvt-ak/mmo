# US-082: Keyword experiment ↔ suggestion FK (traceability)

## Status

planned

## Lane

normal

## Product Contract

`keyword_experiments` does not store `suggestion_id` and does not snapshot
`risk_flags` / validation from discovery. Creating an experiment from a suggestion
only copies prediction fields (`ExperimentCreate`). Joining outcomes back to
discovery risk signals therefore requires fragile keyword-string matching.

This breaks durable analytics for **any** post-hoc learning (not only viral-outlier
policy). Operators who report via `performance_reports` with `suggestion_id` retain
the join; experiment path does not.

## Goal

Add durable link from experiment → suggestion so later analysis can always join
prediction-time `platform_signals` (risk flags, validation adjustments, status)
without string matching.

## Scope (proposed)

- [ ] Alembic: `keyword_experiments.suggestion_id` UUID FK → `suggestions.id`
      (`ON DELETE SET NULL`), nullable for manual experiments
- [ ] `ExperimentCreate` / API: accept optional `suggestion_id`; validate exists
- [ ] Web create-from-suggestion flow passes suggestion id when present
- [ ] Tests: create with FK; create without FK (manual) still works
- [ ] Optional (same story or follow-up): snapshot `risk_flags` JSON at create time
      if denormalized query without join is desired

## Non-goals

- Ranking / haircut / validation policy (US-081 deferred)
- Backfilling historical experiments unless easy and optional in the same PR
- Changing `performance_reports` (already has `suggestion_id`)

## Rationale (standalone)

Traceability suggestion→experiment is a general learning-infra gap. It is **not**
justified solely because US-081 needs viral evidence — that gate already works via
`performance_reports` ⨝ `suggestions`.

## Validation (planned)

```bash
PYTHONPATH=. pytest videoscout/tests_api/test_experiments_api.py -v
```

## Related

- US-081 deferred evidence gate (reports ⨝ suggestions)
- US-001 / experiments API
