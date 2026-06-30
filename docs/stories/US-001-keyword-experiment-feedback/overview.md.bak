# US-001: Keyword Experiment Feedback Loop

## Overview

Build a feedback loop where users test agent-suggested keywords and report real performance results. The system learns from these outcomes to improve future keyword recommendations.

## Problem Statement

Current agent evaluation uses TikTok saturation + basic heuristics, but doesn't learn from actual keyword performance. Users have no way to:
- Track keyword experiments
- Report actual performance
- See how agent predictions compare to real results

## Solution

Implement keyword experiment tracking with:
- Database storage for experiment records
- Pattern extraction from completed experiments
- Weight adjustment suggestions based on patterns
- Human approval workflow before applying changes

## Scope

### In Scope
- Experiment tracking (start, report, analyze)
- Pattern extraction (rule-based, min 3 occurrences)
- Weight adjustment suggestions (not auto-apply)
- Reminder for experiments 7+ days old
- UI for experiment management

### Out of Scope
- TikTok API integration for automated tracking
- Statistical significance testing
- Multi-user experiment aggregation
- Export to markdown reports

## Success Criteria

| Criterion | Target |
|-----------|--------|
| Experiments tracked | 5+ completed |
| Patterns discovered | 3+ with confidence >0.6 |
| Weight adjustments applied | After human approval |
| Reminder banner working | 7+ days old experiments |
| Accuracy formula | Match doc example (93 for 4500/2000/12%) |

## Stakeholders

- **Users**: Need to track and report keyword experiments
- **Agents**: Need learned patterns to improve recommendations
- **Developers**: Need clean architecture for future enhancements
