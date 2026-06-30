# Cách VideoScout Hoạt Động (How It Works)

## 🎯 Tổng Quan

VideoScout tự động tìm video YouTube phù hợp để reup lên TikTok thông qua hệ thống **3 AI agents** hoạt động độc lập và học hỏi từ kết quả.

---

## 📊 Flow Hoạt Động Chính

```
┌─────────────────────────────────────────────────────────┐
│  USER: Nhập keywords ban đầu (vd: "kpop fancam")       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  1. DISCOVER AGENT - Tìm Channels                       │
│     • Tìm trên YouTube với keywords                     │
│     • Filter: subs < 50K, có upload gần đây             │
│     • Loại bỏ channels đã có trong DB                   │
│     • Output: List 20-50 channels mới                   │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  2. EVALUATE AGENT - Đánh Giá Bằng AI                   │
│     • LLM đọc tên channel + 10 video titles gần nhất    │
│     • Chấm điểm 0-10 (repost potential)                │
│     • Đánh giá niche_fit + copyright risk               │
│     • Recommendation: "follow" hoặc "skip"              │
│     • Output: List channels có điểm + lý do            │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  3. AUTO-FOLLOW - Orchestrator Quyết Định               │
│     • Sắp xếp theo điểm giảm dần                        │
│     • Tự động follow top 10 channels                     │
│     • Lưu vào DB với niche tag                          │
│     • Output: 10 channels mới được theo dõi             │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  4. DAILY SCANNING - Quét Video Hàng Ngày              │
│     • Quét tất cả channels đang follow                  │
│     • Filter videos: 150K-200K views, <30 days, <3min  │
│     • Tính opportunity_score (0-100)                    │
│     • Output: List videos sẵn sàng download            │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  5. LEARN AGENT - Học Từ Kết Quả (Tùy Chọn)           │
│     • Phân tích channels nào cho videos tốt            │
│     • Tìm pattern: subs, views, niche                   │
│     • Đề xuất keywords mới                              │
│     • Đề xuất điều chỉnh filters                       │
│     • Human approval required → Update strategy.json    │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 Chi Tiết 3 Agents

### **1. Discover Agent** 🔍

**File:** `videoscout/agents/discover_agent.py`

**Input:**
```json
{
  "keywords": ["kpop fancam", "idol dance"],
  "filters": {
    "max_subs": 50000,
    "min_uploads_per_month": 4
  }
}
```

**Process:**
1. Đọc `strategy.json` lấy keywords
2. Với mỗi keyword:
   - Gọi YouTube API search
   - Filter theo subscribers, upload frequency
   - Check xem đã có trong DB chưa
3. Gộp tất cả kết quả
4. Sort theo score (subs + views + recency)

**Output:**
```json
[
  {
    "id": "UCxxxxx",
    "name": "KpopDancer123",
    "subscribers": 5000,
    "avg_views": 50000,
    "upload_frequency": 15,
    "score": 85
  }
]
```

**Code Example:**
```python
# videoscout/agents/discover_agent.py
def run() -> list[dict]:
    strategy = _load_strategy()
    keywords = strategy.get("keywords", [])
    
    all_candidates = []
    for kw in keywords:
        channels = discover_channels(kw, filters)
        all_candidates.extend(channels)
    
    return sorted(all_candidates, key=lambda x: x['score'], reverse=True)
```

---

### **2. Evaluate Agent** 🤖

**File:** `videoscout/agents/evaluate_agent.py`

**Input:** List channels từ Discover Agent

**Process:**
1. Với mỗi channel:
   - Fetch 30 videos gần nhất
   - Lấy channel stats (subs, views)
   - Gửi cho LLM prompt:
     ```
     Channel: KpopDancer123
     Subscribers: 5,000
     Recent videos:
     - "NewJeans Hype Boy fancam" (80K views)
     - "IVE Kitsch dance cover" (120K views)
     ...
     
     Evaluate for TikTok repost:
     - niche_fit: Is this kpop/dance content?
     - risk: Copyright risk? (low/medium/high)
     - score: 0-10 repost potential
     - recommendation: follow or skip?
     - reasoning: Why?
     ```
2. LLM trả về JSON
3. Lưu kết quả vào `channel_outcomes`

**Output:**
```json
{
  "id": "UCxxxxx",
  "name": "KpopDancer123",
  "llm": {
    "niche_fit": true,
    "risk": "low",
    "score": 8,
    "recommendation": "follow",
    "reasoning": "Small channel with consistent kpop dance covers, good view counts, low copyright risk"
  }
}
```

**LLM Logic:**
```python
# videoscout/agents/skills/llm_skills.py
def evaluate_channel(channel, videos):
    prompt = f"""
    Channel: {channel['name']}
    Videos: {video_titles}
    
    JSON response: {{
      "niche_fit": bool,
      "risk": "low|medium|high",
      "score": 0-10,
      "recommendation": "follow|skip",
      "reasoning": "..."
    }}
    """
    
    response = llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return json.loads(response.choices[0].message.content)
