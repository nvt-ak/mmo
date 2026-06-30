# VideoScout — Product Requirements Document

**Version:** 0.1  
**Date:** 2026-06-30  
**Author:** brainstorm session  
**Status:** Draft

---

## 1. Bối Cảnh & Mục Tiêu

### 1.1 Business Context

Model đang được validate:
- Mua TikTok accounts DE (Đức) ~2,500 VNĐ/account
- Warm up accounts → đủ điều kiện TikTok Creator Rewards Beta (DE market)
- Điều kiện qualify: **10K followers + 150K-200K views/30 ngày**
- Revenue sau qualify: ~$47/account/tháng
- 15-16 accounts active = ~$700/tháng
- Chi phí vận hành: ~$6/tháng → margin ~99%

### 1.2 Vấn Đề Cần Giải Quyết

Toàn bộ pipeline đã được automate NGOẠI TRỪ:

```
❌ Tìm channels/videos phù hợp trên YouTube  ← BOTTLENECK
❌ Đánh giá keyword nào chưa bão hòa trên TikTok DE
❌ Track channel nào đang có content tốt để follow
✅ Download + process video (đã có)
✅ Upload lên TikTok (đã có code)
✅ Account management + progress tracking (bạn bạn đã build)
```

### 1.3 Mục Tiêu Của Tool

> Tìm được video YouTube phù hợp để reup TikTok DE **nhanh nhất có thể**, thay thế hoàn toàn việc ngồi scroll YouTube thủ công hàng ngày.

---

## 2. User & Use Case

### 2.1 Primary User

**Profile:** MMO-er đang chạy TikTok Creator Rewards Beta (DE market)
- Có 50-200 TikTok accounts đang nuôi
- Upload 2 videos/ngày/account
- Niche: Idol Kpop, entertainment US/global
- Cần tìm video mới mỗi ngày để upload

### 2.2 Core Use Case

```
Mỗi sáng:
1. Mở VideoScout
2. Xem list video đề xuất hôm nay
3. Review nhanh, chọn video muốn clone
4. Bấm "Export" → lấy URL list để đưa vào download pipeline
5. Đóng app, tiếp tục workflow bình thường
```

**Time target:** Từ mở app → có list video = < 5 phút (hiện tại: 30-60 phút thủ công)

---

## 3. Features

### 3.1 Module 1: Channel Manager

**Mục đích:** Quản lý danh sách YouTube channels đang theo dõi

```
Chức năng:
- Add channel (by URL hoặc Channel ID)
- Tag channel theo niche (Kpop, Idol, Entertainment...)
- Enable/Disable channel (tạm dừng monitor)
- Xem stats channel: subscribers, avg views, upload frequency
- Auto-discover: từ 1 channel → suggest related channels cùng niche
```

**Data lưu:**
```
channel_id, name, url, niche_tag, subscribers, 
avg_views_per_video, upload_frequency, is_active, added_date
```

### 3.2 Module 2: Video Scanner

**Mục đích:** Tự động quét videos mới từ channels đang theo dõi, filter theo tiêu chí

**Filters cứng (không đổi):**
```
✓ Views: 150,000 - 200,000
✓ Upload date: trong 30 ngày gần nhất
✓ Channel subscribers: < 50,000
✓ Video duration: phù hợp với Short format (< 3 phút)
```

**Filters mềm (user tùy chỉnh):**
```
- View range: có thể adjust (default 150K-200K)
- Date range: có thể adjust (default 30 ngày)
- Channel size: có thể adjust (default <50K)
- Exclude keywords trong title
- Include keywords trong title
```

**Scoring Algorithm:**
```python
score = (
    recency_score      # video càng mới càng cao (max 40 điểm)
  + view_sweet_spot    # càng gần 175K (midpoint) càng cao (max 30 điểm)
  + channel_small      # channel càng nhỏ càng ít bị report (max 20 điểm)
  + tiktok_gap         # chưa có trên TikTok DE = bonus (max 10 điểm)
)
# Total: 0-100
```

**Output mỗi video:**
```
- Title, Channel name, Channel subs
- View count, Upload date
- YouTube URL
- Opportunity Score (0-100)
- TikTok status: "Not found" / "Few videos" / "Saturated"
- Thumbnail preview
```

### 3.3 Module 3: TikTok Saturation Checker

**Mục đích:** Check keyword/topic này trên TikTok DE đã nhiều người làm chưa

**Cách hoạt động:**
```
Input: keyword (VD: "aespa winter", "newjeans hanni")
Process: 
  - Search TikTok bằng keyword
  - Đếm số video trong 7 ngày gần nhất
  - Estimate engagement rate
Output:
  🟢 FRESH    < 20 videos/7 ngày  → cơ hội tốt
  🟡 MEDIUM   20-100 videos/7 ngày → còn được
  🔴 SATURATED > 100 videos/7 ngày → tránh
```

