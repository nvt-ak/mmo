# US-066 Trend Cluster — Duplicate Keyword Grouping (Phase 2)

Status: implemented
ADR: 0014 (Phase 2)
Intake: normal — flags: data model (new entity + migration), existing behavior
(ranking/inbox persist path changes), public contracts (inbox response shape
adds cluster grouping). No hard gate (auth/authorization/data-loss/audit/
external-provider) triggered; migration is additive-only (new table + nullable
FK), not destructive.

## Goal

Group near-duplicate keyword candidates that represent the same underlying
content pattern into a single **Trend Cluster** before inbox persist, so the
operator approves one opportunity instead of reviewing N near-duplicate
keyword variants of it (ADR 0014 problem #5: "Keyword as scored object").

## Design Decision (from brainstorm, pre-story)

Three clustering approaches were considered:

1. Embedding similarity (cosine, offline) — most accurate, but requires new
   embedding infra; none exists today (`engine.calculate_relevance()` is a
   Phase-1 string-match stub explicitly marked "in production use
   sentence-transformers" — never implemented).
2. LLM-based grouping (single call over Top-N) — no new infra, but adds
   token cost and run-to-run instability.
3. **Hybrid (chosen)** — cheap heuristic dedup (normalized token overlap)
   runs on *every* candidate (Tier-0-equivalent cost); only ambiguous
   near-duplicate pairs are escalated into the existing `validation_pass.py`
   LLM call (delta-only, already budgeted per ADR 0014) with a grouping
   question added to its payload.

Chosen because it matches the pipeline's existing tiering philosophy (cheap
for all candidates, expensive only for Top-N / ambiguous cases — ADR 0013
Tier 0–2, ADR 0014 validation-is-delta-not-rescore) instead of introducing a
parallel processing path.

## Relevant Product Docs

- `docs/product/workflows.md` (M1 Keyword Intelligence)
- `docs/ARCHITECTURE.md` (M1 Discovery pipeline)
- `docs/decisions/0013-trend-evidence-discovery-pipeline.md`
- `docs/decisions/0014-search-sample-validation-evidence.md`

## Scope (Phase 2 per ADR 0014 roadmap: "Trend Cluster entity")

### In scope

- [x] Heuristic dedup pass (Tier 0, all candidates): normalized token
      overlap (Jaccard) on keyword text, after stripping the existing
      generic-token set (reuse nurture generic-token list — do not fork it)
- [x] Configurable overlap threshold band: below = distinct, above = auto
      same cluster, in-between = ambiguous → escalate
- [x] Ambiguous pairs added to the existing Top-N validation LLM payload as
      a grouping question (extend `validation_pass.py` contract; do not add
      a third LLM call)
- [x] New `TrendCluster` entity/table: id, canonical_keyword, member
      keyword ids, created_at, `pipeline_run_id`
- [x] `cluster_id` (nullable FK) added to keyword/suggestion row — nullable
      because most candidates will not cluster
- [x] Inbox API: keywords in the same cluster render grouped/collapsed;
      member keywords still individually visible on expand
- [ ] `schema_version` bump note on any TrendEvidence field touched (per
      ADR 0013 rule 5) — N/A; no TrendEvidence fields changed
- [x] Tests: heuristic overlap unit tests, threshold-band boundary cases,
      validation payload extension, cluster persistence, inbox grouping

### Explicitly out of scope (do not resolve in this story)

- Opportunity Model (`durability`, `dependency_risk`) — Phase 3 / US-067
- Embedding-based clustering infra — only revisit if heuristic recall proves
  insufficient in practice; not a Phase 2 blocker
- Multi-region trend clustering
- Changing existing rubric scoring weights or `history_prior` math

### Open design questions (resolved in implementation)

1. **Canonical alias selection** — highest `final_score` member after ranking
   (stable, no extra LLM label).
2. **`history_prior` interaction** — each member keeps independent
   `history_prior` at scoring time; no cluster-level penalty in Phase 2.
3. **Threshold tuning source** — fixed defaults (`CLUSTER_JACCARD_LOW=0.35`,
   `CLUSTER_JACCARD_HIGH=0.65`) with env override at ship time.

## Acceptance Criteria

- Near-duplicate keyword candidates from the same discovery job are grouped
  under one Trend Cluster in the inbox instead of appearing as separate rows.
- Heuristic pass runs on 100% of candidates without adding a new LLM call.
- Ambiguous-band pairs are resolved via the existing validation LLM call,
  not a new one.
- Approving or rejecting a cluster's canonical entry does not silently
  approve/reject unrelated non-member keywords.
- No change to nurture/beta scoring rubric weights.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | heuristic overlap function, threshold-band boundaries, cluster assignment logic |
| Integration | validation_pass.py payload extension, TrendCluster persistence round-trip |
| E2E | discovery job run → inbox shows grouped cluster → approve flow unaffected for non-clustered keywords |
| Platform | — |
| Release | — |

When updating durable proof status:
`scripts/bin/harness-cli story update --id US-066 --unit 0 --integration 0 --e2e 0 --platform 0`

## Harness Delta

None yet — file created directly as part of intake for this initiative
(Nhóm B priority from keyword-discovery brainstorm, 2026-07-13). Register in
`harness.db` via `scripts/bin/harness-cli story add` (run locally; CLI binary
in this sandbox is macOS arm64 and cannot execute here).

## Evidence

```bash
python -m pytest videoscout/tests_api/test_trend_cluster.py videoscout/tests_api/test_trend_cluster_integration.py videoscout/tests_api/test_validation_pass.py -v
cd web && npm run lint && npm run build
alembic upgrade head
```
