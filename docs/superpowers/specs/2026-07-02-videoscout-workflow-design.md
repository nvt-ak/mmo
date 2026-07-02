# VideoScout — Workflow & Product Redesign

**Date:** 2026-07-02  
**Status:** Approved (2026-07-02)  
**Scope:** Business workflow, modules, lifecycles, architecture, roadmap v1  
**Supersedes:** `docs/product/PRD.md` v0.1 (video-centric daily digest model)

---

## 1. Problem

PRD v0.1 describes a **video-centric** desktop tool (Daily Digest, export YouTube URLs).  
Implementation (US-002/003) built a **keyword-centric** web inbox.  
US-001 adds a **keyword experiment learning loop** on deprecated PyQt6/SQLite.

None of these match the operator's actual workflow:

> Approve keywords → auto discover channels & download → daily batch review → merge → final videos → (later) upload.

This spec defines the canonical product, modules, object lifecycles, architecture, and phased roadmap.

---

## 2. Business Context

| Item | Value |
| --- | --- |
| Market | TikTok Creator Rewards Beta (DE) |
| Model | Reup YouTube content to TikTok DE accounts |
| Bottleneck | Finding content ideas (keywords/channels) — not download/upload |
| Operator time target | < 5 minutes active time per day |
| Existing automation | Download, process, upload, account management — **outside v1 scope** |

---

## 3. North Star

> Operator approves agent-scored keywords → system auto-handles channel discovery, subscription, and download → operator curates a daily batch (Keep/Skip) → merges videos → **final video files ready for upload**.

**Primary value unit:** approved **keyword**, not individual YouTube video URL.

---

## 4. Decisions (locked in brainstorming)

| # | Topic | Decision |
| --- | --- | --- |
| 1 | Product model | Keyword-led content factory |
| 2 | Approve gate | **Keyword only** — approve triggers full auto cascade (channels, subscribe, download) |
| 3 | Pre-merge checkpoint | **Daily batch review** — operator reviews downloaded videos once per day |
| 4 | Batch actions | **Keep** (→ merge pool) \| **Skip** (excluded from merge) |
| 5 | Merge rules | **Random:** 2 videos from pool, **same keyword**. **Manual:** any 2 from pool, cross-keyword OK |
| 6 | Architecture | **Monolith in-repo** — download + merge built into VideoScout |
| 7 | Upload | **v1:** output `finals/` folder, handoff to existing upload tool. **v2:** upload module in-app |
| 8 | Roadmap shape | **Pipeline stages (Approach 2)** — complete modules in dependency order |

---

## 5. Canonical Workflow

```text
┌─ M1 KEYWORD INTELLIGENCE ─────────────────────────────────────┐
│ Scan (YouTube + TikTok search + knowledge base from past tests) │
│ Agent score + rationale (views, likes, comments, followers)     │
│ Inbox: approve | reject keyword          [ONLY HARD GATE]     │
└───────────────────────────┬───────────────────────────────────┘
                            │ approved
┌─ M2 CHANNEL DISCOVERY ────▼───────────────────────────────────┐
│ Auto: discover channels for keyword → subscribe                 │
└───────────────────────────┬───────────────────────────────────┘
┌─ M3 INGESTION ────────────▼───────────────────────────────────┐
│ Bulk download latest videos + monitor new uploads → queue       │
└───────────────────────────┬───────────────────────────────────┘
┌─ M3b BATCH REVIEW ────────▼───────────────────────────────────┐
│ Daily: Keep → merge_pool | Skip → excluded     [SOFT GATE]      │
└───────────────────────────┬───────────────────────────────────┘
┌─ M4 PRODUCTION ───────────▼───────────────────────────────────┐
│ Manual: pick any 2 from pool                                    │
│ Random: 2 from pool, same keyword                               │
│ → data/finals/                                                  │
└───────────────────────────┬───────────────────────────────────┘
┌─ M5 FEEDBACK (async) ─────▼───────────────────────────────────┐
│ Report TikTok performance per keyword → KB → improves M1        │
└─────────────────────────────────────────────────────────────────┘

v1 ends at finals/ → handoff upload (external)
v2 adds upload module
```

### Operator touchpoints (daily)

| Step | Operator action | Frequency |
| --- | --- | --- |
| Keyword inbox | Approve / reject | Daily, ~2–5 min |
| Batch review | Keep / Skip per video | Daily, ~5–10 min |
| Merge | Manual pair or random | Daily, ~2–5 min |
| Feedback | Report TikTok stats | Async, when results available |

---

## 6. Modules & Function List

### M1 — Keyword Intelligence

| Function | Description |
| --- | --- |
| Scan sources | YouTube channels/videos, TikTok search, operator KB |
| Extract keywords | LLM + heuristics from video content |
| Agent score | Multi-factor score + TikTok saturation + historical performance |
| Keyword inbox | List pending/approved/rejected keywords |
| Approve / reject | Hard gate; approve enqueues cascade |
| Learning insights | Patterns from rejections and performance reports |
| Weight suggestions | Human-approved scoring adjustments |

