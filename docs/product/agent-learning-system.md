# Agent Learning System

## Overview

The VideoScout agent learning system enables continuous improvement of keyword recommendations through real-world experiment feedback. Users test agent-suggested keywords in production, report actual results, and the system automatically extracts patterns to refine its scoring model.

## Architecture

```
User Experiment → Report Outcome → Pattern Extraction → Human Approval → Strategy Update
```

### Components

1. **Experiment Tracking**
   - Database: `keyword_experiments` table
   - Captures: keyword, predicted score, actual performance, baseline context
   - Status: in_progress → success/failed/partial

2. **Pattern Extraction**
   - Function: `learn_agent._extract_patterns(experiments)`
   - Algorithm: Group by keyword traits + outcome type
   - Requirements: Min 3 occurrences, min 0.6 confidence
   - Output: Pattern list with evidence and reasoning

3. **Scoring Adjustment**
   - Function: `learn_agent.suggest_scoring_adjustments(patterns)`
   - Returns: Suggested weight adjustments (not auto-applied)
   - Constraints: Adjustments capped to 0.5x - 2.0x range

4. **Human Approval**
   - UI: LearningInsightsDialog with Approve/Reject buttons
   - Only approved adjustments are applied to strategy.json
   - Maintains update_history for auditability

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

1. User completes 5+ experiments
2. Click "View Learning Insights" in UI
3. System analyzes experiments, extracts patterns
4. UI shows:
   - Patterns discovered
   - Suggested weight adjustments
   - Affected examples
5. User clicks Approve or Reject
6. If approved: strategy.json updated with new weights
7. Future keyword evaluations use updated weights

## Safeguards

- **Min occurrences**: Pattern requires 3+ examples to qualify
- **Confidence threshold**: Only patterns with 0.6+ confidence generate suggestions
- **Weight caps**: All adjustments bounded to 0.5x - 2.0x range
- **Human approval**: No automatic strategy changes
- **Audit trail**: update_history in strategy.json logs all changes

## Files

- `videoscout/agents/learn_agent.py`: Core learning logic
- `videoscout/agents/orchestrator.py`: Workflow coordination
- `videoscout/database/db.py`: Schema definitions
- `videoscout/agents/memory/strategy.json`: Current weights and history
- `videoscout/ui/keyword_experiments_tab.py`: User interface

## Future Enhancements

- Statistical significance testing (t-tests, p-values)
- Multi-user experiment aggregation
- Automated TikTok API result tracking
- Export learning reports to markdown
