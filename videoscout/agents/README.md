# Agentic Loop System

Self-improving YouTube channel discovery using LLM-powered evaluation and learning.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  ORCHESTRATOR                        │
│         (điều phối toàn bộ agent loop)              │
└──────────┬──────────────┬──────────────┬────────────┘
           │              │              │
    ┌──────▼─────┐ ┌──────▼─────┐ ┌────▼───────┐
    │  DISCOVER  │ │  EVALUATE  │ │   LEARN    │
    │   Agent    │ │   Agent    │ │   Agent    │
    └──────┬─────┘ └──────┬─────┘ └────┬───────┘
           │              │              │
    Search YouTube  Score + Rank   Analyze outcomes
    Find candidates  per channel   Update strategy
```

## Components

### 1. Discover Agent
- Searches YouTube channels using strategy keywords
- Filters by subscriber count, views, upload frequency
- Returns new candidate channels not already tracked

### 2. Evaluate Agent
- Uses LLM (via 9router) to assess channel quality
- Analyzes recent video titles for niche fit
- Scores channels 0-10 for TikTok repost potential
- Provides follow/skip recommendation with reasoning

### 3. Learn Agent
- Analyzes historical channel outcomes
- Identifies patterns (what works, what doesn't)
- Suggests new keywords based on successful channels
- Proposes filter adjustments (subscriber limits, etc.)
- Returns suggestions for human approval

### 4. Orchestrator
- Coordinates Discover → Evaluate → Learn workflow
- Auto-follows top N recommended channels
- Logs all loop executions to database

## Memory Structure

```
agents/memory/
├── strategy.json          # Current search strategy
├── channel_outcomes.json  # Channel → performance history
└── learnings.json         # Discovered patterns
```

## Usage

### From UI

1. Go to **🤖 Agent Loop** tab
2. Click **🔍 Run Discovery** to find + evaluate new channels
3. Click **📊 Run Learning** to analyze outcomes and get suggestions
4. Click **🔄 Run Full Loop** to run both in sequence

### Programmatic

```python
from agents import orchestrator

# Discovery cycle (find + evaluate + auto-follow top 10)
result = orchestrator.run_discovery_cycle(auto_follow_top_n=10)

# Learning cycle (analyze + suggest improvements)
suggestions = orchestrator.run_learning_cycle()

# Full loop
full_result = orchestrator.run_full_loop(auto_follow_top_n=10)

# Apply approved suggestions
orchestrator.apply_learning_suggestions({
    "keywords": ["newjeans fancam", "ive stage"],
    "filters": {"max_subs": 30000}
})
```

## LLM Configuration

Uses 9router local proxy (OpenAI-compatible):

```bash
# .env
LLM_BASE_URL=http://localhost:20128/v1
LLM_API_KEY=sk-local
LLM_MODEL=gpt-4o-mini
```

Start 9router before using agents:
```bash
npm install -g 9router
9router
```

## Self-Improvement Loop

Week 1:
- Strategy: keywords=["kpop fancam", "idol dance"]
- Discover 50 channels → Evaluate → Follow top 10
- Harvest feed → 20 videos

Week 2:
- Learn Agent analyzes:
  - 8/10 channels produced good videos → pattern: "channel <5K subs"
  - 2/10 channels failed → pattern: "upload <2 video/week"
- Update strategy:
  - Add keywords: ["newjeans fancam", "ive stage"]
  - Add filter: upload_freq >= 3/week
  - Adjust weights: sub_score ↑, view_score ↓

Week 3:
- Strategy improved → better channels found
- Loop continues...

## Database Schema

```sql
CREATE TABLE channel_outcomes (
    channel_id      TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    subscribers     INTEGER,
    videos_found    INTEGER,
    avg_video_score REAL,
    llm_score       INTEGER,
    llm_recommendation TEXT,
    llm_reasoning   TEXT,
    outcome         TEXT,
    created_at      TEXT
);

CREATE TABLE agent_loops (
    id              INTEGER PRIMARY KEY,
    loop_type       TEXT NOT NULL,
    discovered      INTEGER,
    evaluated       INTEGER,
    recommended     INTEGER,
    auto_followed   INTEGER,
    learning_status TEXT,
    result_json     TEXT,
    started_at      TEXT,
    completed_at    TEXT
);
```

## Safety

- **Agent suggest → human approve → apply**: Learning Agent proposes changes, you review before applying
- All strategy updates logged in `strategy.json` → `update_history`
- Can rollback by editing `memory/strategy.json` manually
- LLM errors are logged, never crash the loop

## Keyword Learning Cycle

`orchestrator.run_keyword_learning_cycle()` closes the US-001 feedback loop:
- analyzes completed `keyword_experiments`
- persists qualified patterns to `keyword_patterns`
- saves the cycle audit record to `agent_loops`
- returns scoring-weight suggestions for human approval

Approved weights are applied via `learn_agent.apply_approved_adjustments()` and consumed by `evaluate_agent.evaluate_keyword()`.

## Performance

- Discovery cycle: ~5-10 minutes for 50 channels (YouTube API quota: ~200 units)
- Evaluation: ~30 seconds for 10 channels (LLM calls via 9router)
- Learning: <5 seconds (pattern analysis + LLM summarization)
- Full loop: ~10-15 minutes end-to-end

## Extending

Add new skills in `agents/skills/`:
- `tiktok_skills.py` - saturation check integration
- `scoring_skills.py` - custom scoring logic
- `llm_skills.py` - new LLM prompts/evaluations
