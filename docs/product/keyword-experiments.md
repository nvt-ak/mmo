# Keyword Experiments

## Purpose

Track real-world keyword performance to validate agent predictions and improve future recommendations.

## User Workflow

### 1. Start Experiment

**When:** After agent suggests keywords or when testing a manual keyword idea

**Steps:**
1. Open VideoScout → Keyword Experiments tab
2. Click "Start New Experiment"
3. Enter keyword (e.g., "newjeans fancam")
4. Select channel to test on
5. Mark source:
   - **Agent Suggested**: If keyword came from agent evaluation
   - **Manual Entry**: If you thought of it independently
6. Click "Start Experiment"

**What happens:**
- System predicts score using current evaluation model
- Experiment saved with status `in_progress`
- Baseline context captured (channel subs, avg views)

### 2. Test Keyword

**Your action:**
- Create TikTok video using the keyword
- Upload and monitor performance for 7-14 days
- Track views, engagement, retention

### 3. Report Results

**When:** After 7-14 days (or when results are conclusive)

**Steps:**
1. Return to Keyword Experiments tab
2. Select your experiment
3. Click "Report Results"
4. Enter actual metrics:
   - Total views
   - Engagement rate (%)
   - Retention rate (%)
5. Mark outcome:
   - ✅ Success: Met or exceeded expectations
   - ⚠️ Partial: Some success but below expectations
   - ❌ Failed: Underperformed significantly
6. Rate 1-5 stars
7. Add comments (optional but helpful)
8. Click "Submit Report"

**What happens:**
- System computes accuracy (predicted vs actual)
- Classifies outcome type (true_positive, false_positive, etc.)
- Uses baseline normalization (your views vs channel average)
- Adds to learning dataset

### 4. View Learning Insights

**When:** After 5+ experiments completed

**Steps:**
1. Click "View Learning Insights"
2. Review patterns discovered:
   - Which keyword types overperformed
   - Which types underperformed
   - Agent suggestion accuracy
3. Review suggested weight adjustments
4. Click **Approve** to apply changes, or **Reject** to keep current strategy

**What happens:**
- If approved: Scoring weights updated
- Future keyword evaluations use new weights
- Change logged in strategy update history

## Reminders

- Yellow banner appears on app startup for experiments 7+ days old
- Banner shows count: "⏰ 2 experiments ready to report"
- Click to view pending experiments

## Metrics Explained

### Views vs Baseline

Performance is normalized against your channel's average:

```
views_vs_baseline = actual_views / channel_avg_views

Example:
- Your channel avg: 2,000 views
- This video: 4,000 views
- Baseline multiplier: 2.0x (good performance)
```

This ensures fair comparison regardless of channel size.

### Accuracy

How close the prediction was:

```
accuracy = 1 - |predicted_score - actual_score| / 100

Example:
- Predicted: 75
- Actual: 82
- Accuracy: 1 - |75-82|/100 = 93%
```

### Outcome Types

- **True Positive**: Predicted success ✅, actually succeeded ✅
- **False Positive**: Predicted success ✅, actually failed ❌
- **True Negative**: Predicted failure ❌, actually failed ❌
- **False Negative**: Predicted failure ❌, actually succeeded ✅

## Best Practices

### For Accurate Learning

1. **Report honestly**: Good and bad results equally important
2. **Wait 7+ days**: Early results can be misleading
3. **Test agent suggestions**: Mix of agent + manual helps track agent accuracy
4. **Add comments**: Context helps (e.g., "Posted at wrong time", "Great hook")
5. **Consistent testing**: Test on same channel for comparable baselines

### For Better Patterns

- Need 3+ similar outcomes to detect a pattern
- More experiments = more reliable insights
- Diverse keyword types help find broader patterns
- Regular learning cycles (weekly/biweekly) keep strategy current

## Privacy & Data

- All experiments stored locally in `videoscout.db`
- No data sent to external servers
- Learning happens on your machine
- Strategy updates saved in `agents/memory/strategy.json`

## Troubleshooting

**"Insufficient data" message:**
- Need at least 5 completed experiments
- Complete and report more experiments

**No patterns found:**
- Need 3+ similar outcomes for a pattern
- Try more experiments with similar keyword types
- Ensure honest reporting (don't only report successes)

**Accuracy seems off:**
- Check if baseline normalization applies to your case
- Consider video quality, posting time, other factors
- Agent learns over time - early predictions less accurate

## Example Experiment

**Start:**
- Keyword: "sewing tutorial beginner"
- Channel: FabricCrafts (5K subs, 2K avg views)
- Source: Agent suggested (score 72)
- Predicted: 72/100

**After 10 days:**
- Actual views: 4,500
- Engagement: 12.0%
- Status: Success ✅
- Rating: 5 stars
- Comments: "Long-tail keyword worked great, clear audience intent"

**Result:**
- Views vs baseline: 2.25x (4500/2000)
- Actual score: 93 (high baseline multiplier + engagement)
- Accuracy: 79%
- Outcome: True Positive
- Contributes to "long_tail + tutorial" pattern
