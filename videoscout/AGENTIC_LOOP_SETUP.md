# Agentic Loop - Setup Complete ✅

## What Was Built

### 🏗️ Architecture

```
videoscout/
├── agents/
│   ├── memory/
│   │   ├── strategy.json              # Current search strategy
│   │   ├── channel_outcomes.json      # Performance tracking
│   │   └── learnings.json             # Discovered patterns
│   ├── skills/
│   │   ├── llm_skills.py              # 9router LLM client
│   │   ├── youtube_skills.py          # YouTube API wrappers
│   │   └── scoring_skills.py          # Enhanced scoring
│   ├── discover_agent.py              # Keyword-based channel discovery
│   ├── evaluate_agent.py              # LLM-powered evaluation
│   ├── learn_agent.py                 # Pattern analysis + suggestions
│   ├── orchestrator.py                # Main coordinator
│   └── README.md                      # Full documentation
├── ui/
│   ├── agent_tab.py                   # New Agent Loop UI
│   └── main_window.py                 # Updated with Agent tab
└── database/
    └── db_migrations.py               # Agent DB schema
```

### 🗄️ Database Schema

**New Tables:**
- `channel_outcomes` - Tracks which channels worked well
- `agent_loops` - Logs all loop executions

### 🎯 Features

1. **Discover Agent**
   - Searches YouTube by strategy keywords
   - Filters by subs, views, upload frequency
   - Returns new candidates

2. **Evaluate Agent**
   - LLM analyzes video titles for niche fit
   - Scores 0-10 for TikTok repost potential
   - Provides follow/skip recommendation + reasoning

3. **Learn Agent**
   - Analyzes historical outcomes
   - Identifies success patterns
   - Suggests new keywords + filter adjustments
   - Human approval required before applying

4. **Orchestrator**
   - Runs Discover → Evaluate → Learn
   - Auto-follows top N recommendations
   - Logs results to DB

### 🎨 UI Integration

New **🤖 Agent Loop** tab with 3 buttons:
- **🔍 Run Discovery** - Find + evaluate new channels
- **📊 Run Learning** - Analyze + suggest improvements
- **🔄 Run Full Loop** - Complete cycle

## Setup Steps

### 1. Install Dependencies

```bash
cd videoscout
pip install -r requirements.txt
```

**New dependency:** `openai==1.54.3` (for 9router client)

### 2. Configure 9router

Already added to `.env`:
```bash
LLM_BASE_URL=http://localhost:20128/v1
LLM_API_KEY=sk-local
LLM_MODEL=gpt-4o-mini
```

### 3. Start 9router

```bash
# Install globally
npm install -g 9router

# Start (opens dashboard at localhost:20128)
9router
```

### 4. Run VideoScout

```bash
python main.py
```

### 5. Use Agent Loop

1. Go to **🤖 Agent Loop** tab
2. Click **🔍 Run Discovery**
3. Wait 5-10 minutes (searches YouTube, evaluates with LLM)
4. Results show in UI with JSON details
5. Auto-follows top 10 recommended channels
6. Click **📊 Run Learning** after a few cycles to get suggestions

## Self-Improvement Example

**Week 1:**
- Keywords: `["kpop fancam", "idol dance"]`
- Discovers 50 channels
- Follows top 10
- Harvests 20 videos

**Week 2:**
- Learn Agent finds: 8/10 channels worked → pattern is `<5K subs`
- Suggests: Add `["newjeans fancam", "ive stage"]`, lower `max_subs` to 30K
- You approve → strategy updates
- Next cycle finds better channels

**Week 3+:**
- Strategy continuously improves
- Better channels → better videos
- Less manual curation needed

## API Usage

### Programmatic

```python
from agents import orchestrator

# Discovery cycle
result = orchestrator.run_discovery_cycle(auto_follow_top_n=10)
# Returns: {discovered, evaluated, recommended, auto_followed, top_channels}

# Learning cycle
suggestions = orchestrator.run_learning_cycle()
# Returns: {analysis, suggestions, status: "pending_approval"}

# Apply approved suggestions
orchestrator.apply_learning_suggestions({
    "keywords": ["newjeans fancam"],
    "filters": {"max_subs": 30000}
})
```

### Memory Files

Edit `agents/memory/strategy.json` to manually adjust:
- `keywords` - Search terms
- `filters` - Subscriber/view/duration limits
- `weights` - Scoring weights
- `llm.enabled` - Toggle LLM evaluation

## Performance

- **Discovery**: ~5-10 min for 50 channels (200 YouTube API units)
- **Evaluation**: ~30 sec for 10 channels (LLM via 9router)
- **Learning**: <5 sec (pattern analysis)
- **Full loop**: ~10-15 min total

## Safety

✅ **Human-in-the-loop**: Learning Agent suggests → you approve → applies
✅ **Rollback**: Edit `strategy.json` manually
✅ **Logging**: All loops logged to `agent_loops` table
✅ **Error handling**: LLM errors never crash the loop

## Troubleshooting

**"ModuleNotFoundError: No module named 'openai'"**
```bash
pip install openai
```

**"LLM connection failed"**
- Check 9router is running: `http://localhost:20128`
- Check `.env` has correct `LLM_BASE_URL`

**"No keywords in strategy"**
- Default keywords loaded from `memory/strategy.json`
- Edit file to add your keywords

**"Discovery returns 0 channels"**
- YouTube API quota exhausted (resets daily)
- Keywords too specific
- All matching channels already tracked

## Next Steps

1. ✅ Start 9router
2. ✅ Run `python main.py`
3. ✅ Test Discovery cycle
4. ⏳ Let it run for a few days
5. ⏳ Run Learning cycle
6. ⏳ Review + approve suggestions
7. ⏳ Repeat → continuous improvement

## Files Changed

- `videoscout/agents/` - Full agent system (new)
- `videoscout/ui/agent_tab.py` - Agent UI (new)
- `videoscout/ui/main_window.py` - Added Agent tab
- `videoscout/database/db_migrations.py` - Agent schema (new)
- `videoscout/.env` - Added LLM config
- `videoscout/requirements.txt` - Added openai

**Total:** 15 new files, 2 modified files
