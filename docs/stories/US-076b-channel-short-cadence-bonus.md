# US-076b Channel Short Cadence Bonus (M2)

## Status

implemented

## Lane

normal

**Risk flags:**
- Existing behavior — enriches M2 subscribe signals; must not change US-076 pass/fail branches.
- Multi-domain — `channel_discovery.py`, `youtube.py`, cascade tests.
- Weak proof without fixture timestamps — golden cases need `published_at` + `duration_sec`.

**Scope:** Add **short-upload cadence** as a **bonus signal** (not a hard subscribe gate) on the M2 channel cascade path, building on US-076. Does **not** add channel cadence to M1 keyword ranker, Tier-1 enrichment, or `supply_pressure`. Does **not** implement channel-scoped search or `relevanceLanguage` fixes (defer US-076c).

## Product Contract

After US-076, cascade subscribes when `evaluate_channel_relevance()` passes via metadata, multi-video, or catalog-coherence branches. Empirical review (2026-07-13) identified a separate M2 question:

> *Is this channel worth keeping as a continuous source?*

Short cadence (≥1 short/day in a recent window) indicates a channel that can supply content repeatedly — aligned with `workflows.md` operational goal (low daily operator time, durable sources). This is **not** the same as M1's *"is this trend worth following?"* question.

**Layer placement (verified against code):**

| Layer | Cadence signal? | Why |
| --- | --- | --- |
| M1 Ranker / Tier-1 | **No** | `load_tier1_channel()` only works when channel already in DB; new keywords lack per-channel cadence without extra API (ADR 0013 rejects enrich-all). ADR 0013 Tier-1 "upload frequency" not implemented on `ChannelModel` — see ADR 0015. |
| M1 `uploads_per_day` (search sample) | **Different metric** | `compute_distribution_stats()` in `search_sample.py` — aggregate across many creators in a keyword search sample (ADR 0014 Tier-2), not one channel. |
| M2 `evaluate_channel_relevance` | **Yes (this story)** | Channel already chosen; `get_recent_videos` list is per-channel; cadence answers source durability. |

**Non-goals:**

- Hard reject when cadence < threshold if US-076 already passed (especially `metadata_pass` — Cargo official channel posts infrequently).
- Cadence-only subscribe without US-076 relevance pass.
- M1 keyword scoring / Ranker changes.
- `_score_channel()` lifetime `video_count` proxy fix (optional follow-up US-076c — adds quota at discover time).
- US-067 / R7g Opportunity Assessment (aggregate durability — different layer).

Relevant product contract: `docs/product/workflows.md` (M2 Channel Discovery, M3 Ingestion).

## Relevant Product Docs

- `docs/product/workflows.md`
- `docs/stories/US-076-channel-relevance-v2-metadata-catalog.md`
- `docs/decisions/0015-tier1-upload-frequency-clarification.md`

## Acceptance Criteria

### Data shape (`get_recent_videos`)

- [x] `get_recent_videos` return dicts include `published_at` (full ISO from YouTube `publishedAt`), retaining existing `upload_date` (`YYYY-MM-DD`) for backward compatibility.
- [x] No additional YouTube API quota — same `playlistItems` + `videos` calls as today.

### Cadence helper

- [x] Add `compute_short_upload_cadence(videos, *, short_max_duration_sec=180, timestamp_key="published_at") -> dict` in `channel_discovery.py` (or shared util imported by M2 only).
- [x] Reuse span formula from `search_sample.compute_distribution_stats` (`newest`, `oldest`, `span_days`, `count / span_days`) on a **per-channel** video list filtered to shorts (`duration_sec <= short_max_duration_sec`).
- [x] Return at least: `shorts_count`, `shorts_per_day`, `window_span_days`, `cadence_confidence` (`high` if `shorts_count >= 3`, else `low`).

### Bonus integration (`evaluate_channel_relevance`)

