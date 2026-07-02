# R2 — Channel Cascade (M2) Implementation Plan

> **For agentic workers:** Subagent-driven execution. Harness workflow required.

**Goal:** On keyword approve, auto-discover YouTube channels and subscribe (internal watchlist) linked to keyword.

**Architecture:** Port `services/channel_discovery.py` logic to `core_engine/channel_discovery.py` using `services/youtube.py`. Add `channel_keyword_links` table. `KeywordCascadeWorker` runs on approve via FastAPI BackgroundTasks. **No download in R2** (R3).

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, YouTube Data API, pytest

## Global Constraints

- Stories: US-020, US-021 (E05)
- Product: `docs/product/workflows.md` step 2
- Subscribe = upsert `channels` + `scan_enabled=True` + link row (not browser YouTube subscribe)
- Top N channels per keyword: default 5, configurable via settings later
- Mock YouTube in tests

---

### Task 1: Stories + harness (US-020, US-021)

Create story md files, register harness, intake.

### Task 2: Schema `channel_keyword_links` + `KeywordCascadeJobModel`

Alembic 0004, models, schemas.

### Task 3: `core_engine/channel_discovery.py`

`discover_channels(keyword, max_results=10) -> list[ChannelCandidate]` using YouTube API.

### Task 4: `workers/keyword_cascade.py`

`run_keyword_cascade(suggestion_id)` — discover, upsert channels, create links, update job status.

### Task 5: Wire `bulk_approve` + single approve path

After approve, enqueue cascade per keyword. Return cascade job ids in response extension or separate poll endpoint `GET /api/v1/cascade/{job_id}`.

### Task 6: API `GET /api/v1/suggestions/{id}/channels`

List channels linked to approved keyword.

### Task 7: Tests + docs + harness proof

`test_channel_cascade.py`, update workflows.md M2 status, backlog.
