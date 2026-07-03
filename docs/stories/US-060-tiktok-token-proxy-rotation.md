# US-060 — TikTok msToken pool + proxy rotation

**Lane:** normal  
**Epic:** E09  
**Status:** implemented

## Goal

Reduce TikTok gate failures during discovery by rotating multiple msTokens
and optional Playwright proxies via TikTok-Api session config.

## Env

- `TIKTOK_MS_TOKENS` — comma-separated msToken values
- `TIKTOK_MS_TOKEN_FILE` — one token per line
- `TIKTOK_PROXY` / `TIKTOK_PROXIES` / `TIKTOK_PROXY_FILE`
- `TIKTOK_BROWSER` — chromium | firefox | webkit
- `TIKTOK_NUM_SESSIONS` — cap parallel TikTok-Api sessions (default 3)
- `TIKTOK_SEARCH_PACING` — human-like delays between keyword searches (default true)
- `TIKTOK_SEARCH_INTERVAL_MIN_SECONDS` / `TIKTOK_SEARCH_INTERVAL_MAX_SECONDS` — gap between searches (default 8–18s)
- `TIKTOK_SEARCH_TYPING_SECONDS_PER_CHAR` — extra delay per character typed (default 0.06)
- `TIKTOK_SEARCH_POST_DWELL_*` — scroll/read pause after results load (default 2–5s)

## Verify

```bash
python -m pytest videoscout/tests_api/test_tiktok_scoring.py -v
```
