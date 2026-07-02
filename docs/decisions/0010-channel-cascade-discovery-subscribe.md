# 0010 Channel Cascade Discovery Subscribe

Date: 2026-07-02

## Status

Accepted

## Context

R2 adds the first half of Module M2: approving a keyword should immediately
trigger channel discovery and internal subscribe behavior. This introduces
provider calls (YouTube API), asynchronous execution, and durable linkage
between keyword suggestions and channel entities.

Without explicit job and link tables, there is no reliable way to monitor
cascade progress, retry safely, or inspect which channels were discovered for a
specific keyword.

## Decision

Implement channel cascade with:

- `channel_keyword_links` table for suggestion-channel linkage and scoring
- `keyword_cascade_jobs` table for asynchronous job lifecycle
- FastAPI `BackgroundTasks` trigger from `bulk_approve`
- Worker-based orchestration (`videoscout/workers/keyword_cascade.py`) using
  SQLAlchemy sessions
- Discovery logic ported to `videoscout/core_engine/channel_discovery.py`
  consuming `get_youtube_service()` rather than legacy sqlite modules

R2 scope ends at discover + subscribe (internal `channels` upsert with
`scan_enabled=True`). Downloading is deferred to R3.

## Alternatives Considered

1. Synchronous discovery inside approve endpoint.
2. Reuse legacy `videoscout/services/channel_discovery.py` directly.
3. Store only derived channel state, no link/job records.

## Consequences

Positive:

- Approval remains responsive while cascade runs asynchronously.
- Operators can inspect per-job status and failure messages.
- Keyword-to-channel lineage is preserved for product insights.

Tradeoffs:

- Additional schema and API surface to maintain.
- Background task execution is process-local (no external queue yet).
- Retry/dedup behavior must be enforced in worker logic.

## Follow-Up

- R3 should consume subscribed channels for download/watcher pipeline.
- Introduce configurable top-N per keyword in settings API.
- Consider queue-backed workers for multi-process deployments.
