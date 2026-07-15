# VideoScout — US-081 Viral-Outlier Ranking Policy (Deferred)

**Date:** 2026-07-15  
**Status:** Deferred (evidence gate — no ranking change until trigger met)  
**Lane:** normal  
**Story:** US-081  
**Related:** US-080 (audit saturation undo), US-082 (experiment↔suggestion FK, separate)

---

## 1. Problem

Concentrated search samples (`viral_outlier` / `single_viral_source`) can mislead
saturation **display** (fixed in US-080) and also drive **ranking** via
`validation_status=weakened` → `final_score *= 0.95`.

Current status rules are **asymmetric by platform**:

```text
confidence <= -0.15 OR fragmented → weakened
elif youtube.viral_outlier → weakened   # YouTube only
else → confirmed                        # TikTok-only outlier often stays confirmed
```

Whether this asymmetry is bug vs intentional (YouTube narrow-ride vs TikTok
high-variance) is **unproven**. Shipping narrow-status, soft haircut, or hybrid
without outcomes would be ranking-by-intuition.

## 2. Decision (locked)

| Topic | Decision |
| --- | --- |
| Ranking change now | **None** — defer US-081 |
| Soft haircut (Z) / drop YT elif / hybrid C | **Open** until evidence gate met |
| Recompute final from component adj (Y) | **Rejected** (see US-080 design) |
| Evidence path | `performance_reports` ⨝ `suggestions` (flags already on `platform_signals`) |
| `keyword_experiments` FK | **Out of scope** → US-082 (independent gap) |

## 3. Evidence gate (revisit trigger)

Re-open US-081 brainstorm → design → plan **only when**:

1. At least **N = 12** completed outcomes (default; acceptable band 10–15) where:
   - linked suggestion’s `platform_signals.agent.risk_flags` contains
     `single_viral_source`, **and**
   - report (or suggestion reported fields) has a real outcome — not
     experiment `in_progress` / empty outcome
2. Query is runnable on operator’s real Postgres (not empty local sandbox).

### 3.1 Sample query (illustrative)

```sql
SELECT
  pr.id AS report_id,
  pr.keyword,
  pr.outcome,
  pr.actual_views,
  s.final_score,
  s.platform_signals->'agent'->'risk_flags' AS risk_flags,
  s.platform_signals->'agent'->'validation'->'adjustments' AS validation_adj,
  s.platform_signals->'agent'->'validation'->>'validation_status' AS validation_status
FROM performance_reports pr
JOIN suggestions s ON s.id = pr.suggestion_id
WHERE pr.suggestion_id IS NOT NULL
  AND pr.outcome IS NOT NULL
  AND s.platform_signals->'agent'->'risk_flags' ? 'single_viral_source';
```

Optional slice for US-080 audit presence:

```sql
  AND (s.platform_signals->'agent'->'validation'->'adjustments'->>'saturation')::float = 0.05
```

Count:

```sql
SELECT COUNT(*) FROM ( /* same join filters */ ) t;
-- reopen when COUNT >= 12
```

## 4. What stays true until then

- US-080 saturation +0.05 audit/display only — unchanged.
- No change to haircut magnitudes or `elif yt viral_outlier` status branch.
- YT/TT asymmetry treated as **unresolved product hypothesis**, not a defect to fix “for fairness.”

## 5. Deferred design options (reminders only)

When gate clears, re-decide among prior options with data:

| Option | Idea |
| --- | --- |
| Narrow status | Gate/remove YT-only `elif` weakened |
| Soft haircut (Z) | Keep weakened; softer multiplier when n≥5 |
| Hybrid | Soft haircut for outlier-only paths on both platforms |

## 6. Success for this packet

- Story status `deferred` with gate + query above.
- Zero application code / migration in US-081.
- US-082 recorded separately for experiment traceability.
