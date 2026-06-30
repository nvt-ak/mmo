# Project Summary - MMO Repository

**Date:** 2026-06-30  
**Location:** `/Users/nvt/Documents/mmo`

---

## 🎯 Overview

This repository contains **two main projects**:

1. **Repository Harness** - A framework for AI-assisted software development
2. **VideoScout** - A desktop application for finding YouTube videos to repost on TikTok

---

## 📁 Repository Structure

```
mmo/
├── docs/                          # Harness documentation
│   ├── HARNESS.md                 # Main harness guide
│   ├── FEATURE_INTAKE.md          # Work classification
│   ├── ARCHITECTURE.md            # Architecture discovery
│   ├── TEST_MATRIX.md             # Validation expectations
│   ├── TOOL_REGISTRY.md           # External tool management
│   ├── product/                   # Product contracts
│   ├── stories/                   # Story packets
│   ├── decisions/                 # Decision records
│   └── templates/                 # Reusable templates
│
├── scripts/                       # Harness tooling
│   ├── bin/
│   │   └── harness-cli            # Rust CLI tool (macOS/Linux)
│   └── schema/                    # Database schema
│
├── videoscout/                    # Main application
│   ├── agents/                    # AI agent system
│   │   ├── memory/                # Agent strategy & learnings
│   │   ├── skills/                # Reusable agent skills
│   │   ├── discover_agent.py      # Channel discovery
│   │   ├── evaluate_agent.py      # LLM evaluation
│   │   ├── learn_agent.py         # Pattern learning
│   │   └── orchestrator.py        # Agent coordinator
│   │
│   ├── ui/                        # PyQt6 desktop interface
│   │   ├── main_window.py         # Main app window
│   │   ├── agent_tab.py           # Agent loop controls
│   │   ├── channel_discovery.py   # Channel management
│   │   ├── daily_digest.py        # Video discovery
│   │   ├── tiktok_checker.py      # TikTok keyword checker
│   │   ├── analytics.py           # Performance analytics
│   │   └── settings.py            # Configuration
│   │
│   ├── services/                  # Business logic
│   │   ├── youtube_service.py     # YouTube API wrapper
│   │   ├── tiktok_service.py      # TikTok scraper
│   │   ├── scanner_service.py     # Video scanner
│   │   ├── scheduler_service.py   # Background tasks
│   │   └── channel_discovery.py   # Channel discovery
│   │
│   ├── database/                  # Data layer
│   │   ├── db.py                  # SQLite connection
│   │   ├── models.py              # Data models
│   │   └── db_migrations.py       # Schema migrations
│   │
│   ├── utils/                     # Utilities
│   │   ├── logger.py              # Logging
│   │   └── export.py              # Data export
│   │
│   ├── main.py                    # Application entry point
│   ├── requirements.txt           # Python dependencies
│   ├── videoscout.db              # SQLite database
│   └── .env                       # Configuration (API keys)
│
├── AGENTS.md                      # Agent instructions
├── README.md                      # Main readme
└── harness.db                     # Harness SQLite database
```

---

## 🚀 Project 1: Repository Harness

### Purpose
A framework that transforms any software repository into an "agent-ready workspace" for AI coding assistants (Claude Code, Codex, Cursor, etc.).

### Key Concept
> "Coding agents don't only need better prompts. They need better repositories."

### Core Components

#### 1. **AGENTS.md**
- Stable entry point for AI agents
- Contains project-specific instructions
- Links to Harness documentation

#### 2. **Feature Intake Process**
- Classifies work into: Tiny, Normal, High-Risk
- Ensures proper planning before implementation
- Breaks large requests into story-sized work

#### 3. **Documentation Structure**
- `docs/product/` - Product contracts
- `docs/stories/` - Story packets (work units)
- `docs/decisions/` - Architecture decisions
- `docs/templates/` - Reusable templates

#### 4. **Harness CLI**
- Rust-based command-line tool
- Manages operational data in SQLite
- Commands for stories, decisions, traces, audits

#### 5. **Tool Registry**
- Registers external tools as capability providers
- Tools can be: CLI, binary, MCP, skill, HTTP
- Graceful degradation when tools are absent

### Installation
```bash
# Install into any project
curl -fsSL "https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --yes
```

