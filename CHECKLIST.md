# ✅ VideoScout - Action Checklist

**Ngày:** 2026-06-30  
**Trạng thái hiện tại:** Documentation Complete, Pending OpenAI SDK

---

## 📋 Immediate Actions (Khi có Internet)

### [ ] Step 1: Install OpenAI SDK
```bash
cd /Users/nvt/Documents/mmo/videoscout
source venv/bin/activate
pip install openai
```

**Verify:**
```bash
python -c "import openai; print(f'✅ OpenAI {openai.__version__}')"
```

---

### [ ] Step 2: Test LLM Client
```bash
cd videoscout
source venv/bin/activate
python << 'PYEOF'
from agents.skills.llm_skills import _call_llm, _get_config

config = _get_config()
print(f"Config: {config}")

response = _call_llm("Say hello in 3 words")
if response:
    print(f"✅ LLM works: {response}")
else:
    print("❌ LLM failed - check Codex API")
PYEOF
```

**Expected:** `✅ LLM works: Hello to you`

---

### [ ] Step 3: Run App
```bash
python main.py
```

**Should see:** Dark-themed PyQt6 window with 6 tabs

---

### [ ] Step 4: Configure Settings
1. Click **⚙️ Settings** tab
2. Check **LLM Configuration** section:
   - Base URL: `http://localhost:20218/api/v1`
   - API Key: `sk-71bdfd45ea19211e-wft2jm-561021e2`
   - Model: `gpt-4o-mini`
3. Click **💾 Save All Settings**
4. Look for: `✅ Settings saved successfully!`

---

### [ ] Step 5: Test Agent Loop
1. Click **🤖 Agent Loop** tab
2. Click **🔍 Run Discovery**
3. Wait 5-10 minutes
4. Check logs for NO errors:
   ```bash
   tail -f videoscout/logs/videoscout_*.log
   ```

**Expected log:**
```
[INFO] orchestrator: === Discovery Cycle Starting ===
[INFO] discover: Discovered X new candidates
[INFO] llm: LLM client created: base_url=http://localhost:20218/api/v1
[INFO] llm: LLM evaluate: ChannelName → score=8 rec=follow
[INFO] orchestrator: Auto-followed X/Y recommended channels
[INFO] orchestrator: === Discovery Cycle Complete ===
```

---

## 📚 Reading Checklist

### [ ] Must Read (Total: 7 min)
- [ ] `START_HERE.md` (1 min) - Overview
- [ ] `FINAL_SUMMARY.md` (3 min) - Complete summary
- [ ] `QUICK_REFERENCE.md` (1 min) - Commands
- [ ] `CHECKLIST.md` (2 min) - This file

### [ ] Should Read (Total: 26 min)
- [ ] `QUICK_START.md` (8 min) - Setup guide
- [ ] `HOW_IT_WORKS.md` (15 min) - Deep dive
- [ ] `FIX_OPENAI_OFFLINE.md` (3 min) - Fixes

### [ ] Nice to Read (Total: 27 min)
- [ ] `PROJECT_SUMMARY.md` (10 min) - Architecture
- [ ] `SUMMARY_CHANGES.md` (5 min) - Changelog
- [ ] `README_DOCUMENTATION.md` (2 min) - Navigation
- [ ] `FIX_LLM_ERROR.md` (5 min) - Troubleshooting
- [ ] `README.md` (5 min) - Harness info

**Total reading time:** ~60 minutes

---

## 🎯 Usage Checklist (Week 1)

### [ ] Day 1: Setup & Explore
- [ ] Install OpenAI SDK
- [ ] Run app successfully
- [ ] Configure Settings
- [ ] Explore all 6 tabs
- [ ] Read `HOW_IT_WORKS.md`

### [ ] Day 2: Manual Mode
- [ ] Go to **🔍 Discovery** tab
- [ ] Add 5 channels manually
- [ ] Go to **📋 Daily Digest** tab
- [ ] Click **Scan Now**
- [ ] See some videos appear

### [ ] Day 3: Agent Discovery
- [ ] Go to **🤖 Agent Loop** tab
- [ ] Click **🔍 Run Discovery**
- [ ] Wait for results (~5-10 min)
- [ ] Check which channels auto-followed
- [ ] Review in **🔍 Discovery** tab

### [ ] Day 4: Monitor & Analyze
- [ ] Check **📊 Analytics** tab
- [ ] Review channel performance
- [ ] Check database:
   ```bash
   sqlite3 videoscout/videoscout.db "SELECT COUNT(*) FROM channels;"
   sqlite3 videoscout/videoscout.db "SELECT COUNT(*) FROM videos;"
   ```