- [x] Extend `signals` with: `shorts_per_day`, `cadence_bonus`, `cadence_skipped` (bool).
- [x] **Do not** add a `rejected` branch solely for low cadence — US-076 `pass`/`reason`/`decision_branch` unchanged for subscribe gate.
- [x] When `decision_branch == "metadata_pass"`: set `cadence_skipped=True`, `cadence_bonus=0` (log only; no penalty).
- [x] Otherwise: compute `cadence_bonus` in `[0, CADENCE_BONUS_MAX]` when `shorts_per_day >= MIN_SHORTS_PER_DAY` **and** `avg_views` meets minimum (cross-check against reup farms — use `avg_views` from caller or median of recent short views in sample).
- [x] Expose combined `source_quality_score = base_score + cadence_bonus` in `signals` for logging/tie-break; cascade subscribe still uses `pass` from US-076 tree only.

### Cascade wiring

- [x] `keyword_cascade.py` passes `avg_views` from `ChannelCandidate` into `evaluate_channel_relevance` (or cadence helper).
- [x] Debug log includes `shorts_per_day`, `cadence_bonus`, `cadence_skipped`.

### Regression

- [x] US-076 golden fixture (`jetzt_kommt_rolf_channels.json`): all 5 `expect_subscribe` unchanged.
- [x] `test_match_rate_alone_cannot_separate_hans_and_mikado` still passes.
- [x] `test_channel_cascade.py` US-074/075/076 integration tests still pass.
- [x] Unit tests for `compute_short_upload_cadence`: 0 shorts → 0/day; 7 shorts over 7 days → ~1/day; same-calendar-day shorts counted at day resolution.

### Preconditions (validation runbook)

- [ ] Story validation section documents: sync repo (`git fetch`) before manual empirical review; verify symbols on current HEAD.

## Design Notes

- **Commands:** None.
- **Queries:** Reuse `get_recent_videos(days=30, max_results=10)` for v1; optional increase to `max_results=20` only if tests show insufficient shorts for cadence confidence (no discover-time quota change).
- **API:** No schema migration.
- **Tables:** None (persisting cadence on `ChannelModel` deferred — would enable future Tier-1 after subscribe, not M1 rank).
- **Constants (tune in `channel_discovery.py`):**
  - `SHORT_MAX_DURATION_SEC = 180` (align PRD Short format)
  - `MIN_SHORTS_PER_DAY = 1.0`
  - `CADENCE_BONUS_MAX = 5.0` (tie-break magnitude, not gate)
  - `CADENCE_MIN_AVG_VIEWS = 50_000` (or reuse sweet-spot from `_score_channel` — tune with fixtures)
- **UI surfaces:** None; optional future cascade debug panel.

### Deferred (US-076c)

- Channel-scoped `search.list(q=keyword, channelId=...)`.
- Adaptive `days` / `max_results` by `video_count` and upload cadence at discover time.
- Replace `_score_channel()` lifetime `video_count` upload proxy with real cadence (quota cost at discover).
- `relevanceLanguage` fix for DE keywords in `discover_channels` / `get_emergence_videos`.
- Persist `shorts_per_day` on `ChannelModel` after scan for Tier-1 cache on **subsequent** enrichment passes.

## Validation

When updating durable proof status:
`scripts/bin/harness-cli story update --id US-076b --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | `test_channel_cadence.py` — helper + bonus signals; US-076 golden unchanged |
| Integration | `test_channel_cascade.py` — existing cascade tests pass |
| E2E | Not required |
| Platform | Not required |

```bash
python -m pytest videoscout/tests_api/test_channel_cadence.py \
  videoscout/tests_api/test_channel_relevance_v2.py \
  videoscout/tests_api/test_channel_cascade.py -v
```

## Harness Delta

- Story added to `docs/stories/backlog.md` under Epic E05 (Channel Cascade).
- Builds on US-076; splits deferred scope from US-076 "Deferred (US-076b)" section.
- ADR 0015 clarifies ADR 0013 Tier-1 upload-frequency doc drift.

## Evidence

```bash
python -m pytest videoscout/tests_api/test_channel_cadence.py \
  videoscout/tests_api/test_channel_relevance_v2.py \
  videoscout/tests_api/test_channel_cascade.py -v
# 26 passed, 10 warnings in 1.66s

python -m pytest videoscout/tests_api/ --tb=short -q
# 285 passed, 13 warnings in 198.52s
```