### 3.4 Module 4: Daily Digest

**Mục đích:** Tổng hợp kết quả mỗi sáng thành actionable list

```
Layout:
┌─────────────────────────────────────────────────┐
│  VideoScout — Daily Digest  📅 30/06/2026       │
│  Scanned: 847 videos | Found: 23 opportunities  │
├─────────────────────────────────────────────────┤
│ 🔥 TOP PICKS HÔM NAY                           │
│                                                 │
│ #1  Score: 94  🟢 FRESH                        │
│     "aespa Winter Fancam 4K MAMA 2025"          │
│     👤 KpopFancam4K (23K subs)                 │
│     👁 178,432 views  📅 3 ngày trước           │
│     🔗 [Copy URL]  [Mark as Used]              │
│                                                 │
│ #2  Score: 87  🟢 FRESH                        │
│     "NewJeans Hanni Solo Stage"                 │
│     👤 KoreanIdolClips (31K subs)              │
│     👁 165,891 views  📅 7 ngày trước           │
│     🔗 [Copy URL]  [Mark as Used]              │
│                                                 │
│ ... (20 videos total)                           │
├─────────────────────────────────────────────────┤
│ [Export All URLs]  [Export Top 10]  [Refresh]  │
└─────────────────────────────────────────────────┘
```

### 3.5 Module 5: History & Analytics

**Mục đích:** Track videos đã dùng, channel nào đang cho content tốt

```
- Lịch sử videos đã mark as used
- Channel nào cung cấp nhiều video tốt nhất
- Niche nào đang có nhiều opportunity nhất
- Trend: opportunity đang tăng hay giảm theo tuần
```

---

## 4. Technical Architecture

### 4.1 Tech Stack

```
Language:     Python 3.11+
UI Framework: PyQt6 (desktop app, cross-platform)
Database:     SQLite (local, không cần server)
APIs:         YouTube Data API v3 (Google Cloud, free tier)
Scraping:     Playwright (TikTok saturation check)
Scheduler:    APScheduler (auto-scan mỗi sáng)
Packaging:    PyInstaller (build .exe Windows)
```

### 4.2 Tại Sao PyQt6

```
✓ Native desktop feel trên Windows
✓ Không cần internet để chạy UI
✓ Data local hoàn toàn, không upload lên đâu
✓ Build thành .exe dễ dàng với PyInstaller
✓ Python ecosystem: dùng lại được requests, playwright, etc.
```

### 4.3 Project Structure

```
videoscout/
├── main.py                    # Entry point
├── config.py                  # API keys, settings
├── database/
│   ├── db.py                  # SQLite connection, migrations
│   └── models.py              # Channel, Video, ScanResult models
├── services/
│   ├── youtube_service.py     # YouTube Data API v3 calls
│   ├── tiktok_service.py      # TikTok scraper (Playwright)
│   ├── scanner_service.py     # Main scan logic + scoring
│   └── scheduler_service.py   # Auto-scan cron
├── ui/
│   ├── main_window.py         # Main window layout
│   ├── channel_manager.py     # Module 1 UI
│   ├── video_scanner.py       # Module 2 UI
│   ├── daily_digest.py        # Module 4 UI
│   └── analytics.py           # Module 5 UI
├── utils/
│   ├── export.py              # Export URLs to clipboard/file
│   └── helpers.py             # Common utilities
├── requirements.txt
└── README.md
```

### 4.4 Database Schema

```sql
-- Channels đang theo dõi
CREATE TABLE channels (
    id              TEXT PRIMARY KEY,  -- YouTube channel ID
    name            TEXT NOT NULL,
    url             TEXT NOT NULL,
    niche_tag       TEXT,              -- "kpop", "idol", "entertainment"
    subscribers     INTEGER,
    avg_views       INTEGER,
    is_active       BOOLEAN DEFAULT 1,
    last_scanned    TIMESTAMP,
    added_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Videos đã scan được
CREATE TABLE videos (
    id              TEXT PRIMARY KEY,  -- YouTube video ID
    channel_id      TEXT REFERENCES channels(id),
    title           TEXT NOT NULL,
    view_count      INTEGER,
    upload_date     DATE,
    duration_sec    INTEGER,
    thumbnail_url   TEXT,
    youtube_url     TEXT NOT NULL,
    opportunity_score INTEGER,         -- 0-100
    tiktok_status   TEXT,              -- "fresh", "medium", "saturated"
    is_used         BOOLEAN DEFAULT 0, -- đã mark as used chưa
    found_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lịch sử scan
CREATE TABLE scan_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scanned_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    channels_scanned INTEGER,
    videos_found    INTEGER,
    top_score       INTEGER
);

-- TikTok keyword cache (tránh spam check)
CREATE TABLE tiktok_cache (
    keyword         TEXT PRIMARY KEY,
    video_count_7d  INTEGER,
    status          TEXT,              -- "fresh", "medium", "saturated"
    checked_at      TIMESTAMP
);
```