### [ ] Day 5: TikTok Check
- [ ] Go to **🎯 TikTok Check** tab
- [ ] Enter a keyword (e.g., "newjeans fancam")
- [ ] See if already saturated on TikTok
- [ ] Decide if niche is good

### [ ] Day 7: Learning Cycle
- [ ] Go to **🤖 Agent Loop** tab
- [ ] Click **📊 Run Learning**
- [ ] Review suggestions
- [ ] Decide which to apply
- [ ] Edit `agents/memory/strategy.json` if needed

---

## 🔧 Maintenance Checklist (Monthly)

### [ ] Performance Check
- [ ] Check YouTube API quota usage
- [ ] Review logs for errors
- [ ] Check database size
- [ ] Clean old logs if needed

### [ ] Strategy Review
- [ ] Review `agents/memory/channel_outcomes.json`
- [ ] Check which channels performing well
- [ ] Run Learning Agent
- [ ] Apply approved suggestions

### [ ] Data Export
- [ ] Go to **📊 Analytics** tab
- [ ] Export CSV for analysis
- [ ] Review best channels
- [ ] Adjust filters if needed

### [ ] Backup
```bash
# Backup database
cp videoscout/videoscout.db videoscout/videoscout.backup.db

# Backup strategy
cp videoscout/agents/memory/strategy.json videoscout/agents/memory/strategy.backup.json

# Backup .env
cp videoscout/.env videoscout/.env.backup
```

---

## 🐛 Troubleshooting Checklist

### [ ] LLM Not Working
1. [ ] Check Codex API running:
   ```bash
   curl http://localhost:20218/api/v1/models
   ```
2. [ ] Check API key in Settings
3. [ ] Check logs for error details
4. [ ] Read `FIX_OPENAI_OFFLINE.md`

### [ ] No Videos Found
1. [ ] Check filters in Settings
2. [ ] Try broader keywords
3. [ ] Check YouTube API key valid
4. [ ] Check API quota not exceeded

### [ ] Agent Loop Fails
1. [ ] Check LLM is working
2. [ ] Check logs for specific error
3. [ ] Verify Codex API accessible
4. [ ] Try Manual mode instead

### [ ] App Crashes
1. [ ] Check logs: `tail videoscout/logs/*.log`
2. [ ] Check Python errors in terminal
3. [ ] Verify all dependencies installed
4. [ ] Try `pip install -r requirements.txt` again

---

## 📊 Success Metrics Checklist

### [ ] Week 1 Goals
- [ ] 10+ channels added
- [ ] 20+ videos found
- [ ] Agent Loop tested successfully
- [ ] Understand scoring system

### [ ] Month 1 Goals
- [ ] 30+ channels tracked
- [ ] 100+ videos discovered
- [ ] Learning cycle completed
- [ ] Strategy improved based on data

### [ ] Month 3 Goals
- [ ] 50+ channels tracked
- [ ] 500+ videos discovered
- [ ] Autonomous weekly discovery
- [ ] Minimal manual intervention

---

## 🎓 Knowledge Checklist

### [ ] Understanding System
- [ ] Know what Discover Agent does
- [ ] Know what Evaluate Agent does
- [ ] Know what Learn Agent does
- [ ] Understand Self-Improvement Loop

### [ ] Understanding Database
- [ ] Know `channels` table structure
- [ ] Know `videos` table structure
- [ ] Know `channel_outcomes` purpose
- [ ] Can query database with SQL

### [ ] Understanding Scoring
- [ ] Know channel score factors
- [ ] Know video score formula (0-100)
- [ ] Understand why 150-200K views
- [ ] Understand why <50K subs better

### [ ] Understanding Files
- [ ] Know where `.env` is
- [ ] Know where `strategy.json` is
- [ ] Know where logs are
- [ ] Know where database is

---

## ✅ Final Verification

### [ ] Documentation
- [ ] Have 12 documentation files
- [ ] Read at least `START_HERE.md`
- [ ] Know where to find help

### [ ] Code
- [ ] `llm_skills.py` fixed
- [ ] `settings.py` updated
- [ ] `.env` configured
- [ ] Backup files created

### [ ] Configuration
- [ ] YouTube API key set
- [ ] LLM Base URL correct
- [ ] LLM API key correct
- [ ] Model name correct

### [ ] Ready to Use
- [ ] OpenAI SDK installed (pending)
- [ ] App runs without errors (pending)
- [ ] Agent Loop works (pending)
- [ ] Understand how to use

---

## 🚀 Next Action

**Right now:**
```bash
cat START_HERE.md
```

**When internet available:**
```bash
cd videoscout && source venv/bin/activate && pip install openai && python main.py
```

---

**Created:** 2026-06-30 23:21  
**Location:** `/Users/nvt/Documents/mmo/CHECKLIST.md`  
**Status:** 🟡 Pending OpenAI SDK Installation