```

---

### **3. Learn Agent** 📚

**File:** `videoscout/agents/learn_agent.py`

**Chạy Khi Nào?**
- Sau 5-10 discovery cycles
- Hoặc user click "Run Learning" manually

**Process:**

**Step 1: Analyze Outcomes**
```python
def analyze_outcomes():
    outcomes = get_outcomes()  # Từ DB: channel_outcomes table
    
    successful = [o for o in outcomes 
                  if o['outcome'] == 'follow' 
                  and o['videos_found'] > 5]
    
    failed = [o for o in outcomes 
              if o['outcome'] == 'skip']
    
    # Gửi cho LLM tìm patterns
    patterns = summarize_outcomes(outcomes)
    return {
        "patterns": patterns,
        "successful_channels": successful,
        "failed_channels": failed
    }
```

**Step 2: Suggest Improvements**
```python
def suggest_strategy_updates():
    analysis = analyze_outcomes()
    
    # LLM suggest keywords mới dựa trên successful channels
    new_keywords = suggest_keywords(
        analysis['successful_channels'],
        current_keywords
    )
    
    # Tính toán filter adjustments
    successful = analysis['successful_channels']
    avg_subs = mean([ch['subscribers'] for ch in successful])
    
    if avg_subs < current_max_subs * 0.3:
        filter_adjustments = {
            "max_subs": int(current_max_subs * 0.7)
        }
    
    return {
        "keyword_suggestions": new_keywords,
        "filter_adjustments": filter_adjustments,
        "reasoning": "..."
    }
```

**Output (Pending Approval):**
```json
{
  "status": "pending_approval",
  "suggestions": {
    "keyword_suggestions": [
      "newjeans fancam",
      "ive stage",
      "aespa dance"
    ],
    "filter_adjustments": {
      "max_subs": 30000
    },
    "reasoning": "Successful channels avg 5K subs. Lower max_subs to find more similar channels."
  }
}
```

**Step 3: Human Approval → Apply**
```python
# User reviews suggestions in UI, then manually edits:
# videoscout/agents/memory/strategy.json

{
  "keywords": [
    "kpop fancam",          # existing
    "newjeans fancam",      # NEW - approved
    "ive stage"             # NEW - approved
  ],
  "filters": {
    "max_subs": 30000       # UPDATED - approved
  }
}
```

---

## 🗂️ Database Schema

### **channels** - Đang Follow
```sql
CREATE TABLE channels (
    id TEXT PRIMARY KEY,          -- UCxxxxx
    name TEXT,                    -- "KpopDancer123"
    url TEXT,                     -- Full YouTube URL
    niche_tag TEXT,               -- "kpop", "dance", etc
    subscribers INTEGER,          -- 5000
    avg_views INTEGER,            -- 50000
    is_active BOOLEAN,            -- Still scanning?
    last_scanned TIMESTAMP,       -- Last scan time
    added_at TIMESTAMP            -- When added
);
```

### **videos** - Discovered Videos
```sql
CREATE TABLE videos (
    id TEXT PRIMARY KEY,          -- Video ID
    channel_id TEXT,              -- Foreign key
    title TEXT,
    view_count INTEGER,           -- 175000
    upload_date TEXT,
    youtube_url TEXT,
    duration_sec INTEGER,         -- 180 (3 phút)
    thumbnail_url TEXT,
    opportunity_score INTEGER,    -- 0-100
    tiktok_status TEXT,           -- "unknown", "found", "not_found"
    is_used BOOLEAN,              -- Already downloaded?
    found_at TIMESTAMP,
    channel_name TEXT,
    channel_subscribers INTEGER
);
```

### **channel_outcomes** - Agent Performance Tracking
```sql
CREATE TABLE channel_outcomes (
    channel_id TEXT PRIMARY KEY,
    name TEXT,
    subscribers INTEGER,
    videos_found INTEGER,         -- How many good videos?
    avg_video_score REAL,         -- Average opportunity_score
    llm_score INTEGER,            -- LLM's 0-10 score
    llm_recommendation TEXT,      -- "follow" or "skip"
    llm_reasoning TEXT,
    outcome TEXT,                 -- Final decision
    created_at TIMESTAMP
);
```

### **agent_loops** - Execution Logs
```sql
CREATE TABLE agent_loops (
    id INTEGER PRIMARY KEY,
    loop_type TEXT,               -- "discovery", "learning", "full"
    channels_discovered INTEGER,
    channels_evaluated INTEGER,
    channels_recommended INTEGER,
    channels_auto_followed INTEGER,
    status TEXT,                  -- "complete", "failed"
    result_json TEXT,             -- Full JSON result
    created_at TIMESTAMP
);
```

---

## 📈 Scoring Algorithm

### **Channel Score (Discover Phase)**
```python
def calculate_channel_score(channel):
    # Subs: nhỏ hơn = tốt hơn (ít bị report)
    subs_score = 100 - (channel['subscribers'] / 500)
    
    # Views: trung bình càng cao càng tốt
    views_score = min(channel['avg_views'] / 1000, 100)
    
    # Upload frequency: 4+ videos/tháng
    freq_score = min(channel['upload_frequency'] * 5, 100)
    
    total = (subs_score * 0.3) + (views_score * 0.5) + (freq_score * 0.2)
    return int(total)
