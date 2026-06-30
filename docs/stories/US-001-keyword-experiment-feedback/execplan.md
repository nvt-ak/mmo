# US-001 Execution Plan

## Implementation Phases

### Phase 1: Database Schema (DONE)
- Create `keyword_experiments` table with baseline normalization fields
- Create `keyword_patterns` table for learning storage
- Add indexes for query performance
- Add CHECK constraints for data integrity

**Files:**
- `videoscout/database/db.py` - Schema definition
- `videoscout/database/migrations/001_add_experiment_computed_fields.sql`

**Acceptance:**
- All tables created
- All constraints working
- All indexes created

### Phase 2: Agent Logic (DONE)
- Implement `analyze_keyword_experiments()`
- Implement `_extract_patterns()` with rule-based grouping
- Implement `suggest_scoring_adjustments()` (returns suggestions only)
- Implement `apply_approved_adjustments()`
- Add `evaluate_keyword()` stub
- Add `run_keyword_learning_cycle()` to orchestrator

**Files:**
- `videoscout/agents/learn_agent.py` - Core learning logic
- `videoscout/agents/evaluate_agent.py` - Keyword evaluation
- `videoscout/agents/orchestrator.py` - Workflow coordination

**Acceptance:**
- Pattern extraction working
- Suggestions returned, not auto-applied
- Integration with existing agent loop

### Phase 3: UI Implementation (DONE)
- Create `KeywordExperimentsTab` in PyQt6 ✅
- Implement reminder banner ✅
- Implement start experiment dialog
- Implement report results dialog
- Implement learning insights dialog with Approve/Reject

**Files:**
- `videoscout/ui/keyword_experiments_tab.py` - Main tab
- `videoscout/ui/learning_insights_dialog.py` - Approval dialog

**Acceptance:**
- All UI components functional
- Reminder banner displays correctly
- Approval workflow working

### Phase 4: Validation (TODO)
- Add integration tests
- Run 5+ real experiments
- Verify pattern discovery
- Verify weight adjustment application

---

## Formula Locking (DONE)

All formulas locked and documented:

### Formula 1: `actual_score`
```python
views_component = min(75.0, views_vs_baseline * 35.0)
engagement_component = min(25.0, actual_engagement * 1.2)
score = views_component + engagement_component
return min(100.0, max(0.0, score))
```

### Formula 2: `classify_outcome`
```python
PREDICTED_SUCCESS_THRESHOLD = 60
predicted_success = predicted_score >= 60
actual_success = test_status == 'success'
if test_status == 'partial': actual_success = False
# Return TP/FP/TN/FN based on boolean combinations
```

### Formula 3: `evaluate_keyword` (MVP)
```python
# Saturation base: fresh=80, medium=55, saturated=25
# +8 for long_tail (3+ words), -10 for single_word
# -5 for viral/trending, +5 for tutorial/how to
```

---

## Known Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Pattern overfitting with small data | Require min 3 occurrences, cap adjustments 0.5x-2.0x |
| Users forget to report | Reminder banner for 7+ day experiments |
| LLM analysis cost | Cache insights 24h, only analyze last 30 experiments |
| `channel_id` ambiguity | Make nullable, use `account_label` for TikTok context |
