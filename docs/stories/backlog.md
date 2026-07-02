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
| E09 Dual-Track Discovery | M1 R7 — trend discovery, nurture/beta split | **R7c done** |

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
| R7d | Trend sources expansion | TBD |
| R8 | v2 upload | TBD |

## Notes

- US-005 (evaluate_keyword LLM) folded into US-011
- US-004 deferred until R5 (full workflow E2E)
- US-054–056: beta scoring pipeline per ADR 0012; nurture stays heuristic
