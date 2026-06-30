# US-001 Validation Plan

## Unit Tests

| Test | File | Coverage |
|------|------|----------|
| `test_insert_experiment_with_all_fields` | test_keyword_schema.py | Schema acceptance |
| `test_suggestion_source_constraint` | test_keyword_schema.py | CHECK constraint |
| `test_test_status_constraint` | test_keyword_schema.py | CHECK constraint |
| `test_reminder_query` | test_keyword_schema.py | 7-day old query |
| `test_compute_actual_score_doc_example` | test_keyword_schema.py | Formula correctness |
| `test_compute_actual_score_macro_fail` | test_keyword_schema.py | Edge case handling |
| `test_compute_actual_score_with_retention` | test_keyword_schema.py | Bonus calculation |
| `test_classify_outcome_all_types` | test_keyword_schema.py | Outcome logic |
| `test_classify_outcome_threshold` | test_keyword_schema.py | Threshold = 60 |
| `test_compute_accuracy` | test_keyword_schema.py | Accuracy formula |
| `test_dataclass_from_db_row` | test_keyword_schema.py | Model mapping |
| `test_pattern_with_adjustment` | test_keyword_schema.py | Pattern storage |

**Result:** 12/12 passing ✅

## Integration Tests

### Full Learning Cycle

```python
def test_full_keyword_learning_cycle():
    # 1. Insert 5 experiments (3 viral failed, 2 tutorial success)
    # 2. Run run_keyword_learning_cycle()
    # 3. Verify patterns discovered (contains_viral+false_positive)
    # 4. Verify suggestions generated (search_volume adjustment)
    # 5. Call apply_approved_adjustments()
    # 6. Verify strategy.json updated
```

## Manual Test Scenarios

### Scenario 1: Start & Report Experiment
1. Open VideoScout → Keyword Experiments tab
2. Click "Start New Experiment"
3. Enter keyword: "newjeans fancam", channel: Test Channel
4. Click "Start Experiment"
5. After 7+ days, click "Report Results"
6. Enter: 4500 views, 12% engagement, Status: Success, Rating: 5
7. Verify: accuracy=83%, outcome=true_positive, actual_score=93

### Scenario 2: Pattern Discovery
1. Complete 5+ experiments with similar keywords
2. Click "View Learning Insights"
3. Verify: Patterns discovered with confidence > 0.6
4. Verify: Examples listed correctly

### Scenario 3: Approval Flow
1. After learning insights, verify: "Suggested adjustments" shown
2. Click "Reject"
3. Verify: strategy.json unchanged
4. Click "View Learning Insights" again
5. Click "Approve"
6. Verify: strategy.json updated with new weights
7. Verify: update_history logged

### Scenario 4: Reminder Banner
1. Start experiment with created_at = datetime('now', '-8 days')
2. Close and reopen app
3. Verify: Yellow banner shows "1 experiments ready to report"
4. Report results for that experiment
5. Reopen app
6. Verify: Banner shows "0 experiments ready to report"

### Scenario 5: Baseline Normalization
1. Start experiment on nano creator (2K avg views)
2. Report: 4000 views → views_vs_baseline=2.0
3. Start experiment on macro creator (100K avg views)
4. Report: 4000 views → views_vs_baseline=0.04
5. Verify: Nano gets higher actual_score despite same absolute views

## Acceptance Checklist

- [x] Phase 1: Schema created with all required columns
- [x] Phase 1: CHECK constraints working
- [x] Phase 1: All indexes created
- [x] Phase 1: Migration script exists
- [x] Phase 2: Pattern extraction logic implemented
- [x] Phase 2: Suggestions return (not auto-apply)
- [x] Phase 2: Weight adjustments capped 0.5x-2.0x
- [x] Phase 2: Formula 1 (actual_score) matches doc example
- [x] Phase 2: Formula 2 (classify_outcome) uses threshold 60
- [x] Phase 2: Formula 3 (evaluate_keyword) uses saturation heuristics
- [x] Unit tests: 12/12 passing
- [x] Dataclasses: KeywordExperiment, KeywordPattern created
- [ ] Phase 3: UI tab implemented
- [ ] Phase 3: Reminder banner functional
- [ ] Phase 3: Approval dialog with Approve/Reject
- [ ] Manual: 5+ real experiments completed
- [ ] Manual: Pattern discovery verified
- [ ] Manual: Weight adjustment workflow verified