**Existing:** `core_engine/`, `api/suggestions`, `api/learning`, web `/today`, `/insights`  
**Gap:** Full TikTok stats; port US-001 experiments to PostgreSQL + web

### M2 — Channel Discovery

| Function | Description |
| --- | --- |
| Discover channels | Given approved keyword, find matching YouTube channels |
| Auto-subscribe | Subscribe or internal track after keyword approve |
| Link keyword ↔ channel | `channel_keyword_links` for traceability |
| Channel status | Read-only view: last scan, download count |

**Existing:** `api/sources` (manual CRUD only)  
**Gap:** Discovery engine; auto-subscribe; cascade trigger on approve

### M3 — Ingestion

| Function | Description |
| --- | --- |
| Bulk download | Latest N videos per subscribed channel |
| New-video watcher | Poll channels; enqueue new downloads |
| Storage management | `data/downloads/{channel_id}/{video_id}.mp4` |
| Download jobs | Progress, retry, error tracking |

**Existing:** Scan job skeleton in `api/scan`  
**Gap:** yt-dlp integration; watcher; `video_assets` table

### M3b — Batch Review

| Function | Description |
| --- | --- |
| Daily batch view | Grid of videos downloaded since last review |
| Keep | Mark `in_pool` — eligible for merge |
| Skip | Mark `skipped` — excluded from merge |
| Thumbnail + metadata | Title, channel, views, linked keyword |

**Existing:** None  
**Gap:** New web route `/batch`; API for review actions

### M4 — Production (Merge)

| Function | Description |
| --- | --- |
| Merge pool view | Videos with status `in_pool` |
| Manual merge | Operator selects any 2 videos |
| Random merge | System picks 2 from pool, same keyword |
| ffmpeg merge | Concat/merge → output file |
| Finals registry | `data/finals/` + DB record |

**Existing:** None  
**Gap:** `services/merge.py`, `/merge` UI, `merge_jobs` table

### M5 — Feedback Loop

| Function | Description |
| --- | --- |
| Performance report | TikTok views, likes, comments, followers per keyword |
| KB ingestion | Store reports; feed agent scoring |
| Pattern extraction | From reports + rejections (extends US-001) |
| Accuracy tracking | Agent-suggested vs manual keywords |

**Existing:** `learning_events`, US-001 logic (SQLite/desktop)  
**Gap:** Web report form; PostgreSQL port; link report ↔ keyword

---

## 7. Object Lifecycles

```text
KeywordSuggestion:  pending → approved | rejected
                              ↓ (approved)
ChannelSubscription: active (linked to keyword)
VideoAsset:         downloaded → in_pool | skipped
MergeJob:           queued → processing → done | failed
FinalVideo:         ready → (handoff to upload tool)
PerformanceReport:  submitted → ingested → KB
```

### Merge rules (reference)

- **Random:** sample 2 from `in_pool` WHERE same `keyword_id`
- **Manual:** any 2 from `in_pool`, no keyword constraint

---

## 8. Architecture

### Stack (unchanged)

| Layer | Tech |
| --- | --- |
| Frontend | Next.js (App Router) |
| Backend | FastAPI (`videoscout/api_main.py`) |
| Database | PostgreSQL + Alembic |
| Jobs | APScheduler + DB-backed job tables |
| Media | yt-dlp (download), ffmpeg (merge) |
| Storage | Local filesystem under `data/` |

### System diagram

```text
web/ ──REST──► videoscout/api/
                  ├── core_engine/   (agent, scoring, discovery)
                  ├── services/      (youtube, tiktok, download, merge)
                  ├── workers/       (cascade, download, merge jobs) [NEW]
                  └── db/            (SQLAlchemy)
                        │
            PostgreSQL ◄┘     data/downloads/ + data/finals/
```

### Component rules

| Component | May | Must not |
| --- | --- | --- |
| `api/*` | Parse HTTP, enqueue jobs | Call ffmpeg/yt-dlp directly |
| `core_engine/` | Agent logic, rules | File I/O |
| `services/download.py` | yt-dlp, paths | Business rules |
| `services/merge.py` | ffmpeg | DB writes (workers own that) |
| `workers/` | Orchestrate, retry, progress | HTTP logic |

### New / extended tables

| Table | Phase |
| --- | --- |
| `suggestions` (existing) | Keyword inbox |
| `channel_keyword_links` | R2 |
| `video_assets` | R3 |
| `download_jobs` | R3 |
| `merge_jobs` | R5 |
| `final_videos` | R5 |
| `performance_reports` | R6 |

### Keyword approve cascade

```text
POST /api/v1/suggestions/{id}/approve
  → enqueue KeywordCascadeJob
      1. discover_channels(keyword)
      2. subscribe each channel
      3. enqueue BulkDownloadJob
      4. register ChannelWatcher
  → return 202 + job_id
```

