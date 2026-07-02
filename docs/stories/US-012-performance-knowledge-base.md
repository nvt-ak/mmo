# US-012: Performance Report Knowledge Base

## Status

planned

## Lane

normal

## Product Contract

Complete the Module **M1 (Keyword Intelligence)** feedback path: operators submit
TikTok performance reports via API; reports persist in PostgreSQL and feed a
`KnowledgeBase` that enriches future agent keyword extraction prompts. Closes
the async loop in `workflows.md` Step 6 — report performance → improves agent.

**Epic:** E04 Keyword Intelligence v2  
**Roadmap:** R1 — M1 complete (`docs/superpowers/plans/2026-07-02-r1-keyword-intelligence-v2.md`)

## Relevant Product Docs

- `docs/product/workflows.md` — Module M1, object lifecycle `PerformanceReport: submitted → ingested`, Step 6 async feedback
- `docs/product/keyword-experiments.md` — report results workflow
- `docs/product/agent-learning-system.md` — learning architecture (update on R1 closeout)
- `docs/superpowers/plans/2026-07-02-r1-keyword-intelligence-v2.md` — Task 5
- `docs/decisions/0009-keyword-led-content-factory.md`

## Acceptance Criteria

- `POST /api/v1/performance/reports` — submit TikTok stats for a keyword (views, likes, comments, followers_gained, outcome, notes)
- `GET /api/v1/performance/reports?keyword=` — report history for keyword
- `KnowledgeBase.get_context(keyword)` returns formatted snippet (last N reports + aggregate stats) for LLM prompt in `extract_keywords()`
- `PerformanceReport` submission creates `LearningEventModel` with type=`report`
- Uses `performance_reports` table from US-010 migration
- Web form UI deferred to US-013; this story is API + KB engine only

## Design Notes

- **Commands:** None (API-driven)
- **Queries:** `KnowledgeBase.get_context()`, report history by keyword
- **API:** `videoscout/api/performance.py` registered in `videoscout/api_main.py`
- **Tables:** `performance_reports` (FK to `suggestions` optional)
- **Domain rules:** Outcome enum matches product contract (`success`, `partial`, `failed` or equivalent CHECK)
- **UI surfaces:** Report form in US-013 `/insights`

## Validation

```bash
python -m pytest videoscout/tests_api/test_performance_api.py -v
```

| Layer | Expected proof |
| --- | --- |
| Unit | KB context formatting tests |
| Integration | `test_performance_api.py` — submit, list, learning event created |
| E2E | Manual via US-013 report form |
| Platform | PostgreSQL required |
| Release | Harness story update |

Harness update on completion:

```bash
scripts/bin/harness-cli story update --id US-012 --status implemented \
  --unit 1 --integration 1 --e2e 0 --platform 0 \
  --verify "python -m pytest videoscout/tests_api/test_performance_api.py -v"
```

## Harness Delta

- Registered via Task 1: story add US-012
- Verify command: `python -m pytest videoscout/tests_api/test_performance_api.py -v`

## Evidence

_Add commands, reports, or links after validation exists._
