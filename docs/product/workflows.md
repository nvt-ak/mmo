# VideoScout — Operator Workflow (Product Contract)

**Version:** 0.2  
**Date:** 2026-07-02  
**Status:** Active  
**Spec:** [`docs/superpowers/specs/2026-07-02-videoscout-workflow-design.md`](../superpowers/specs/2026-07-02-videoscout-workflow-design.md)

---

## 1. Business Goal

Automate **content discovery** for TikTok DE reup pipeline. Operator active time
target: **< 15 minutes/day**.

Out of scope: download tool (legacy), upload, account management — except VideoScout
v1 builds download + merge in-repo per ADR 0009.

---

## 2. North Star

Operator approves agent-scored **keywords** → system auto-handles channels,
download, and monitoring → operator curates daily batch → merges videos →
**final files in `data/finals/`** → handoff to upload tool (v1).

---

## 3. Daily Operator Workflow

| Step | Action | Gate |
| --- | --- | --- |
| 1 | Review keyword inbox | **Hard:** approve \| reject |
| 2 | (Automatic) channel discovery, subscribe, bulk download trigger | — |
| 3 | Daily batch review downloaded videos | **Soft:** Keep \| Skip |
| 4 | Merge: manual (any 2) or random (same keyword) | — |
| 5 | Collect finals from `data/finals/` | — |
| 6 | (Async) Report TikTok performance → improves agent | — |

---

## 4. Modules

| ID | Name | v1 Status |
| --- | --- | --- |
| M1 | Keyword Intelligence | Partial (US-002/003) |
| M2 | Channel Discovery | Partial (discover + subscribe done in R2) |
| M3 | Ingestion (download + watcher) | Implemented (R3) |
| M3b | Batch Review | Implemented (R4) |
| M4 | Production (merge) | Planned (R5) |
| M5 | Feedback Loop | Partial (US-001 desktop) |

---

## 5. Object Lifecycles

```text
KeywordSuggestion:  pending → approved | rejected
VideoAsset:         downloaded → in_pool | skipped
MergeJob:           queued → processing → done | failed
FinalVideo:         ready
PerformanceReport:  submitted → ingested
```

**Merge rules:**
- Random: 2 videos from merge pool, **same keyword**
- Manual: any 2 from merge pool

---

## 6. Success Metrics (v1)

| Metric | Target |
| --- | --- |
| Active time | < 15 min/day |
| Approve → first download | < 30 min (async OK) |
| Merge job success | > 95% |
| Agent accuracy | Improves over 4 weeks with M5 data |

---

## 7. Out of Scope (v1)

- TikTok upload (v2)
- Multi-user auth
- Cloud storage
- PyQt6 desktop UI (deprecated)
- PRD v0.1 Daily Digest export-URL flow

---

## 8. Related Docs

| Doc | Purpose |
| --- | --- |
| `docs/product/agent-learning-system.md` | Learning architecture (update in R1) |
| `docs/product/keyword-experiments.md` | Experiment workflow (port to web in R1) |
| `docs/ARCHITECTURE.md` | System architecture |
| `docs/decisions/0009-keyword-led-content-factory.md` | Product pivot ADR |
