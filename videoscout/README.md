# VideoScout Backend

FastAPI backend for TikTok keyword suggestion & learning (YouTube reup pipeline).

**Frontend:** see `web/README.md` for Next.js UI.

## Setup

```bash
cd videoscout
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Set DATABASE_URL, YOUTUBE_API_KEY, LLM keys in .env
```

## Run API

```bash
# from repo root
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/videoscout
python -m uvicorn videoscout.api_main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Run Desktop (deprecated)

PyQt6 UI in `videoscout/ui/` is deprecated. Use the web frontend instead.

```bash
python main.py
```

## Structure

```text
videoscout/
  api_main.py       # FastAPI entry
  api/              # Route handlers
  core_engine/      # Suggestion engine + learning
  services/         # YouTube, TikTok
  db/               # SQLAlchemy models
  agents/           # LLM agent logic
  ui/               # Deprecated PyQt6 desktop
```

## Database

PostgreSQL 14+. Run migrations with Alembic from repo root:

```bash
alembic upgrade head
```
