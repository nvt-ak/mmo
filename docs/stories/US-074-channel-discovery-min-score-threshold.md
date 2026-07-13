# US-074 Channel Discovery Minimum Score Threshold

## Status

implemented

## Lane

high-risk

**Risk flags:**
- External systems — uses YouTube Data API search results.
- Existing behavior — changes which channels get subscribed on keyword approve.
- Data model — adds `'completed_no_source'` to `keyword_cascade_jobs.status` CHECK constraint (Alembic migration 0017).
- Public contracts — additive `CascadeJobResponse.status` value.
- Weak proof — new test scenarios required for threshold and no-source path.

Scope narrowed to: filter by existing `discovery_score`, add explicit no-source terminal status, and update the CHECK constraint. No scoring formula or YouTube API call changes.

## Product Contract

When a keyword is approved, VideoScout discovers YouTube channels matching the keyword and subscribes the top candidates for bulk download. Currently, `discovery_score` is computed and sorted but never thresholded, so low-quality or irrelevant channels can still be subscribed as long as they appear in the top 5. This story adds a minimum `discovery_score` threshold before a channel is considered qualified for subscription, and surfaces the case where no channels qualify so operators can see that a keyword approved but produced no usable source channels.

Relevant product contract: `docs/product/workflows.md` (M2 Channel Discovery, M3 Ingestion).

## Relevant Product Docs

- `docs/product/workflows.md`
- `docs/stories/US-020-discover-channels-by-keyword.md`
- `docs/stories/US-021-keyword-approve-cascade.md`

## Acceptance Criteria

- [x] `channel_discovery.py` defines a minimum `MIN_DISCOVERY_SCORE` (default 40.0) for a channel to be considered qualified for subscription.
- [x] `keyword_cascade.py` filters discovered channels by `discovery_score >= MIN_DISCOVERY_SCORE` and subscribes `qualified[:5]` instead of `candidates[:5]`.
- [x] `channels_discovered` remains the raw discovered count; `channels_subscribed` is the count of qualified channels actually subscribed.
- [x] If zero channels qualify, the cascade job status is set to `"completed_no_source"` instead of `"completed"`, with `channels_subscribed=0` and `channels_discovered` set to the raw count.
- [x] Alembic migration `0017` updates the `keyword_cascade_jobs.status` CHECK constraint to include `'completed_no_source'`; model updated in `videoscout/db/models.py`.
- [x] The existing `KeywordCascadeJobModel` / `CascadeJobResponse` contract remains backward-compatible (new status value is additive).
- [x] Integration tests cover: (a) channel below threshold is filtered, (b) zero qualified channels produces `completed_no_source`.

## Design Notes

- **Commands:** None.
- **Queries:** None new; reuse existing `KeywordCascadeJobModel` query in `api/cascade.py`.
- **API:** Additive enum value `"completed_no_source"` on `KeywordCascadeJobModel.status`. `CascadeJobResponse` already exposes `status`, `channels_discovered`, `channels_subscribed`, so no schema change required.
- **Tables:**
  - `keyword_cascade_jobs.status` CHECK constraint expanded via Alembic migration `0017_cascade_no_source_status.py`.
  - `videoscout/db/models.py` updated to match the new constraint.
- **Domain rules:**
  - Threshold is a constant in `channel_discovery.py` near `_score_channel`.
  - Score threshold applies at channel-discovery time, not at keyword-scoring time, so it does not affect keyword score/inbox ranking.
  - If no channels qualify, no `ChannelKeywordLinkModel` rows are created and no `DownloadJobModel` is queued (or it is queued with zero channels and completes immediately).
- **UI surfaces:** Inbox dashboard already shows cascade job status; `completed_no_source` will render as a distinct status once backend emits it.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-074 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Not required separately; logic covered by integration tests. |
| Integration | `videoscout/tests_api/test_channel_cascade.py` passes, including new tests for threshold filtering and `completed_no_source`. Full suite `videoscout/tests_api/` passes. |
| E2E | Not required for this change. |
| Platform | Not required. |
| Release | None. |

## Harness Delta

- New story added to `docs/stories/backlog.md` under Epic E05 (Channel Cascade).
- If threshold tuning reveals friction, consider exposing `DISCOVERY_SCORE_THRESHOLD` via Settings model in a future story.

## Evidence

- All 262 integration tests pass:
  ```bash
  python -m pytest videoscout/tests_api/ -v
  # 262 passed, 13 warnings in 61.27s
  ```
- New test coverage in `videoscout/tests_api/test_channel_cascade.py`:
  - `test_bulk_approve_filters_channels_below_min_score` — verifies low-score channel is not subscribed and job status becomes `completed_no_source`.
  - Existing `test_bulk_approve_triggers_cascade_and_links_channels` still passes, confirming qualified channels are unaffected.
- Migration `alembic/versions/0017_cascade_no_source_status.py` adds `'completed_no_source'` to the status CHECK constraint.
