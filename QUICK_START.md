# Quick Start Guide - MMO Repository

## 🚀 Get VideoScout Running (5 minutes)

### 1. Prerequisites
```bash
# Check Python version (need 3.10+)
python3 --version

# Navigate to project
cd /Users/nvt/Documents/mmo/videoscout
```

### 2. Setup Environment
```bash
# Create virtual environment (if not exists)
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### 3. Configure API Keys
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your YouTube API key
# Get key from: https://console.cloud.google.com/apis/credentials
nano .env
```

Required in `.env`:
```bash
YOUTUBE_API_KEY=your_actual_key_here
LLM_BASE_URL=http://localhost:20128/v1
LLM_API_KEY=sk-local
LLM_MODEL=gpt-4o-mini
```

### 4. Start 9router (for AI features)
```bash
# Install globally (once)
npm install -g 9router

# Start in separate terminal
9router
# Opens dashboard at http://localhost:20128
```

### 5. Run VideoScout
```bash
# From videoscout/ directory with venv activated
python main.py
```

### 6. First Use
1. Go to **⚙️ Settings** tab
2. Verify YouTube API Key is saved
3. Adjust filters if needed (default: 150K-200K views, <50K subs, <3min)
4. Go to **🔍 Discovery** tab
5. Click **Search YouTube** and enter keyword: "kpop fancam"
6. Add some channels
7. Go to **📋 Daily Digest** tab
8. Click **Scan Now**
9. See discovered videos with scores!

---

## 🤖 Using the AI Agent Loop

### What it does
Autonomously discovers, evaluates, and learns which YouTube channels produce good TikTok repost candidates.

### How to use

**Step 1: Run Discovery**
```
Go to 🤖 Agent Loop tab → Click "🔍 Run Discovery"
```
- Searches YouTube with current strategy keywords
- LLM evaluates each channel (0-10 score)
- Auto-follows top 10 recommended channels
- Takes 5-10 minutes

**Step 2: Review Results**
- Check "Last Discovery Result" section
- See which channels were auto-followed
- Review LLM reasoning for each

**Step 3: Let it Learn** (after a few cycles)
```
Click "📊 Run Learning"
```
- Analyzes which channels performed well
- Suggests new keywords to try
- Proposes filter adjustments
- Shows suggestions in UI

**Step 4: Apply Suggestions** (manual approval)
- Review suggestions
- Edit `videoscout/agents/memory/strategy.json` to apply approved changes
- Next discovery cycle uses updated strategy

### Agent Memory Files

**Current Strategy:**
```bash
cat videoscout/agents/memory/strategy.json
```

**Historical Performance:**
```bash
cat videoscout/agents/memory/channel_outcomes.json
```

**Learned Patterns:**
```bash
cat videoscout/agents/memory/learnings.json
```

---

## 📊 Typical Workflow

### Option A: Manual Mode (No AI)
1. Manually add channels in **Discovery** tab
2. **Daily Digest** → Scan Now
3. Review scored videos
4. Copy URLs for download

### Option B: AI-Assisted Mode
1. Set initial keywords in strategy.json
2. **Agent Loop** → Run Discovery (weekly)
3. Agent auto-follows best channels
4. **Daily Digest** → Scan Now (daily)
5. **Agent Loop** → Run Learning (monthly)
6. Review and apply suggestions
7. Repeat → improves over time

### Option C: Hybrid Mode
1. Use **Agent Loop** to discover channels
2. Manually review and tag them
3. Use **Daily Digest** for video scanning
4. Use **TikTok Check** before choosing niches
5. Use **Analytics** to track performance

---

## 🛠️ Common Tasks

### Add YouTube API Key
```bash
# Edit .env file
nano videoscout/.env

# Add line:
YOUTUBE_API_KEY=AIzaSy...your_key_here
```

### Check Database
```bash
sqlite3 videoscout/videoscout.db

# List tables
.tables

# Show channels
SELECT name, subscribers, is_active FROM channels;

# Show recent videos
SELECT title, view_count, opportunity_score 
FROM videos 
ORDER BY found_at DESC 
LIMIT 10;

# Exit
.quit
```

### View Logs
```bash
# Application logs
ls -lh videoscout/logs/

# View latest log
tail -f videoscout/logs/videoscout_*.log
```

### Reset Agent Memory
```bash
# Backup first
cp videoscout/agents/memory/strategy.json strategy.backup.json

# Edit with fresh keywords
nano videoscout/agents/memory/strategy.json
```

