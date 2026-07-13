# Story Backlog

Active stories for VideoScout. Create story packets before implementation
(see `AGENTS.md` workflow rules).

**Product contract:** `docs/product/workflows.md`  
**Roadmap spec:** `docs/superpowers/specs/2026-07-02-videoscout-workflow-design.md`

## Epics

| Epic | Description | Status |
| --- | --- | --- |
| E01 Keyword Learning | Experiment feedback + pattern extraction | US-001 done (desktop) |
| E02 Web Platform | API backend + browser UI | US-002, US-003 done |
| E03 Quality | E2E + production hardening | planned |
| E04 Keyword Intelligence v2 | M1 complete — agent + KB + experiments on web | **R1 done** |
| E05 Channel Cascade | M2 — discover + subscribe on keyword approve | implemented (R2 partial) |
| E06 Ingestion | M3 — download + channel watcher | implemented (R3) |
| E07 Batch & Merge | M3b + M4 — review UI + ffmpeg merge | implemented (R4–R5) |
| E08 Feedback | M5 — TikTok performance reports on web | implemented (R6) |
| E09 Dual-Track Discovery | M1 R7 — trend discovery, nurture/beta split | **R7 evidence pipeline (Sprint 1–4) done**; R7d/R8 next |

## Story Index

| ID | Title | Epic | Lane | Status |
| --- | --- | --- | --- | --- |
| US-001 | Keyword Experiment Feedback Loop | E01 | normal | implemented (desktop) |
| US-002 | FastAPI Backend & PostgreSQL | E02 | high-risk | implemented |
| US-003 | Web Frontend (Next.js Inbox) | E02 | normal | implemented |
| US-004 | Browser E2E Tests (Playwright) | E03 | normal | planned |
| US-010 | Port keyword experiments to PostgreSQL + API | E04 | normal | implemented |
| US-011 | TikTok search stats in agent scoring | E04 | normal | implemented |
| US-012 | Performance report → knowledge base | E04 | normal | implemented |
| US-013 | Web experiments & report UI | E04 | normal | implemented |
| US-020 | Discover channels by keyword | E05 | high-risk | implemented |
| US-021 | Keyword approve cascade job | E05 | high-risk | implemented |
| US-030 | yt-dlp bulk download service | E06 | high-risk | implemented |
| US-031 | Channel new-video watcher | E06 | normal | implemented |
| US-040 | Daily batch review UI (`/batch`) | E07 | normal | implemented |
| US-041 | Merge engine + `/merge` UI | E07 | normal | implemented |
| US-050 | TikTok performance report form | E08 | normal | implemented |
| US-051 | Dual-track trend discovery foundation | E09 | normal | implemented |
| US-052 | TikTok profiles + typed media pools | E09 | normal | implemented |
| US-053 | TikTok msToken search for web API | E09 | normal | implemented |
| US-054 | Keyword context builder (beta KG v1) | E09 | normal | implemented |
| US-055 | Beta LLM keyword scoring | E09 | normal | implemented |
| US-056 | Beta learning weight approval | E09 | normal | implemented |
| US-057 | Batch beta scoring pipeline | E09 | normal | implemented |
| US-058 | Discovery SSE + reload persistence | E09 | normal | implemented |
| US-059 | Discovery progress bar | E09 | tiny | implemented |
| US-060 | TikTok msToken pool + proxy rotation | E09 | normal | implemented |
| US-061 | Runtime scoring rubric + batch spread | E09 | normal | implemented |
| US-062 | TrendEvidence schema + velocity percentile (Sprint 1) | E09 | normal | implemented |
| US-063 | Top-N evidence enrichment (Sprint 2) | E09 | normal | implemented |
| US-064 | Dual-source discovery + ranker (Sprint 3) | E09 | normal | implemented |
| US-065 | Search-sample evidence + validation pass (Sprint 4, ADR 0014) | E09 | normal | implemented |
| US-068 | Discovery job cancel + force restart *(renumbered from US-059)* | E09 | tiny | implemented |
| US-069 | Keyword scoring diversity + platform insights *(renumbered from US-060)* | E09 | normal | implemented |
| US-066 | Trend Cluster — duplicate keyword grouping (Phase 2) | E09 | normal | implemented |

## Roadmap Phases

| Phase | Deliverable | Stories |
| --- | --- | --- |
| R0 | Docs + ADR + backlog | — |
| R1 | M1 complete | US-010–013 |
| R2 | M2 cascade | US-020–021 |
| R3 | M3 ingestion | US-030–031 |
| R4 | M3b batch | US-040 |
| R5 | M4 merge | US-041 |
| R6 | M5 feedback | US-050 |
| R7a | M1 dual-track foundation | US-051 |
| R7b | Profiles + typed pools | US-052 |
| R7b+ | TikTok gate (msToken) | US-053 |
| R7c | Beta LLM scoring + learning approval | US-054, US-055, US-056, US-057 |
| R7c+ | Discovery UX (SSE, cancel/force, progress, insights, msToken pool, rubric spread) | US-058, US-059, US-060, US-061, US-068, US-069 |
| R7e S1 | TrendEvidence v1 + velocity percentile (ADR 0013) | US-062 |
| R7e S2 | Top-N evidence enrichment (ADR 0013) | US-063 |
| R7e S3 | Dual-source discovery + ranker (ADR 0013) | US-064 |
| R7e S4 | Search-sample evidence + validation pass (ADR 0014) | US-065 |
| R7f | Trend Cluster + suggested aliases (ADR 0014 Phase 2) | US-066 (planned, story packet drafted 2026-07-13) |
| R7g | Opportunity Assessment: Trend/Generalizability/Durability/Dependency Risk (ADR 0014 Phase 3) | US-067 (draft, per ADR 0014) |
| R7d | Trend sources expansion (Google Trends, Reddit, RSS via TrendEvidence `raw.*` + provenance) | TBD |
| R8 | v2 upload | TBD |

## Notes

- US-005 (evaluate_keyword LLM) folded into US-011
- US-004 deferred until R5 (full workflow E2E)
- US-054–056: beta scoring pipeline per ADR 0012; nurture stays heuristic
- **2026-07-13 doc sync:** US-062–065 (TrendEvidence pipeline, ADR 0013/0014)
  existed as story packets with working code but were missing from this
  backlog and unregistered in `harness.db` (see `AGENTS.md` → Harness CLI
  commands, run locally). Also found two ID collisions — two files each
  claimed `US-059` and `US-060`. The discovery-progress-bar and
  tiktok-token-proxy-rotation stories keep their original IDs (already
  referenced elsewhere); `discovery-job-cancel-force` → **US-068** and
  `keyword-scoring-insights` → **US-069** (US-066/US-067 stay reserved for
  ADR 0014 Phase 2/3 per that ADR's own roadmap table).