### Key Features
- **Human-agent collaboration model**
- **Risk-based work classification**
- **Validation expectations (test matrix)**
- **Decision capture for future agents**
- **Durable operational layer (SQLite)**

---

## 🎬 Project 2: VideoScout

### Purpose
Desktop application to find and evaluate YouTube videos for reposting to TikTok DE (Deutschland/Germany market).

### Target Use Case
Finding viral-potential videos from small channels that haven't been discovered on TikTok yet.

### Technology Stack
- **Language:** Python 3.10
- **UI:** PyQt6 (dark theme desktop app)
- **Database:** SQLite
- **APIs:** YouTube Data API v3, TikTok web scraper
- **Browser:** Playwright (Chromium)
- **AI:** OpenAI-compatible LLM via 9router
- **Scheduler:** APScheduler

### Key Features

#### 1. **AI Agent System** 🤖
Three-agent loop for autonomous channel discovery:

**Discover Agent**
- Searches YouTube by strategy keywords
- Filters by: subscribers, views, upload frequency
- Returns new candidate channels

**Evaluate Agent**
- Uses LLM to analyze video titles/content
- Scores 0-10 for TikTok repost potential
- Provides follow/skip recommendation + reasoning

**Learn Agent**
- Analyzes historical outcomes
- Identifies success patterns
- Suggests new keywords + filter adjustments
- Human approval required before applying

**Orchestrator**
- Coordinates Discover → Evaluate → Learn
- Auto-follows top N recommended channels
- Logs all executions to database

#### 2. **Channel Discovery** 🔍
- Add YouTube channels manually
- Tag channels by niche (kpop, dance, etc.)
- Track channel statistics
- Automatic scanning of tracked channels

#### 3. **Daily Digest** 📋
- Scans all tracked channels for new videos
- Filters by configurable criteria:
  - Views: 150K – 200K (sweet spot)
  - Upload date: Last 30 days
  - Channel size: < 50K subscribers
  - Duration: < 3 minutes
- Scores videos 0-100 based on opportunity
- Copy URLs for download pipeline

#### 4. **TikTok Keyword Checker** 🎯
- Checks keyword saturation on TikTok
- Verifies if niche is already crowded
- Uses Playwright to scrape TikTok search

#### 5. **Analytics** 📊
- Performance metrics
- Channel statistics
- Video discovery trends

#### 6. **Settings** ⚙️
- YouTube API key configuration
- Filter adjustments (views, subs, duration)
- Scan schedule (hourly/daily)
- Agent strategy configuration

### Scoring Algorithm

Videos scored 0-100 based on:
- **Recency:** 40 points (newer = higher)
- **View sweet spot:** 30 points (closer to 175K = max)
- **Channel size:** 20 points (smaller = less copyright risk)
- **TikTok gap:** 10 points (not on TikTok = bonus)

### Database Schema

**Tables:**
- `channels` - Tracked YouTube channels
- `videos` - Discovered videos
- `settings` - App configuration
- `channel_outcomes` - Agent performance tracking
- `agent_loops` - Agent execution logs

**Models:**
```python
@dataclass
class Channel:
    id: str
    name: str
    url: str
    niche_tag: str
    subscribers: int
    avg_views: int
    is_active: bool
    last_scanned: Optional[str]
    added_at: Optional[str]

@dataclass
class Video:
    id: str
    channel_id: str
    title: str
    view_count: int
    upload_date: str
    youtube_url: str
    duration_sec: int
    thumbnail_url: str
    opportunity_score: int
    tiktok_status: str
    is_used: bool
    found_at: Optional[str]
    channel_name: Optional[str]
    channel_subscribers: Optional[int]
```

### Dependencies

```txt
PyQt6==6.7.0                      # Desktop UI framework
google-api-python-client==2.130.0 # YouTube API
playwright==1.44.0                # TikTok scraper
apscheduler==3.10.4              # Background scheduler
requests==2.32.3                  # HTTP client
python-dotenv==1.0.1             # Environment config
pyinstaller==6.6.0               # EXE builder
openai==1.54.3                   # LLM client
```

### Configuration (.env)

```bash
# YouTube API
YOUTUBE_API_KEY=your_key_here

# LLM (9router)
LLM_BASE_URL=http://localhost:20128/v1
LLM_API_KEY=sk-local
LLM_MODEL=gpt-4o-mini
```

