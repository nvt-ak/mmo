# ⚡ VideoScout Quick Reference Card

**Ngày:** 2026-06-30 | **Thời gian:** 23:18 (GMT+7)

---

## 🎯 ONE-LINER COMMANDS

```bash
# Start app
cd videoscout && source venv/bin/activate && python main.py

# Fix OpenAI (when internet available)
pip install openai

# Check logs
tail -f videoscout/logs/videoscout_*.log

# Check database
sqlite3 videoscout/videoscout.db "SELECT COUNT(*) FROM channels;"

# Test LLM
python -c "from agents.skills.llm_skills import _call_llm; print(_call_llm('test'))"
```

---

## 📂 IMPORTANT FILES

| File | Purpose | Edit? |
|------|---------|-------|
| `videoscout/.env` | Configuration | ✅ Yes |
| `videoscout/agents/memory/strategy.json` | Agent keywords | ✅ Yes |
| `videoscout/videoscout.db` | Database | ❌ No |
| `videoscout/agents/skills/llm_skills.py` | LLM client | ⚠️ Fixed |
| `videoscout/ui/settings.py` | Settings UI | ⚠️ Updated |

---

## ⚙️ CONFIGURATION

### .env File:
```bash
YOUTUBE_API_KEY=AIzaSyA1-ykZSELbXqXRbllpzIrTtzeTCU_6zAA
LLM_BASE_URL=http://localhost:20218/api/v1
LLM_API_KEY=sk-71bdfd45ea19211e-wft2jm-561021e2
LLM_MODEL=gpt-4o-mini
```

### Strategy File:
```bash
# Edit keywords:
nano videoscout/agents/memory/strategy.json

# Location:
videoscout/agents/memory/strategy.json
```

---

## 🤖 3 AGENTS EXPLAINED (30 seconds)

| Agent | What | Input | Output | Time |
|-------|------|-------|--------|------|
| **Discover** | Find channels | Keywords | 20-50 channels | 5 min |
| **Evaluate** | Score channels | Channels | 0-10 ratings | 30 sec |
| **Learn** | Improve strategy | Outcomes | Suggestions | 5 sec |

**Flow:** Keywords → Discover → Evaluate → Auto-follow top 10 → Daily Scan → Learn → Repeat

---

## 📊 SCORING

### Channel Score:
- Small subs (< 50K) = Good (less copyright)
- High avg views = Good
- Frequent uploads = Good

### Video Score (0-100):
- 🕐 Recency: 40 pts (newer = better)
- 👁️ Views: 30 pts (175K = perfect)
- 📺 Channel: 20 pts (smaller = better)
- 🎵 TikTok: 10 pts (not on TikTok = bonus)

---

## 🔧 COMMON TASKS

### Add YouTube API Key:
1. Settings tab
2. YouTube API section
3. Paste key
4. Save

### Configure LLM:
1. Settings tab
2. LLM Configuration section
3. Base URL: `http://localhost:20218/api/v1`
4. API Key: `sk-71bdfd45ea19211e-wft2jm-561021e2`
5. Save

### Check Database:
```bash
sqlite3 videoscout/videoscout.db << 'SQL'
.mode column
.headers on
SELECT name, subscribers, is_active FROM channels LIMIT 10;
SELECT COUNT(*) as total_videos FROM videos;
SQL
```

### View Agent Memory:
```bash
cat videoscout/agents/memory/strategy.json | python -m json.tool
cat videoscout/agents/memory/channel_outcomes.json | python -m json.tool
```

---

## 🐛 TROUBLESHOOTING (30 seconds)

| Problem | Solution |
|---------|----------|
| LLM error | `pip install openai` |
| No internet | Use Manual mode (works without LLM) |
| YouTube quota | Wait till midnight PT or new API key |
| No videos | Check filters in Settings |
| App crash | Check logs: `tail videoscout/logs/*.log` |

---

## 📚 DOCUMENTATION MAP

