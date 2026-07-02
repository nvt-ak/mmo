# VideoScout Web (Phase 2)

Next.js frontend for the VideoScout keyword inbox.

## Stack

- Next.js 16 (App Router)
- TypeScript + Tailwind CSS
- TanStack React Query

## Pages

| Route | Purpose |
|-------|---------|
| `/today` | Inbox — bulk approve/reject, report, improve |
| `/sources` | YouTube channel management + manual scan |
| `/settings` | Scoring weights + niche topics |
| `/insights` | Learning patterns + cycle trigger |

## Setup

```bash
# Terminal 1: backend
cd /path/to/mmo
export DATABASE_URL=postgresql://...
export YOUTUBE_API_KEY=...
/Users/nvt/.asdf/installs/python/3.10.0/bin/python -m uvicorn videoscout.api_main:app --reload --port 8000

# Terminal 2: frontend
cd web
cp .env.local.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) → redirects to `/today`.

## API

Backend must run on port **8000** (CORS allows `localhost:3000`).

Override with `NEXT_PUBLIC_API_URL` in `.env.local`.

## Scripts

```bash
npm run dev      # dev server
npm run build    # production build
npm run lint     # eslint
```

## Structure

```
web/src/
├── app/              # routes
├── components/       # UI by feature
└── lib/api/          # typed API client + types
```
