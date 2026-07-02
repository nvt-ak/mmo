# Keyword Experiments

## Purpose

Track real-world keyword performance to validate agent predictions and improve future recommendations. R1 delivers the full workflow on the **web stack** (PostgreSQL + FastAPI + Next.js). The legacy PyQt6 desktop tab is deprecated and not extended.

## User Workflow (Web)

Primary surface: **Insights** page at `/insights` in the web app.

### 1. Start Experiment

**When:** After agent suggests keywords or when testing a manual keyword idea

**Via API** (automation or future UI):

```http
POST /api/v1/experiments
Content-Type: application/json

{
  "keyword": "newjeans fancam",
  "channel_id": "UC...",
  "channel_subscribers": 5000,
  "creator_avg_views": 2000,
  "suggestion_source": "agent_suggested",
  "agent_suggested_score": 72,
  "predicted_score": 72
}
```

**What happens:**
- System predicts score using current evaluation model
- Experiment saved with status `in_progress`
- Baseline context captured (channel subs, avg views)

### 2. Test Keyword

**Your action:**
- Create TikTok video using the keyword
- Upload and monitor performance for 7-14 days
- Track views, likes, comments, followers gained

### 3. Report Results

**When:** After 7-14 days (or when results are conclusive)

**Web steps:**
1. Open the web app → navigate to **Insights** (`/insights`)
2. In the **Report performance** form, select an approved keyword from the dropdown (or type one manually)
3. Enter actual metrics:
   - Views
   - Likes
   - Comments
   - Followers gained
4. Select outcome: Success / Neutral / Failure
5. Click **Submit report**

**API equivalent:**

```http
POST /api/v1/performance/reports
Content-Type: application/json

{
  "keyword": "newjeans fancam",
  "actual_views": 4500,
  "actual_likes": 320,
  "actual_comments": 45,
  "followers_gained": 12,
  "outcome": "success",
  "suggestion_id": "<optional-uuid>"
}
```

**Experiment report** (full experiment lifecycle):

```http
POST /api/v1/experiments/{experiment_id}/report
```

**What happens:**
- Report persisted in `performance_reports` table
- `LearningEventModel` created (type=`report`)
- `KnowledgeBase` enriches future keyword extraction prompts
- System computes accuracy (predicted vs actual) when linked to an experiment
- Uses baseline normalization (your views vs channel average)

### 4. View Experiments & Learning Insights

**When:** Any time; pattern analysis after 5+ completed experiments

**Web steps:**
1. Open **Insights** (`/insights`)
2. Review **Recent experiments** table (shows `in_progress` and `reported` items)
3. Review rejection patterns, success patterns, and summary metrics
4. Click **Run learning cycle** to trigger pattern analysis
5. Review suggested weight adjustments from the learning cycle response

**API endpoints:**

| Action | Endpoint |
| --- | --- |
| List experiments | `GET /api/v1/experiments` |
| List experiments (filtered) | `GET /api/v1/experiments?status=in_progress` |
| Analyze patterns | `POST /api/v1/experiments/analyze` |
| Learning insights | `GET /api/v1/learning/insights` |
| Run learning cycle | `POST /api/v1/learning/cycle` |
| Report history | `GET /api/v1/performance/reports?keyword=` |

**What happens:**
- Pattern extraction requires min 3 occurrences, min 0.6 confidence
- Weight suggestions capped 0.5x–2.0x, not auto-applied
- Future keyword evaluations use approved strategy updates

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

- Experiments and reports stored in PostgreSQL (local or deployed instance)
- API served by FastAPI backend (`videoscout/api_main.py`)
- Web UI consumes API only — no direct DB access
- Learning happens server-side; strategy updates require operator approval

## Troubleshooting

**"Insufficient data" message:**
- Need at least 5 completed experiments
- Complete and report more experiments via `/insights`

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

**After 10 days (report via `/insights`):**
- Actual views: 4,500
- Likes: 320, Comments: 45
- Outcome: Success
- Followers gained: 12

**Result:**
- Views vs baseline: 2.25x (4500/2000)
- Actual score: 93 (high baseline multiplier + engagement)
- Accuracy: 79%
- Outcome: True Positive
- Contributes to "long_tail + tutorial" pattern
