# Agent Learning System

## Overview

The VideoScout agent learning system enables continuous improvement of keyword recommendations through real-world experiment feedback. Operators test agent-suggested keywords in production, report actual TikTok results via the web UI, and the system extracts patterns to refine its scoring model. All data persists in PostgreSQL and is accessible through the FastAPI backend.

## Architecture

```
User Experiment → Report Outcome → Pattern Extraction → Human Approval → Strategy Update
```

**Stack (R1):** PostgreSQL → FastAPI (`/api/v1/...`) → Next.js web (`/insights`)

### Components

1. **Experiment Tracking**
   - Database: `keyword_experiments` table (PostgreSQL, Alembic migration `0002`)
   - API: `POST /api/v1/experiments`, `GET /api/v1/experiments`, `POST /api/v1/experiments/{id}/report`
   - Captures: keyword, predicted score, actual performance, baseline context
   - Status: `in_progress` → `reported` (success/failed/partial outcome)

2. **Performance Reports & Knowledge Base**
   - Database: `performance_reports` table (shared migration `0002`)
   - API: `POST /api/v1/performance/reports`, `GET /api/v1/performance/reports?keyword=`
   - `KnowledgeBase.get_context(keyword)` formats recent reports + aggregates for LLM prompts
   - Submissions create `LearningEventModel` records (type=`report`)

3. **Pattern Extraction**
   - Module: `videoscout/core_engine/experiments.py`
   - Functions: `extract_patterns()`, `suggest_weight_adjustments()`
   - API trigger: `POST /api/v1/experiments/analyze`
   - Algorithm: Group by keyword traits + outcome type
   - Requirements: Min 3 occurrences, min 0.6 confidence
   - Output: Pattern list with evidence and reasoning

4. **Scoring Adjustment**
   - Function: `suggest_weight_adjustments(patterns)` in `core_engine/experiments.py`
   - Returns: Suggested weight adjustments (not auto-applied)
   - Constraints: Adjustments capped to 0.5x - 2.0x range
   - No file I/O to legacy `strategy.json`; adjustments returned via API only

5. **Learning Insights (Web)**
   - UI: `/insights` — rejection/success patterns, summary metrics, recent experiments
   - API: `GET /api/v1/learning/insights`, `POST /api/v1/learning/cycle`
   - "Run learning cycle" button triggers analysis and strategy updates
   - Human approval flow preserved — no automatic strategy changes without operator action

## Baseline Normalization

To compare performance across channels of different sizes, all metrics are normalized against the channel's baseline:

```python
views_vs_baseline = actual_views / creator_avg_views

# Example:
# Nano creator (2K avg views): 4K views → 2.0x baseline → good
# Macro creator (100K avg views): 4K views → 0.04x baseline → poor
```

This prevents the system from learning "high absolute views = success" when context matters.

## Agent Suggestion Tracking

Experiments track whether they originated from:
- `agent_suggested`: Agent recommended this keyword with a score
- `user_manual`: User entered this keyword independently

This enables separate accuracy tracking:
- Overall accuracy: All experiments
- Agent accuracy: Only agent-suggested experiments

## Pattern Examples

**Pattern: contains_viral + false_positive**
- Count: 5 occurrences
- Confidence: 0.82
- Insight: "Keywords containing 'viral' consistently overestimated by 15-20 points"
- Suggested adjustment: Reduce search_volume weight from 1.0 to 0.9

**Pattern: long_tail + true_positive**
- Count: 7 occurrences
- Confidence: 0.88
- Insight: "Long-tail keywords (3+ words) consistently underestimated by 10 points"
- Suggested adjustment: Increase trend_velocity weight from 1.0 to 1.1

## Learning Cycle

1. Operator completes 5+ experiments (via API or web report form)
2. Open **Insights** (`/insights`) in the web app
3. Click **Run learning cycle** (or call `POST /api/v1/experiments/analyze`)
4. System analyzes experiments, extracts patterns
5. UI shows:
   - Rejection and success patterns
   - Summary metrics
   - Recent experiments table
6. Review suggested weight adjustments from analyze response
7. Approve adjustments through learning cycle (no auto-apply)
8. Future keyword evaluations use updated weights

## Safeguards

- **Min occurrences**: Pattern requires 3+ examples to qualify
- **Confidence threshold**: Only patterns with 0.6+ confidence generate suggestions
- **Weight caps**: All adjustments bounded to 0.5x - 2.0x range
- **Human approval**: No automatic strategy changes
- **Audit trail**: Learning events and report history in PostgreSQL

## Files

| Layer | Path |
| --- | --- |
| Domain logic | `videoscout/core_engine/experiments.py` |
| Knowledge base | `videoscout/core_engine/knowledge_base.py` |
| Learning agent | `videoscout/core_engine/learning.py` |
| Experiments API | `videoscout/api/experiments.py` |
| Performance API | `videoscout/api/performance.py` |
| Learning API | `videoscout/api/learning.py` |
| DB models | `videoscout/db/models.py` |
| Web UI | `web/src/components/insights/insights-page.tsx` |
| Report form | `web/src/components/insights/performance-report-form.tsx` |
| Legacy (desktop) | `videoscout/ui/keyword_experiments_tab.py` (deprecated, not extended) |

## Future Enhancements

- Statistical significance testing (t-tests, p-values)
- Multi-user experiment aggregation
- Automated TikTok API result tracking
- Export learning reports to markdown
