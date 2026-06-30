# US-001 Design Document

## Architecture

### Data Flow

```
User starts experiment
    ↓
Agent predicts score (evaluate_keyword)
    ↓
Experiment saved (keyword_experiments table)
    ↓
User reports results (7-14 days later)
    ↓
System computes actual_score + accuracy
    ↓
User clicks "View Learning Insights"
    ↓
Agent extracts patterns from experiments
    ↓
Agent suggests weight adjustments
    ↓
User approves → apply_approved_adjustments()
    ↓
Strategy.json updated → future predictions use new weights
```

## Data Models

### KeywordExperiment

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| keyword | TEXT | Keyword being tested |
| channel_id | TEXT | YouTube channel (nullable) |
| channel_subscribers | INTEGER | Snapshot at experiment start |
| creator_avg_views | INTEGER | Channel baseline for normalization |
| views_vs_baseline | REAL | computed: actual_views / creator_avg_views |
| suggestion_source | TEXT CHECK | 'agent_suggested' | 'user_manual' |
| agent_suggested_score | INTEGER | Score when agent recommended |
| predicted_score | INTEGER | 0-100 prediction |
| prediction_reasoning | TEXT | LLM/algorithm reasoning |
| actual_views | INTEGER | Real performance |
| actual_engagement | REAL | Engagement rate |
| actual_retention | REAL | Retention rate (optional) |
| actual_score | REAL | computed from formula |
| test_status | TEXT CHECK | 'in_progress' | 'success' | 'failed' | 'partial' |
| user_rating | INTEGER CHECK 1-5 | User sentiment |
| user_comments | TEXT | Qualitative feedback |
| accuracy | REAL | computed: 1 - |pred - actual|/100 |
| outcome_type | TEXT CHECK | 'true_positive' | 'false_positive' | etc. |
| keyword_traits | TEXT | JSON array of detected traits |
| account_label | TEXT | Free-text TikTok account |
| reported_at | TEXT | When results reported |
| created_at | TEXT | When experiment started |

### KeywordPattern

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| pattern_type | TEXT | 'overestimate' | 'underestimate' | 'surprise' |
| keyword_trait | TEXT | 'contains_viral' | 'long_tail' | etc. |
| outcome_type | TEXT | 'true_positive' | 'false_positive' | etc. |
| insight | TEXT | Human-readable insight |
| reasoning | TEXT | Evidence supporting insight |
| example_keywords | TEXT | JSON array of examples |
| occurrence_count | INTEGER | Number of experiments matching |
| avg_predicted | REAL | Average predicted score |
| avg_actual | REAL | Average actual score |
| suggested_adjustment | TEXT | JSON: {"search_volume": 0.9} |
| experiment_ids | TEXT | JSON array of experiment IDs |
| confidence | REAL | 0-1 confidence score |
| discovered_at | TEXT | When pattern discovered |
| last_seen_at | TEXT | Most recent matching experiment |

## UI Components

### KeywordExperimentsTab (QWidget)

**Components:**
- `QTableWidget`: List of experiments with columns
- `QPushButton`: Start New Experiment
- `QPushButton`: Report Results
- `QPushButton`: View Learning Insights
- `QLabel`: Reminder banner (7+ day experiments)

**Methods:**
- `load_experiments()`: Query and display experiments
- `start_experiment_dialog()`: Modal for starting experiment
- `report_results_dialog()`: Modal for reporting results
- `show_insights()`: Show LearningInsightsDialog
- `check_pending_reminders()`: Check for 7+ day old experiments

### LearningInsightsDialog (QDialog)

**Components:**
- `QLabel`: Stats summary (total, TP, FP, accuracy)
- `QLabel`: Patterns discovered (trait + outcome + count)
- `QLabel`: LLM insights (if available)
- `QLabel`: Suggested adjustments (if any)
- `QPushButton`: Approve (green, bold)
- `QPushButton`: Reject (gray)

**Behavior:**
- Shows patterns with confidence scores
- Shows weight adjustment recommendations
- Only closes with Approve or Reject
- Calls `apply_approved_adjustments()` on Approve

## Key Algorithms

### Pattern Extraction

```python
1. Group experiments by (keyword_trait, outcome_type)
2. Filter groups with >= 3 occurrences
3. For each group:
   - avg_predicted = mean of predicted scores
   - avg_actual = mean of actual scores
   - confidence = 1 - stddev(accuracies)
4. Sort by occurrence_count DESC, confidence DESC
```

### Weight Adjustment Suggestion

```python
1. For each pattern:
   - If confidence >= 0.6 and count >= 3:
     - If "contains_viral" + "false_positive":
       → Reduce search_volume by 10%
     - If "long_tail" + "false_negative":
       → Increase trend_velocity by 10%
2. Cap all adjustments to 0.5x - 2.0x
3. Return suggestions for human approval
```

## Database Queries

### Reminder Query
```sql
SELECT * FROM keyword_experiments
WHERE test_status = 'in_progress'
AND julianday('now') - julianday(created_at) >= 7
```

### Pattern Extraction Query
```sql
SELECT keyword, outcome_type, predicted_score, actual_score
FROM keyword_experiments
WHERE reported_at IS NOT NULL
```

### Agent Learning Cycle Query
```sql
SELECT * FROM keyword_experiments
WHERE test_status IN ('success', 'failed', 'partial')
AND reported_at IS NOT NULL
ORDER BY reported_at DESC
LIMIT 100
```

## Error Handling

| Error | Handling |
|-------|----------|
| LLM unavailable | Log warning, continue without insights |
| Missing baseline data | Use defaults (avg_views=2000) |
| Invalid source value | CHECK constraint rejects |
| Insufficient data (<5 experiments) | Return "insufficient_data" status |
| Divide by zero | Guard with `if creator_avg_views > 0` |

## Security Considerations

- No user authentication required (local desktop app)
- All data stored locally in SQLite
- Strategy updates logged in history
- No external API calls for experiment data