### Build Executable (Windows)
```bash
cd videoscout
pyinstaller --onefile --windowed --name VideoScout \
  --add-data "*.env;." main.py

# Output: dist/VideoScout.exe
```

---

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'PyQt6'"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "YouTube API quota exceeded"
- Quota: 10,000 units/day
- Search = ~100 units
- Channel details = ~1 unit
- Resets at midnight Pacific Time
- Solution: Wait or create new API key

### "LLM connection failed"
```bash
# Check 9router is running
curl http://localhost:20128/v1/models

# Restart 9router
pkill -f 9router
9router
```

### "No videos found"
- Check filters in Settings (might be too restrictive)
- Try broader keywords
- Verify channels are active
- Check YouTube API key is valid

### Database locked
```bash
# Close the app first, then:
rm videoscout/videoscout.db-shm
rm videoscout/videoscout.db-wal
```

---

## 📈 Performance Expectations

| Task | Time | API Quota |
|------|------|-----------|
| Manual channel scan | ~2-5 sec | ~1 unit |
| Daily Digest (10 channels) | ~30 sec | ~10 units |
| Agent Discovery (50 channels) | ~5-10 min | ~200 units |
| Agent Evaluation (10 channels) | ~30 sec | 0 (uses LLM) |
| Agent Learning | <5 sec | 0 (local analysis) |

**Daily API Budget Planning:**
- Manual scanning: ~100 channels/day = 100 units
- Agent discovery: 1 cycle = 200 units
- Daily digest: 3 scans = 30 units
- Total: ~330 units (well within 10K limit)

---

## 🎯 Default Filters (Adjustable in Settings)

| Filter | Default | Why |
|--------|---------|-----|
| Views | 150K – 200K | Sweet spot: viral but not oversaturated |
| Uploaded within | 30 days | Fresh content only |
| Channel size | < 50K subs | Less likely to copyright strike |
| Duration | < 3 minutes | TikTok-friendly length |
| Niche tag | "kpop" | Focus on one vertical |

---

## 💡 Tips

1. **Start Small**: Add 5-10 channels, test scanning before scaling
2. **Tag Niches**: Use consistent tags (kpop, dance, comedy) for filtering
3. **Check TikTok First**: Use TikTok Check tab before committing to a niche
4. **Weekly Discovery**: Run agent loop once/week to find new channels
5. **Monthly Learning**: Run learning cycle after accumulating data
6. **Export Data**: Use Analytics tab to export CSV for external analysis
7. **Backup Strategy**: Keep `strategy.json` backups before experiments
8. **Monitor Quota**: Check YouTube API console for daily usage

---

## 📚 File Locations Reference

| What | Where |
|------|-------|
| Main app | `videoscout/main.py` |
| Configuration | `videoscout/.env` |
| Database | `videoscout/videoscout.db` |
| Agent strategy | `videoscout/agents/memory/strategy.json` |
| Logs | `videoscout/logs/` |
| UI code | `videoscout/ui/` |
| Agent code | `videoscout/agents/` |
| Services | `videoscout/services/` |

---

## 🎓 Learning Path

1. **Day 1**: Setup → Add 5 channels → Test Daily Digest
2. **Day 2**: Configure filters → Add more channels → Test TikTok Check
3. **Day 3**: Run first Agent Discovery → Review results
4. **Week 2**: Let agents accumulate data → Run Learning cycle
5. **Week 3**: Apply learned suggestions → Measure improvement
6. **Month 2**: Fully autonomous weekly discovery + learning

---

## 🆘 Getting Help

1. Check `PROJECT_SUMMARY.md` for architecture overview
2. Check `videoscout/README.md` for basic usage
3. Check `videoscout/AGENTIC_LOOP_SETUP.md` for agent details
4. Check logs in `videoscout/logs/`
5. Check database with `sqlite3 videoscout/videoscout.db`

---

## ✅ Success Checklist

- [ ] Python 3.10+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Playwright installed (`playwright install chromium`)
- [ ] YouTube API key configured in `.env`
- [ ] 9router running (for AI features)
- [ ] App starts without errors (`python main.py`)
- [ ] Can add a channel manually
- [ ] Daily Digest scan works
- [ ] Agent discovery runs successfully
- [ ] Database contains data

---

**Ready to start?** Run: `cd videoscout && source venv/bin/activate && python main.py`

