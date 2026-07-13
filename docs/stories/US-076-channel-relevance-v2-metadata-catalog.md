# US-076 Channel Relevance v2 — Metadata + Catalog Coherence

## Status

implemented

## Lane

normal

**Risk flags:**
- Existing behavior — changes which channels get subscribed on keyword approve (post US-075).
- Multi-domain — `channel_discovery.py`, `keyword_cascade.py`, cascade integration tests.
- Weak proof without golden fixture — requires frozen regression cases from empirical session.

**Scope:** Replace US-075 single-video `max(token_overlap)` gate with a **decision tree** that uses channel metadata (name + description already fetched by `discover_channels`) and **catalog coherence** (pattern among non-matching recent videos). Does **not** change discovery inbox (`trend_discovery`) or `discover_channels` ranking.

## Product Contract

US-075 added a content relevance gate on keyword approve cascade: fetch 10 recent videos, subscribe if `compute_channel_keyword_relevance() >= 0.5`. Empirical testing on keyword **`jetzt kommt rolf`** (DE TikTok trend, 2026-07) exposed two failure modes on real YouTube channels:

| Channel | US-075 result | Ground truth |
| --- | --- | --- |
| Cargo - Topic (official Rolf Zuckowski) | **Filtered** (score 0.00) | Should subscribe — official artist channel |
| Rolfs Vater | Filtered (0.33) | Correct reject |
| SimonsagtVEVO | Filtered (0.33) | Correct reject |
| Hans Schmitz (Der Retter religious films) | **Subscribed** (1.00 token overlap) | Should reject — one video uses Rolf song as B-roll |
| Mikado singt (children's cover) | Subscribed (1.00) | Correct subscribe |

**Root causes (verified on production logic):**

1. **Single-video OR** — one video with 100% token overlap (`jetzt`, `kommt`, `rolf` scattered in a long title) is enough to pass; Hans Schmitz case is **not** contiguous phrase match.
2. **Metadata blind spot** — `ChannelCandidate.description` is fetched but **not passed** to relevance scoring; official channels can score 0.00 when recent uploads omit trend tokens.
3. **Match-rate / consensus alone cannot fix Hans vs Mikado** — both have `match_count=1`, `match_rate=0.1` (1/10 videos); any threshold ≤10% keeps Hans; >10% drops Mikado (positive control).

**Non-goals for this story:**
- `match_rate` threshold as a standalone gate (explicit anti-regression test required).
- `final_relevance = max(video, metadata, search)` — `max()` still passes Hans when video branch scores 1.0.
- Channel-scoped YouTube search (defer to US-076b if Cargo still fails after metadata pass).
- Fixing `relevanceLanguage="en"` in `discover_channels` / `get_emergence_videos` (separate story).

Relevant product contract: `docs/product/workflows.md` (M2 Channel Discovery, M3 Ingestion).

## Relevant Product Docs

- `docs/product/workflows.md`
- `docs/stories/US-074-channel-discovery-min-score-threshold.md`
- `docs/stories/US-075-channel-content-relevance-gate.md`

## Acceptance Criteria

### Scoring API

- [x] Replace or wrap `compute_channel_keyword_relevance(keyword, videos)` with `evaluate_channel_relevance(keyword, *, channel_name, channel_description, videos) -> (pass: bool, score: float, reason: str, signals: dict)`.
- [x] Return `signals` includes at least: `video_best`, `match_count`, `match_rate`, `metadata_score`, `catalog_dominant_pattern`, `decision_branch`.
- [x] `reason` uses explicit branch labels: `metadata_pass` | `multi_video` | `catalog_coherent_single` | `catalog_outlier_single` | `rejected`.

### Decision tree (normative)

1. **`metadata_pass`** — keyword distinctive tokens overlap channel `name` + `description` above `METADATA_PASS_THRESHOLD` → **PASS** (fixes Cargo FN even when `video_best=0`).
2. **`multi_video`** — `match_count >= 2` and per-video overlap ≥ `MIN_PER_VIDEO_OVERLAP` → **PASS**.
3. **`single_match`** — when `match_count == 1`:
   - **`catalog_coherent_single`** — the matching video aligns with dominant title pattern among recent catalog → **PASS** (Mikado).
   - **`catalog_outlier_single`** — matching video is outlier vs dominant pattern (e.g. 9/10 titles share `Film Der Retter`, match is the exception) → **FAIL** (Hans).
   - If metadata supports keyword and does not contradict dominant pattern → **PASS**.
   - Else → **FAIL**.
4. Otherwise → **FAIL**.

**Catalog coherence (minimum v1):** Among videos with per-video overlap `< MIN_PER_VIDEO_OVERLAP`, extract the most frequent shared token bigram (or trigram) across titles; matching video is an outlier if it does not contain that dominant pattern. Implementation must be deterministic and unit-tested.

**Explicit non-goal test:** `match_rate` alone must not be the subscribe gate — fixture proves Hans and Mikado share `match_rate=0.1` but opposite `expect_subscribe`.

### Cascade wiring

- [x] `keyword_cascade.py` passes `candidate.name`, `candidate.description`, and `recent_videos` into `evaluate_channel_relevance`.
- [x] Subscribe when `pass is True` (threshold behavior subsumed by evaluator).
- [x] Existing statuses `completed_no_relevant_source` / `completed_no_source` unchanged.

### Golden fixture regression

- [x] Frozen fixture: `videoscout/tests_api/fixtures/jetzt_kommt_rolf_channels.json` (no live YouTube in tests).
- [x] Unit tests: all 5 cases assert `expect_subscribe` and document `match_rate` where applicable.
- [x] Anti-trap test: `test_match_rate_alone_cannot_separate_hans_and_mikado` — same `match_rate`, opposite outcomes.
- [x] US-075 English regression: `test_bulk_approve_triggers_cascade_and_links_channels` and `test_bulk_approve_filters_channels_with_irrelevant_content` still pass.

### Fixture expectations (empirical baseline)

| Channel | match_count | match_rate | expect_subscribe | failure_mode / note |
| --- | --- | --- | --- | --- |
| Cargo - Topic | 0 | 0.0 | **true** | `metadata_pass` (official Rolf Zuckowski) |
| Rolfs Vater | 1 | 0.1 | false | low overlap / wrong channel |
| SimonsagtVEVO | 1 | 0.1 | false | low overlap / wrong artist |
| Hans Schmitz | 1 | 0.1 | **false** | `catalog_outlier_single` — 100% token overlap on 1 video |
| Mikado singt | 1 | 0.1 | **true** | `catalog_coherent_single` — same match_rate as Hans |

## Design Notes

- **Commands:** None.
- **Queries:** Reuse `get_recent_videos(days=30, max_results=10)` — no new API calls for v1.
- **API:** No schema migration; logging may include richer `rel_reason` in cascade debug logs.
- **Tables:** None.
- **Constants (tune in `channel_discovery.py`):**
  - `METADATA_PASS_THRESHOLD` (suggested start: 0.5 on distinctive keyword tokens)
  - `MIN_PER_VIDEO_OVERLAP` (keep aligned with US-075: 0.5 on `len(kw_tokens)` basis)
  - `CATALOG_PATTERN_MIN_SHARE` (suggested: ≥0.6 of non-matching videos share dominant bigram)
- **Distinctive tokens:** Keyword tokens minus `_GENERIC_TOKENS` (and optionally DE fillers in a **channel-relevance-only** stopword set — do not mutate global `_GENERIC_TOKENS` without scorer regression tests).
- **UI surfaces:** None required; cascade job status unchanged.

### Deferred

- **US-076b** — short cadence bonus on M2 cascade (`docs/stories/US-076b-channel-short-cadence-bonus.md`).
- **US-076c** — channel-scoped search, adaptive fetch window, `_score_channel` cadence proxy fix, `relevanceLanguage` DE fix, optional `ChannelModel` cadence persist.

## Validation

When updating durable proof status:
`scripts/bin/harness-cli story update --id US-076 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | `test_channel_relevance_v2.py` — 5 golden cases + anti-trap test + catalog pattern helpers |
| Integration | `test_channel_cascade.py` — existing US-074/075 tests still pass |
| E2E | Not required |
| Platform | Not required |

```bash
python -m pytest videoscout/tests_api/test_channel_relevance_v2.py videoscout/tests_api/test_channel_cascade.py -v
```

## Harness Delta

- Story added to `docs/stories/backlog.md` under Epic E05 (Channel Cascade).
- Builds on US-075; empirical session transcript: keyword `jetzt kommt rolf`, 5-channel YouTube scrape 2026-07-13.

## Evidence

```bash
python -m pytest videoscout/tests_api/test_channel_relevance_v2.py videoscout/tests_api/test_channel_cascade.py -v
# 16 passed, 2 warnings in 2.31s

python -m pytest videoscout/tests_api/ --tb=short -q
# 275 passed, 13 warnings in 64.73s
```