### 4.5 YouTube API Usage

```python
# Quota estimate (free tier: 10,000 units/ngày)
# search.list = 100 units/call
# videos.list = 1 unit/call
# channels.list = 1 unit/call

# Với 50 channels:
# - videos.list per channel = 50 × 1 = 50 units
# - detail lookup cho filtered videos = ~20 × 1 = 20 units
# Total per scan: ~70-100 units
# Scans per day với free tier: ~100 scans → dư dùng
```

### 4.6 TikTok Saturation Check

```python
# Dùng Playwright headless
# Search TikTok by keyword
# Parse số video results trong 7 ngày
# Cache result 6 giờ để tránh over-request

# Không cần TikTok login
# Search public results là đủ
```

---

## 5. UI/UX

### 5.1 Layout Chính

```
┌─────────────────────────────────────────────────────┐
│  VideoScout                          [_] [□] [X]   │
├──────────┬──────────────────────────────────────────┤
│          │                                          │
│ 📋 Daily │         Main Content Area               │
│  Digest  │                                          │
│          │                                          │
│ 📺 Channels│                                        │
│  Manager │                                          │
│          │                                          │
│ 🔍 Scanner│                                        │
│          │                                          │
│ 📊 Analytics│                                      │
│          │                                          │
│ ⚙️ Settings│                                       │
│          │                                          │
└──────────┴──────────────────────────────────────────┘
```

### 5.2 Settings

```
- YouTube API Key
- Scan schedule: mỗi X giờ (default: 6AM hàng ngày)
- Default filters (view range, date range, channel size)
- Notification: Windows notification khi scan xong
- Export format: plain URLs / CSV / JSON
```

---

## 6. Build & Release

### 6.1 Development

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# Run development
python main.py

# Build Windows executable
pyinstaller --onefile --windowed --name VideoScout main.py
```

### 6.2 Requirements.txt

```
PyQt6==6.7.0
google-api-python-client==2.130.0
playwright==1.44.0
apscheduler==3.10.4
requests==2.32.3
python-dotenv==1.0.1
pyinstaller==6.6.0
```

---

## 7. Phased Rollout

### Phase 1 — MVP (2 tuần)
```
✓ Channel Manager: add/remove channels
✓ Video Scanner: filter theo 3 tiêu chí chính
✓ Daily Digest: list video với score
✓ Export URLs
✓ SQLite local storage
Goal: Bạn bạn dùng được thay thế scroll thủ công
```

### Phase 2 — Validate (tuần 3-4)
```
✓ TikTok Saturation Checker
✓ Auto-scan scheduler
✓ Windows notification
✓ Analytics cơ bản
Goal: Confirm tool tiết kiệm >30 phút/ngày
```

### Phase 3 — Productize (tháng 2)
```
✓ Packaging thành .exe
✓ License key system (nếu muốn bán)
✓ Auto-update mechanism
✓ Multi-user support
Goal: Có thể bán cho MMO-ers khác $20-30/tháng
```

---

## 8. Risks & Mitigations

| Risk | Khả năng | Mitigation |
|------|----------|------------|
| YouTube API quota hết | Thấp | Cache aggressively, 10K units/ngày là đủ |
| TikTok block Playwright | Trung bình | Rotate user agents, add delays |
| TikTok DE policy thay đổi | Cao | Tool vẫn useful cho bất kỳ niche/market nào |
| YouTube thay đổi layout | Thấp | Dùng official API, không scrape |

---

## 9. Success Metrics

```
Phase 1 done khi:
□ Bạn bạn confirm: tìm video < 5 phút/ngày (hiện tại 30-60 phút)
□ Accuracy: >80% videos trong list thỏa đủ 3 tiêu chí
□ Zero false positives: không có video đã bị reup nhiều

Phase 2 done khi:
□ TikTok check accuracy > 70%
□ Auto-scan chạy ổn định 7 ngày liên tiếp không crash

Phase 3 done khi:
□ 3 người ngoài dùng được không cần hướng dẫn
□ .exe chạy được trên máy Windows mới không cần setup
```

---

## 10. Out of Scope (Không Build)

```
✗ Download video (đã có tool)
✗ Process/edit video (đã có tool)  
✗ Upload lên TikTok (đã có code)
✗ TikTok account management (bạn bạn đã có)
✗ Revenue tracking (bạn bạn đã có dashboard)
```

Tool này chỉ làm 1 việc: **tìm và đánh giá video YouTube để reup.**