### Usage Workflow

1. **Setup**
   - Install dependencies: `pip install -r requirements.txt`
   - Install Playwright: `playwright install chromium`
   - Configure API keys in `.env`
   - Start 9router for LLM: `9router`

2. **Add Channels**
   - Go to **Channels** tab
   - Add YouTube channel URLs
   - Tag by niche (kpop, dance, etc.)

3. **Run Agent Loop** (Autonomous)
   - Go to **🤖 Agent Loop** tab
   - Click **🔍 Run Discovery** (finds + evaluates new channels)
   - Wait 5-10 minutes
   - Top 10 channels auto-followed
   - Click **📊 Run Learning** after several cycles
   - Review and approve suggestions

4. **Manual Scanning**
   - Go to **Daily Digest** tab
   - Click **Scan Now**
   - Review scored videos
   - Copy URLs for download

5. **Check TikTok Saturation**
   - Go to **TikTok Check** tab
   - Enter keyword
   - See if niche is oversaturated

6. **Build Executable**
   ```bash
   pyinstaller --onefile --windowed --name VideoScout \
     --add-data "*.env;." main.py
   ```

### Agent Memory Files

Located in `videoscout/agents/memory/`:

**strategy.json**
```json
{
  "keywords": ["kpop fancam", "idol dance", "newjeans"],
  "filters": {
    "max_subs": 50000,
    "min_views": 150000,
    "max_views": 200000,
    "days_back": 30,
    "niche_tag": "kpop"
  },
  "weights": {
    "recency": 0.4,
    "view_sweet_spot": 0.3,
    "channel_size": 0.2,
    "tiktok_gap": 0.1
  },
  "llm": {
    "enabled": true
  }
}
```

**channel_outcomes.json**
```json
[
  {
    "channel_id": "UCxxx",
    "name": "KpopDancer123",
    "subscribers": 5000,
    "videos_found": 15,
    "avg_video_score": 75,
    "llm_evaluation": {...},
    "outcome": "follow",
    "timestamp": "2026-06-30T10:00:00Z"
  }
]
```

**learnings.json**
```json
{
  "patterns": "Channels with 3-10K subs perform best...",
  "keyword_suggestions": ["ive fancam", "aespa stage"],
  "last_updated": "2026-06-30T10:30:00Z"
}
```

### Self-Improvement Loop

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

---

## 🔑 Key Files Reference

### Harness
- `AGENTS.md` - Agent entry point
- `docs/HARNESS.md` - Framework guide
- `docs/FEATURE_INTAKE.md` - Work classification
- `scripts/bin/harness-cli` - CLI tool

### VideoScout
- `videoscout/main.py` - Application entry
- `videoscout/agents/orchestrator.py` - Agent coordinator
- `videoscout/ui/main_window.py` - Main window
- `videoscout/database/db.py` - Database layer
- `videoscout/.env` - Configuration

---

## 🎯 Next Steps

### For Harness
1. Install into a real project
2. Create product contracts
3. Define validation matrix
4. Capture architecture decisions

### For VideoScout
1. Get YouTube API key
2. Install dependencies
3. Configure `.env`
4. Start 9router
5. Run application
6. Add first channels
7. Test agent loop

---

## 📚 Documentation Links

- Harness README: `README.md`
- VideoScout README: `videoscout/README.md`
- Agent Setup: `videoscout/AGENTIC_LOOP_SETUP.md`
- Harness Guide: `docs/HARNESS.md`
- Feature Intake: `docs/FEATURE_INTAKE.md`

---

## 🛠️ Tech Stack Summary

| Component | Technology |
|-----------|------------|
| **Harness CLI** | Rust |
| **App Language** | Python 3.10 |
| **Desktop UI** | PyQt6 |
| **Database** | SQLite |
| **YouTube API** | Google API Python Client |
| **Web Scraping** | Playwright (Chromium) |
| **AI/LLM** | OpenAI-compatible (9router) |
| **Scheduler** | APScheduler |
| **Build Tool** | PyInstaller |

---

## 📊 Project Status

- **Harness:** Framework complete, ready for adoption
- **VideoScout:** Fully functional with AI agent system
- **Integration:** Both projects coexist in same repository
- **Documentation:** Comprehensive guides available

