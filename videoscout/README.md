# VideoScout

Desktop app tìm và đánh giá video YouTube để reup TikTok DE.

## Setup

```bash
cd videoscout
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Điền YOUTUBE_API_KEY vào .env
```

## Run

```bash
python main.py
```

## Build .exe (Windows)

```bash
pyinstaller --onefile --windowed --name VideoScout \
  --add-data "*.env;." main.py
```

## Workflow

1. **Settings** → nhập YouTube API Key → Save
2. **Channels** → Add channel URL (YouTube idol channels)
3. **Daily Digest** → Scan Now → xem list video → Copy URLs
4. Paste URLs vào download pipeline của bạn
5. **TikTok Check** → verify keyword chưa bão hòa trước khi chọn niche mới

## Filters mặc định

| Filter | Default |
|--------|---------|
| Views | 150K – 200K |
| Uploaded within | 30 ngày |
| Channel size | < 50K subs |
| Duration | < 3 phút |

Thay đổi trong **Settings**.

## Scoring (0-100)

- Recency: 40 pts (càng mới càng cao)
- View sweet spot: 30 pts (gần 175K = max)
- Channel size: 20 pts (càng nhỏ càng ít bị report)
- TikTok gap: 10 pts (chưa có trên TikTok = bonus)