| I want to... | Read this |
|--------------|-----------|
| Setup quickly | `QUICK_START.md` |
| Understand system | `HOW_IT_WORKS.md` |
| See architecture | `PROJECT_SUMMARY.md` |
| Fix LLM error | `FIX_OPENAI_OFFLINE.md` |
| See all changes | `SUMMARY_CHANGES.md` |
| Navigate docs | `README_DOCUMENTATION.md` |
| Quick commands | `QUICK_REFERENCE.md` (this file) |

---

## 🎮 WORKFLOWS

### Manual Mode (No AI):
```
Add channels → Daily Digest → Scan → Copy URLs → Done
```

### AI Mode (Full Auto):
```
Agent Loop → Run Discovery → Auto-follow top 10 → Done
```

### Hybrid Mode (Best):
```
Agent Discovery (weekly) → Review channels → Daily Digest → Agent Learning (monthly)
```

---

## 📈 PERFORMANCE

| Task | Time | API Units |
|------|------|-----------|
| Add channel | 2 sec | 1 |
| Scan 10 channels | 30 sec | 10 |
| Discovery (50 channels) | 5-10 min | 200 |
| Evaluation (10 channels) | 30 sec | 0 (LLM) |
| Learning | 5 sec | 0 |

**Daily Budget:** 300 units / 10,000 quota = Safe ✅

---

## 🔑 KEYBOARD SHORTCUTS (In App)

| Tab | Shortcut |
|-----|----------|
| Agent Loop | First in nav |
| Discovery | Second |
| Daily Digest | Third |
| TikTok Check | Fourth |
| Analytics | Fifth |
| Settings | Sixth |

---

## 💡 PRO TIPS

1. **Start small:** 5-10 channels first
2. **Tag niches:** Use consistent tags (kpop, dance)
3. **Check TikTok:** Before committing to niche
4. **Weekly discovery:** Run agent loop once/week
5. **Monthly learning:** After accumulating data
6. **Backup strategy:** Before experiments
7. **Monitor quota:** Check YouTube API console
8. **Export data:** Use Analytics for CSV

---

## ⚠️ CURRENT STATUS

### ✅ Working:
- Manual mode
- Settings UI
- Database
- Logs

### ❌ Needs Fix:
- OpenAI SDK (no internet)
- Agent Loop (depends on OpenAI)

### 📝 Action:
```bash
pip install openai  # When internet available
```

---

## 🚀 GETTING STARTED (60 seconds)

```bash
# 1. Navigate
cd /Users/nvt/Documents/mmo/videoscout

# 2. Activate venv
source venv/bin/activate

# 3. Install OpenAI (if not done)
pip install openai

# 4. Run
python main.py

# 5. In app:
# - Settings → Configure LLM
# - Discovery → Add channels
# - Agent Loop → Run Discovery
```

---

## 📞 HELP

**Stuck?** Check these files in order:
1. `QUICK_REFERENCE.md` (this file) - 1 min
2. `QUICK_START.md` - 5 min
3. `FIX_OPENAI_OFFLINE.md` - 3 min
4. `HOW_IT_WORKS.md` - 15 min

**Still stuck?** Check logs:
```bash
ls -lt videoscout/logs/ | head -5
tail -100 videoscout/logs/videoscout_*.log
```

---

## 🎯 SUCCESS METRICS

### After 1 week:
- [ ] 10+ channels added
- [ ] 20+ videos found
- [ ] Agent loop tested
- [ ] Understand scoring

### After 1 month:
- [ ] 30+ channels
- [ ] 100+ videos
- [ ] Learning cycle done
- [ ] Strategy improved

### After 3 months:
- [ ] 50+ channels
- [ ] 500+ videos
- [ ] Self-improving loop
- [ ] Minimal manual work

---

## 🔗 QUICK LINKS

**Config:**
- `.env`: `/Users/nvt/Documents/mmo/videoscout/.env`
- Strategy: `/Users/nvt/Documents/mmo/videoscout/agents/memory/strategy.json`

**Logs:**
- Location: `/Users/nvt/Documents/mmo/videoscout/logs/`

**Database:**
- File: `/Users/nvt/Documents/mmo/videoscout/videoscout.db`

**Docs:**
- All in: `/Users/nvt/Documents/mmo/`

---

**💡 Remember:** This is a QUICK reference. For details, read the full docs!

**🚀 Start here:** `cd videoscout && python main.py`

