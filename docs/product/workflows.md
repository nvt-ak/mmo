# VideoScout — Operator Workflow (Product Contract)

**Version:** 0.3  
**Date:** 2026-07-02  
**Status:** Active  
**Spec:** [`docs/superpowers/specs/2026-07-02-videoscout-workflow-design.md`](../superpowers/specs/2026-07-02-videoscout-workflow-design.md)  
**Dual-track amendment:** [`docs/superpowers/specs/2026-07-02-dual-track-keyword-discovery-design.md`](../superpowers/specs/2026-07-02-dual-track-keyword-discovery-design.md) (ADR 0011)

---

## 1. Business Goal

Automate **content discovery** for TikTok DE reup pipeline. Operator runs two tracks:

- **Nurture** — grow accounts via trend/idol clone (broad keywords, light TikTok gate)
- **Beta** — Creator Rewards DE (long-tail keywords, full agent + TikTok gate)

Active time target: **< 15 minutes/day** (review steps; async download/merge excluded).

Out of scope: upload automation (v1 handoff), account management outside profile registry.

---

## 2. North Star

Operator reviews **two daily keyword inboxes** (nurture + beta) from external trends →
approves → system builds **typed media pools** → operator bulk-posts from correct pool to
**nurture or beta TikTok profiles** → reports beta performance → agent improves beta scoring.

**Primary value units:**

- Nurture keyword → Nurture media pool → Nurture profiles
- Beta keyword → Beta media pool → Beta profiles

Legacy path (single inbox → merge → `data/finals/` handoff) remains for beta merge output;
R7 adds profile distribution layer on top.

---

## 3. Daily Operator Workflow

| Step | Action | Gate | Time (active) |
| --- | --- | --- | --- |
| 1 | Review **Nurture inbox** — trend source + light TikTok stats | Hard: approve \| reject | ~3 min |
| 2 | Review **Beta inbox** — full agent breakdown + TikTok insight + KB | Hard: approve \| reject | ~5 min |
| 3 | (Automatic) cascade → download per approved keyword | — | async |
| 4 | Batch review downloaded videos | Soft: Keep \| Skip | ~5 min |
| 5 | Merge (beta default; nurture optional) | — | as needed |
| 6 | **Nurture profiles** — bulk assign/post from Nurture pool | — | as needed |
| 7 | **Beta profiles** — bulk assign/post from Beta pool | — | as needed |
| 8 | (Async) Report beta TikTok performance → learning cycle | — | non-blocking |

**Pool quality gate:**

```text
download → pending_review
Keep → in_pool, pool_status: ready
bulk assign → assigned
post confirm → posted
```

---

## 4. Modules

| ID | Name | v1 Status |
| --- | --- | --- |
| M1 | Keyword Intelligence (dual-track) | Partial — R7 amends discovery |
| M2 | Channel Discovery | Implemented (R2) |
| M3 | Ingestion (download + watcher) | Implemented (R3) |
| M3b | Batch Review | Implemented (R4) |
| M4 | Production (merge) | Implemented (R5) |
| M5 | Feedback Loop | Implemented (R6) |
| M7 | Profile Distribution | Planned (R7b–c) |

---

## 5. Object Lifecycles

```text
KeywordSuggestion:  pending → approved | rejected  (keyword_type: nurture | beta)
VideoAsset:         downloaded → in_pool | skipped  (pool_type, pool_status)
MergeJob:           queued → processing → done | failed
FinalVideo:         ready  (pool_type inherited)
tiktok_profiles:    stage nurture → beta  (manual promote only)
profile_media_assignments: queued → posted | failed
PerformanceReport:  submitted → ingested  (beta-primary)
```

**Merge rules:**

- Random: 2 videos from merge pool, **same keyword**
- Manual: any 2 from merge pool
- Nurture: merge optional (single-clip clone OK)
- Beta: merge same-keyword as existing rules

**Constraints:** nurture profile cannot consume beta pool content and vice versa.

---

## 6. Success Metrics (v1)

| Metric | Target |
| --- | --- |
| Active time | < 15 min/day |
| Bootstrap | Fresh install → ≥5 nurture + ≥3 beta keywords after first discovery |
| Approve → pool ready | < 30 min async |
| Pool separation | 0 cross-type profile assignments |
| Beta agent accuracy | Improves over 4 weeks with M5 data |
| Merge job success | > 95% |

---

## 7. Out of Scope (v1)

- TikTok upload API automation (assign + handoff queue only)
- Multi-user auth
- Auto-promote nurture profile to beta
- Cloud storage for media pools
- PyQt6 desktop UI (deprecated)
- TikTok as keyword discovery source

---

## 8. Related Docs

| Doc | Purpose |
| --- | --- |
| `docs/superpowers/specs/2026-07-02-dual-track-keyword-discovery-design.md` | R7 dual-track spec |
| `docs/decisions/0011-dual-track-nurture-beta.md` | Dual-track ADR |
| `docs/product/agent-learning-system.md` | Learning architecture |
| `docs/product/keyword-experiments.md` | Experiment workflow |
| `docs/ARCHITECTURE.md` | System architecture |
| `docs/decisions/0009-keyword-led-content-factory.md` | Product pivot ADR |
