# US-001: Keyword Experiment Feedback Loop

## Status

completed

## Lane

normal

## Product Contract

The VideoScout agent system must learn from real user experiment outcomes to improve keyword recommendations. Users can track keyword experiments, report actual performance results, and the system extracts patterns to adjust scoring weights. All weight adjustments require human approval before application.

## Relevant Product Docs

- `videoscout/agents/README.md` (existing - describes agent loop)
- `docs/product/agent-learning-system.md` (to be created)
- `docs/product/keyword-experiments.md` (to be created)

## Acceptance Criteria

- Database schema supports experiments with baseline context (channel_subscribers, creator_avg_views, views_vs_baseline)
- User can start experiment with source tracking (agent_suggested vs user_manual)
- User can report actual performance with baseline-normalized scoring
- System computes accuracy using baseline-adjusted metrics
- Learn agent extracts patterns (min 3 occurrences, min 0.6 confidence)
- Agent suggests weight adjustments (returns suggestions, does not auto-apply)
- UI shows approval dialog with Approve/Reject buttons
- Reminder banner displays on app startup for experiments 7+ days old
- Agent suggestion accuracy tracked separately from manual experiments

## Design Notes

**Commands:**
- `start_experiment(keyword, channel_id, source, agent_score)` → experiment_id
- `report_outcome(experiment_id, actual_views, engagement, status, rating, comments)` → updated experiment
- `run_keyword_learning_cycle()` → {analysis, suggestions, action_required}
- `apply_approved_adjustments(adjustments)` → updated strategy

**Queries:**
- `get_experiments(status)` → list of experiments
- `get_pending_reminders()` → experiments 7+ days old
- `analyze_keyword_experiments()` → {patterns, stats, llm_insights}

**Tables:**
- `keyword_experiments`: id, keyword, channel_id, channel_subscribers, creator_avg_views, views_vs_baseline, suggestion_source, agent_suggested_score, predicted_score, actual_views, accuracy, outcome_type, test_status, user_rating, reported_at
- `keyword_patterns`: id, pattern_type, keyword_trait, outcome_type, insight, occurrence_count, confidence, discovered_at

**Domain rules:**
- Pattern requires min 3 occurrences to qualify
- Weight adjustments capped to 0.5x - 2.0x range
- Accuracy computed as: 1 - |predicted - actual_normalized| / 100
- Outcome types: true_positive, false_positive, true_negative, false_negative
- Baseline normalization: views_vs_baseline = actual_views / creator_avg_views

**UI surfaces:**
- Desktop PyQt6: KeywordExperimentsTab with table, start/report dialogs, insights dialog

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-001 --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | 7 tests: pattern extraction, baseline normalization, suggestion format, weight caps, insufficient data, agent tracking |
| Integration | 1 test: full cycle (insert experiments → analyze → suggest → approve → verify strategy) |
| E2E | Manual: 5 scenarios (baseline normalization, agent tracking, approval flow, pattern extraction, reminder banner) |
| Platform | N/A (desktop only) |
| Release | Manual validation with 20+ real experiments over 4 weeks |

## Harness Delta

**New capabilities needed:**
- None (uses existing Python test framework, SQLite database, PyQt6 UI)

**Documentation updates:**
- Create `docs/product/agent-learning-system.md` to describe learning architecture
- Create `docs/product/keyword-experiments.md` to describe user workflow
- Update `videoscout/agents/README.md` to document keyword learning cycle

## Evidence

Implementation phases:
1. Phase 1: Database schema (keyword_experiments, keyword_patterns tables)
2. Phase 2: Learn agent enhancement (_extract_patterns, suggest_scoring_adjustments, apply_approved_adjustments)
3. Phase 3: UI (KeywordExperimentsTab with reminder banner, start/report dialogs, insights approval dialog)
4. Phase 4: Orchestrator integration (run_keyword_learning_cycle)

Unit tests: `videoscout/tests/test_learn_agent.py`
Integration test: `videoscout/tests/test_keyword_learning_integration.py`
Manual test scenarios documented in story notes.

## Notes

All review fixes incorporated:
- FIX #1: Schema includes baseline context (channel_subscribers, creator_avg_views, views_vs_baseline)
- FIX #2: Approval flow enforced (suggest_scoring_adjustments → UI approval → apply_approved_adjustments)
- FIX #3: _extract_patterns() fully specified with min occurrences, confidence calculation
- FIX #4: Suggestion tracking (suggestion_source, agent_suggested_score, separate agent_accuracy stat)
- FIX #5: Desktop-friendly reminders (banner on startup, check experiments 7+ days old)

Consistent with existing learn_agent.py approval pattern where suggestions are returned for human review before application.

## Updated Notes (Post-Review)

### Schema Compatibility Verified
- ✅ `channels.avg_views` exists - can use for baseline
- ✅ `agent_loops` table exists - reuse for keyword_learning cycle
- ✅ `channel_outcomes` separate - no conflict

### Missing Function
- ⚠️ `evaluate_keyword()` does not exist in codebase
- **Solution**: Add stub in Phase 2 that returns mock score
- **Full implementation**: Separate story (US-002: Keyword Evaluation with LLM)

### Verification Command
Add when test suite complete:
```bash
python -m pytest videoscout/tests/test_learn_agent.py -v
```

### Related Tables
- `channel_outcomes`: Tracks channel discovery outcomes (separate concern)
- `agent_loops`: Reuse for keyword_learning_cycle tracking
- `channels`: Source for baseline context (avg_views, subscribers)


## Completion Status

**Phase 1 (Schema):** Complete ✅
- `keyword_experiments` table with baseline normalization
- `keyword_patterns` table for learning storage
- 8 indexes, CHECK constraints, foreign keys

**Phase 2 (Agent Logic):** Complete ✅
- Pattern extraction (min 3 occurrences, 0.6 confidence)
- Weight adjustment suggestions (not auto-apply)
- 3 formulas locked: `actual_score`, `classify_outcome`, `evaluate_keyword`
- 12 unit tests passing

**Phase 3 (UI):** Complete ✅
- KeywordExperimentsTab with reminder banner
- LearningInsightsDialog with Approve/Reject
- Fixed blockers: UserRole data, sqlite3.Row, scheduler import

**Phase 4 (Orchestrator):** Complete ✅
- `run_keyword_learning_cycle()` integrated in orchestrator
- Saves loop record to `agent_loops` table
- Returns analysis + suggestions + action_required flag
- 8 unit tests + 3 integration tests passing (11 total, both PYTHONPATH contexts)
- Weight consumption: `evaluate_keyword()` reads `keyword_scoring_weights` from strategy
- UI orchestrator path: `show_insights()` calls `run_keyword_learning_cycle()`
- Pattern persistence: qualified patterns saved to `keyword_patterns` table
- Connection leak fixed: orchestrator closes conn after INSERT

**Pending (Validation):**
- Manual E2E: 5 scenarios (baseline normalization, agent tracking, approval flow, pattern extraction, reminder banner)
- Production: 5+ real experiments, pattern discovery verification, weight adjustment workflow
- Docs: Create `agent-learning-system.md`, `keyword-experiments.md`; update `agents/README.md`