### Web routes (target)

| Route | Module | Phase |
| --- | --- | --- |
| `/today` | M1 inbox | exists |
| `/batch` | M3b review | R4 |
| `/merge` | M4 production | R5 |
| `/sources` | M2 status (read-heavy) | R2+ |
| `/settings` | Config, paths | exists |
| `/insights` | M5 + M1 learning | R6 extends |

### Error handling

| Failure | Behavior |
| --- | --- |
| LLM unavailable | Empty suggestion queue; UI banner |
| YouTube quota exceeded | Pause scans; notify operator |
| Download failure | Retry 3×; skip video; log error |
| Merge failure | Job `failed`; sources preserved; operator retry |
| Disk full | Block downloads; alert |

---

## 9. Roadmap (Pipeline Stages)

| Phase | Module | Deliverable | Est. |
| --- | --- | --- | --- |
| **R0** | Foundation | This spec + PRD v0.2 + epic/story backlog + deprecate PRD v0.1 | 2–3 days |
| **R1** | M1 complete | Inbox + agent score + TikTok insight + US-001 on PostgreSQL/web | 2 weeks |
| **R2** | M2 | Approve keyword → auto discover + subscribe | 1.5 weeks |
| **R3** | M3 | Bulk download + new-video watcher + storage | 2 weeks |
| **R4** | M3b | `/batch` Keep/Skip UI | 1 week |
| **R5** | M4 | Manual + random merge → `finals/` | 1.5 weeks |
| **R6** | M5 | TikTok report → KB closes loop on M1 | 1 week |
| **R7** | v2 | Upload module | TBD |

**v1 usable (keyword → final video): ~10 weeks** (1 dev, part-time)

### Relationship to existing stories

| Existing | Maps to |
| --- | --- |
| US-001 | M5 — port to web/PostgreSQL in R1/R6 |
| US-002 | M1 backend foundation — extend, not replace |
| US-003 | M1 web foundation — add routes in R4/R5 |
| US-004 | E2E for full workflow — after R5 |
| US-005 | M1 agent evaluation — fold into R1 |

### Proposed new epics (R0 backlog)

| Epic | Stories (draft) |
| --- | --- |
| E04 Keyword Intelligence v2 | US-010 port experiments, US-011 TikTok stats, US-012 KB scoring |
| E05 Channel Cascade | US-020 discover-by-keyword, US-021 auto-subscribe, US-022 cascade job |
| E06 Ingestion | US-030 yt-dlp download, US-031 channel watcher |
| E07 Batch & Merge | US-040 batch review UI, US-041 merge engine |
| E08 Feedback | US-050 performance report web |

---

## 10. Success Metrics (v1)

| Metric | Target |
| --- | --- |
| Operator active time | < 15 min/day (approve + batch + merge) |
| Keyword approve → first download | < 30 min (async acceptable) |
| Batch review throughput | 50 videos reviewed in < 10 min |
| Merge success rate | > 95% jobs complete without error |
| Agent keyword accuracy | Improves over 4 weeks with M5 reports (qualitative + accuracy stat) |
| False cascade rate | < 10% keywords revoked within 24h (if undo added) |

---

## 11. Out of Scope (v1)

| Item | Reason |
| --- | --- |
| TikTok upload | v2; existing upload code |
| Account management | External system |
| Revenue / analytics dashboard | External system |
| Multi-user / auth | Single operator v1 |
| Cloud storage / CDN | Local filesystem v1 |
| PyQt6 desktop UI | Deprecated (ADR 0008) |
| PRD v0.1 video Daily Digest export | Superseded by this workflow |
| License / SaaS packaging | Post-v1 |

---

## 12. Documentation Actions (R0)

| Action | File |
| --- | --- |
| Mark superseded | `docs/product/PRD.md` — add banner pointing to this spec |
| Create PRD v0.2 | `docs/product/PRD.md` rewrite or `docs/product/workflows.md` |
| Update architecture | `docs/ARCHITECTURE.md` — add M1–M5, workers, storage |
| Update backlog | `docs/stories/backlog.md` — E04–E08 |
| ADR (optional) | `0009-keyword-led-content-factory` |

---

## 13. Open Questions (post-v1)

- **Undo keyword approve:** revoke + unsubscribe + purge downloads?
- **Skip disposition:** delete file or archive?
- **Download filters:** apply PRD view range (150–200K) at download time or only at agent score time?
- **Subscribe semantics:** literal YouTube account subscribe vs internal watchlist only?
- **New video default:** auto-download all new or queue for next batch review only?

These do not block R0/R1; resolve before R2/R3 implementation.

---

## 14. Next Steps

1. User reviews this spec
2. R0: update product docs + backlog + ADR
3. Invoke **writing-plans** skill for R1 implementation plan
4. Each phase: feature intake → story packet → harness matrix (per `AGENTS.md`)
