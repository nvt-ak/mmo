# US-081: Viral-outlier weakened / haircut policy (ranking)

## Status

deferred

## Lane

normal (ranking behavior — requires evidence before implementation)

## Product Contract

US-080 fixed **display** of saturation under `viral_outlier` (`adjustments.saturation = +0.05`).
Ranking still flows mainly through `validation_status` → haircut (`×0.95` when
`weakened`). Status rules are platform-asymmetric today (YouTube outlier →
`weakened`; TikTok-only outlier often stays `confirmed`).

**This story does not change ranking until the evidence gate below is met.**

Design: `docs/superpowers/specs/2026-07-15-viral-outlier-weakened-policy-deferred-design.md`

## Why deferred

- No production outcome corpus yet (`keyword_experiments` locally ≈ 1 in_progress;
  Postgres outcomes not available in agent sandbox; calibration still `linked_reports=0`).
- Shipping soft haircut / drop-elif / hybrid without outcomes would be ranking-by-intuition —
  inconsistent with verify-first practice used for US-080.
- YT/TT asymmetry may be **intentional** (narrow-ride vs high-variance markets) — unproven.

## Evidence gate (revisit trigger)

Re-open brainstorm for this story only when:

- ≥ **12** rows (acceptable 10–15) of
  `performance_reports` ⨝ `suggestions`
  where `platform_signals.agent.risk_flags` contains `single_viral_source`
  **and** report `outcome IS NOT NULL`.

Sample count query:

```sql
SELECT COUNT(*)
FROM performance_reports pr
JOIN suggestions s ON s.id = pr.suggestion_id
WHERE pr.suggestion_id IS NOT NULL
  AND pr.outcome IS NOT NULL
  AND s.platform_signals->'agent'->'risk_flags' ? 'single_viral_source';
```

Flags already persist on `suggestions.platform_signals` at discovery save — **no
new instrumentation required for this gate**. Do **not** depend on
`keyword_experiments` (no `suggestion_id` / no flag snapshot today).

## Open philosophy (decide at revisit — not now)

| Option | Change |
| --- | --- |
| Narrow status | Gate/remove `elif yt.get("viral_outlier"): status = "weakened"` |
| Soft haircut (Z) | Keep weakened; softer multiplier when outlier + n≥5 |
| Hybrid | Soft haircut for outlier-only paths on YT and TT |

**Rejected for this story forever unless separate epic:** recompute `final_score`
from all validation component adjustments (Y) — activates VP −0.12 as ranking
delta and near-cancels +0.05 sat undo under current weights.

## Non-goals

- [x] Zero code / zero migration in US-081
- [x] No haircut or status change while deferred
- [x] Experiment↔suggestion FK → **US-082** (independent gap)

## Depends on

- US-080 implemented (audit saturation undo)
- Operator-runable Postgres with reports linked to suggestions

## Acceptance when reopened

To be rewritten after evidence gate; until then success = gate documented and
status `deferred` in harness + backlog.