```

### **Video Opportunity Score (0-100)**
```python
def calculate_opportunity_score(video):
    # Recency: càng mới càng tốt (40 points)
    days_old = (now - video['upload_date']).days
    recency = max(0, 40 - days_old)
    
    # View sweet spot: 175K = max (30 points)
    view_target = 175000
    view_diff = abs(video['view_count'] - view_target)
    view_score = max(0, 30 - (view_diff / 10000))
    
    # Channel size: nhỏ hơn = ít bị report (20 points)
    subs = video['channel_subscribers']
    channel_score = max(0, 20 - (subs / 2500))
    
    # TikTok gap: chưa có trên TikTok = bonus (10 points)
    tiktok_bonus = 10 if video['tiktok_status'] == 'not_found' else 0
    
    return int(recency + view_score + channel_score + tiktok_bonus)
```

---

## 🔧 Agent Memory Files

### **strategy.json** - Current Strategy
```json
{
  "keywords": [
    "kpop fancam",
    "idol dance",
    "newjeans"
  ],
  "filters": {
    "max_subs": 50000,
    "min_views": 150000,
    "max_views": 200000,
    "days_back": 30,
    "max_duration_sec": 180,
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
  },
  "last_updated": "2026-06-30T10:00:00Z"
}
```

### **channel_outcomes.json** - Historical Results
```json
[
  {
    "channel_id": "UCxxxxx",
    "name": "KpopDancer123",
    "subscribers": 5000,
    "videos_found": 15,
    "avg_video_score": 82,
    "llm_evaluation": {
      "score": 8,
      "recommendation": "follow",
      "reasoning": "..."
    },
    "outcome": "follow",
    "timestamp": "2026-06-29T10:00:00Z"
  }
]
```

### **learnings.json** - Discovered Patterns
```json
{
  "patterns": [
    "Channels with 3-10K subs perform best",
    "Fancam content has higher TikTok conversion",
    "Avoid channels with music labels in name"
  ],
  "keyword_suggestions": [
    "newjeans fancam",
    "ive stage"
  ],
  "last_updated": "2026-06-30T10:00:00Z"
}
```

---

## 🎬 Example Use Case

### **Week 1: Khởi Động**
```
1. User nhập keywords: ["kpop fancam", "idol dance"]
2. Click "Run Discovery"
3. Discover Agent → tìm 50 channels
4. Evaluate Agent → LLM chấm điểm → 12 channels "follow"
5. Auto-follow top 10
6. Daily Digest quét 10 channels → tìm 25 videos
7. Copy URLs → download → upload TikTok
```

### **Week 2: Thu Thập Dữ Liệu**
```
- Discovery chạy 2 lần nữa
- Total: 30 channels followed
- 50 videos downloaded
- Performance tracking: 8/10 channels tốt, 2/10 kém
```

### **Week 3: Learning Cycle**
```
1. Click "Run Learning"
2. Learn Agent phân tích:
   - Channels 3-8K subs cho videos tốt nhất
   - Pattern: "newjeans" keyword chưa thử
3. Suggestions:
   - Add keywords: ["newjeans fancam", "ive stage"]
   - Lower max_subs: 50K → 30K
4. User approve → Edit strategy.json
5. Next discovery tìm channels tốt hơn
```

### **Month 2+: Tự Động Hóa**
```
- Weekly discovery (auto-follow top 10)
- Daily digest (quét videos)
- Monthly learning (cải thiện strategy)
- Ngày càng ít cần can thiệp thủ công
```

---

## 🐛 Lỗi Hiện Tại

### **Vấn Đề:**
```
Client.__init__() got an unexpected keyword argument 'proxies'
```

**Root Cause:**
- OpenAI Python SDK version mới không hỗ trợ `proxies` argument
- Code có thể đang pass thừa parameters

**Fix:**
```python
# videoscout/agents/skills/llm_skills.py

# BEFORE (có thể có lỗi)
def _client() -> OpenAI:
    return OpenAI(
        base_url=_BASE_URL, 
        api_key=_API_KEY,
        proxies=None  # ← LỖI: argument không hợp lệ
    )

# AFTER (đơn giản hóa)
def _client() -> OpenAI:
    return OpenAI(
        base_url=_BASE_URL,
        api_key=_API_KEY
    )
```

---

## ✅ Next Steps

1. **Fix LLM client** (xem file tiếp theo)
2. **Kiểm tra 9router đang chạy:**
   ```bash
   curl http://localhost:20128/v1/models
   ```
3. **Test lại Discovery cycle**
4. **Kiểm tra logs** để verify LLM hoạt động

---

**File này giải thích:** Cách hệ thống hoạt động từ đầu đến cuối, flow của 3 agents, database schema, scoring logic, và use case thực tế.

