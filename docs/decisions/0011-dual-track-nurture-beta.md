# 0011 Dual-Track Nurture Beta

Date: 2026-07-02

## Status

Accepted

## Context

Post-R1 implementation still uses **channel-first scan** (`videoscout/api/scan.py`):
keyword suggestions require pre-seeded YouTube channels. Fresh install → 0 keywords
after successful scan.

This contradicts:

1. ADR 0009 keyword-led model — channels appear after keyword approve (cascade), not before.
2. Operator's real TikTok workflow — **nurture** accounts (trend/idol clone, broad keywords,
   light evaluation) vs **beta** accounts (Creator Rewards DE, long-tail, rigorous gate).

M1 workflow spec diagram also implied TikTok as discovery input; TikTok is evaluation-only.

Brainstorm review (2026-07-02) noted convergence quality is high but divergent-phase
artifacts were missing. This ADR records rejected alternatives, ICE rationale, pre-mortem,
and validation plan retroactively.

Full spec: `docs/superpowers/specs/2026-07-02-dual-track-keyword-discovery-design.md`.

## Decision

Adopt **dual pipeline, shared core** for keyword discovery and distribution.

| Topic | Decision |
| --- | --- |
| Discovery | Trend-first (`TrendDiscoveryJob`); YouTube/social/web — **not TikTok** |
| Keyword types | `keyword_type: nurture \| beta` on suggestions; separate inboxes |
| TikTok role | Gate only — light (nurture) vs full (beta) |
| Approve outcome | Typed media pool (`pool_type`), not profile binding |
| Profiles | `tiktok_profiles.stage`; manual nurture → beta promote |
| Channel scan | Deprecated as primary path; post-cascade rescan only |
| Learning | Beta-primary full loop; nurture aggregate/low priority |
| Rollout | R7a (foundation) → R7d (expanded trend sources) |

## Alternatives Considered

See also Appendix A in the dual-track spec for lens labels and extended kill reasons.

| # | Alternative | Kill reason |
| --- | --- | --- |
| 1 | **Keep channel-first scan** | Bootstrap failure; contradicts ADR 0009 |
| 2 | **Single inbox + `keyword_type` filter** | Nurture (fast, light) and beta (deep, full gate) review speeds conflict on one surface |
| 3 | **Global mode toggle** (nurture day / beta day) | Operator runs both daily; toggle hides half the pipeline |
| 4 | **Discovery fix only** — defer profiles/pools | Solves 0-keyword bug but not nurture/beta ops split |
| 5 | **Operator picks type at approve** (no auto-classify) | Lower classifier risk; extra click every approve; discovery can't pre-sort |
| 6 | **Profile-bound keywords** (approve → assign profile) | Breaks bulk-post factory model; pool separation harder |
| 7 | **TikTok as discovery source** | Circular with evaluation layer; contradicts corrected M1 boundary |
| 8 | **Nurture-only v1, beta later** | Fastest ship; delays Creator Rewards value unit |
| 9 | **Two separate apps** | Full duplication of cascade/download/merge infra |

**Chosen over highest-ICE option:** Discovery-only fix (ICE ~567) scores higher on ease,
but intentionally rejected — operator workflow fidelity requires nurture/beta separation
(ICE ~315 for dual-track, Impact 9).

## ICE Rationale (chosen vs top alt)

| Idea | Impact | Confidence | Ease | ICE | Biggest risk |
| --- | --- | --- | --- | --- | --- |
| Dual inbox + typed pools **(chosen)** | 9 | 7 | 5 | 315 | Classifier noise + route sprawl |
| Single inbox + filters | 6 | 8 | 8 | 384 | Mixed review UX |
| Discovery fix only | 7 | 9 | 9 | 567 | No nurture/beta ops split |
| Operator manual type at approve | 7 | 8 | 7 | 392 | Slower daily loop |

## Pre-Mortem (12 months, dual-track failed)

1. **Classifier noise** — operator reclassifies constantly; abandons nurture inbox.
2. **Beta pool starvation** — full gate + YouTube-only discovery → empty beta inbox for weeks.
3. **Route sprawl** — six new surfaces; operator reverts to spreadsheet.
4. **Type leakage bug** — nurture content assigned to beta profile despite constraints.
5. **Learning split** — beta improves, nurture stays dumb; operator blames whole system.

**Riskiest assumption to test first:** auto-classify nurture vs beta accuracy before
locking gate thresholds (§6.2 of spec).

**Cheap experiment:** 7-day manual tagging — run trend candidates, operator tags
nurture/beta post-hoc, measure agreement with proposed heuristics before R7a ships
classifier.

## Consequences

Positive:

- Fresh install bootstrap: trend discovery without manual channels.
- Typed pools enforce nurture/beta content separation at assign time.
- Shared cascade/download infra — no full pipeline fork.
- Corrects M1 discovery vs evaluation boundary (TikTok = gate).

Tradeoffs:

- Six new UI routes; daily time budget must reconcile with parent "<5 min active" target
  (spec §7 splits ~13 min across steps — clarify active vs async).
- Auto-classify heuristics (0.25/0.40 thresholds) unvalidated until experiment completes.
- `keyword` unique dedupe + first-type-wins may starve one track for ambiguous phrases.
- Nurture learning deprioritized — trend false positives may not feed back quickly.
- Social/web trend sources deferred to R7d — R7a YouTube-only may thin beta inbox.

## Follow-Up

- R7a: `keyword_type`, TrendDiscovery (YouTube v1), dual inbox, light/full gates.
- R7b: `tiktok_profiles`, typed pools, profile routes.
- R7c: bulk assign, learning split by `keyword_type`.
- R7d: social/web trend sources, classifier tuning from patterns.
- Update `docs/product/workflows.md`, `docs/ARCHITECTURE.md`, parent workflow spec amendment.
- Run 7-day classifier agreement experiment before locking §6.2 thresholds.
