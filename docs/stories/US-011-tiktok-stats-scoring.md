# US-011: TikTok Search Stats in Agent Scoring

## Status

planned

## Lane

normal

## Product Contract

Enrich Module **M1 (Keyword Intelligence)** agent scoring with TikTok search
market stats so operators see saturation context alongside LLM scores. Each scored
keyword includes video count, average engagement metrics, and a saturation tier
to support approve/reject decisions in the keyword inbox.

**Epic:** E04 Keyword Intelligence v2  
**Roadmap:** R1 — M1 complete (`docs/superpowers/plans/2026-07-02-r1-keyword-intelligence-v2.md`)

## Relevant Product Docs

- `docs/product/workflows.md` — Module M1 (Keyword Intelligence), Step 1 keyword inbox gate
- `docs/product/PRD.md` — scoring and saturation sections
- `docs/superpowers/plans/2026-07-02-r1-keyword-intelligence-v2.md` — Task 4
- `docs/decisions/0009-keyword-led-content-factory.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- `SuggestionEngine.score_keywords()` calls `TikTokService.search_videos()` per candidate keyword
- Each scored suggestion includes `tiktok_stats` with: `video_count_7d`, `avg_views`, `avg_likes`, `avg_comments`, `saturation_tier` (`fresh` | `moderate` | `saturated`)
- `TikTokService.search_videos` computes `avg_likes` and `avg_comments` from video list when available
- `calculate_saturation()` returns tier and attaches stats dict; persisted on suggestion (`tiktok_status`, `tiktok_count_at_suggest`, or JSONB field)
- US-005 (evaluate_keyword LLM) scope folded into this story per backlog notes
- No R2+ scope (channel cascade, download, merge)

## Design Notes

- **Commands:** Scan job triggers scoring via existing scheduler
- **Queries:** TikTok search API per keyword candidate
- **API:** Extended suggestion response in `videoscout/schemas.py` (`TikTokSearchStats`)
- **Tables:** Optional Alembic `0003` only if JSONB on suggestions required — prefer extending existing suggestion columns
- **Domain rules:** Saturation tiers drive operator context, not hard reject
- **UI surfaces:** Stats visible in inbox when US-003 suggestion cards extended (optional in R1)

## Validation

```bash
python -m pytest videoscout/tests_api/test_tiktok_scoring.py -v
```

| Layer | Expected proof |
| --- | --- |
| Unit | `test_tiktok_scoring.py` — mock TikTok service, assert stats on score output |
| Integration | Full `videoscout/tests_api/` suite passes after engine changes |
| E2E | Manual: scan → inbox shows TikTok stats |
| Platform | TikTok service mockable in tests |
| Release | Harness story update |

Harness update on completion:

```bash
scripts/bin/harness-cli story update --id US-011 --status implemented \
  --unit 1 --integration 0 --e2e 0 --platform 0 \
  --verify "python -m pytest videoscout/tests_api/test_tiktok_scoring.py -v"
```

## Harness Delta

- Registered via Task 1: story add US-011
- Verify command: `python -m pytest videoscout/tests_api/test_tiktok_scoring.py -v`

## Evidence

_Add commands, reports, or links after validation exists._
