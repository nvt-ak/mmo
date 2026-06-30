"""
TikTok saturation checker.

Uses TikTok's internal JSON API (/api/search/item/full/) via TikTokApi library.
Requires ms_token — get it from tiktok.com cookies (cookie name: msToken).

How to get ms_token:
  1. Open tiktok.com in Chrome, log in
  2. F12 → Application → Cookies → https://www.tiktok.com
  3. Find cookie named 'msToken', copy its value
  4. Add to .env:  TIKTOK_MS_TOKEN=your_value_here
"""
import asyncio
import json
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from database.db import get_connection

CACHE_TTL_HOURS = 6
SEARCH_URL = "https://www.tiktok.com/api/search/item/full/"


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_ms_token() -> str | None:
    """Read ms_token from env or tiktok_ms_token.txt file."""
    token = os.getenv("TIKTOK_MS_TOKEN", "").strip()
    if token:
        return token
    token_file = Path(__file__).parent.parent / "tiktok_ms_token.txt"
    if token_file.exists():
        token = token_file.read_text().strip()
        if token:
            return token
    return None


def _get_cached(keyword: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM tiktok_cache WHERE keyword = ?", (keyword,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    if datetime.now() - datetime.fromisoformat(row["checked_at"]) > timedelta(hours=CACHE_TTL_HOURS):
        return None
    return dict(row)


def _save_cache(keyword: str, count: int, status: str):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO tiktok_cache (keyword, video_count_7d, status, checked_at) VALUES (?,?,?,?)",
        (keyword, count, status, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def _classify(count: int) -> str:
    if count < 20:
        return "fresh"
    if count < 100:
        return "medium"
    return "saturated"


# ── TikTokApi async core ──────────────────────────────────────────────────────

async def _fetch_search_count(keyword: str, ms_token: str) -> int:
    """Call TikTok's internal search API and return video count."""
    from TikTokApi import TikTokApi

    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=3,
            headless=True,
        )

        params = {
            "keyword": keyword,
            "count": 30,
            "cursor": 0,
            "source": "search_video",
        }
        response = await api.make_request(url=SEARCH_URL, params=params)

        if response is None:
            print(f"[TikTok] API returned None for '{keyword}'")
            return 0

        items = response.get("item_list", [])
        has_more = response.get("has_more", False)
        print(f"[TikTok] API response: {len(items)} items, has_more={has_more}, keyword='{keyword}'")
        return len(items)


def _run_async(coro):
    """Run async coroutine safely from a sync context (QThread-compatible)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Running inside an existing loop (shouldn't happen in QThread, but safe)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ── public API ────────────────────────────────────────────────────────────────

def check_saturation(keyword: str) -> dict:
    """
    Return {keyword, video_count_7d, status, cached}.
    status: "fresh" | "medium" | "saturated" | "error"
    """
    cached = _get_cached(keyword)
    if cached:
        cached["cached"] = True
        return cached

    ms_token = _get_ms_token()
    if not ms_token:
        print(
            "[TikTok] No ms_token found. "
            "Add TIKTOK_MS_TOKEN=... to .env or create tiktok_ms_token.txt.\n"
            "Get it from: tiktok.com → F12 → Application → Cookies → msToken"
        )
        return {"keyword": keyword, "video_count_7d": -1, "status": "error", "cached": False}

    try:
        count = _run_async(_fetch_search_count(keyword, ms_token))
        status = _classify(count)
        _save_cache(keyword, count, status)
        return {"keyword": keyword, "video_count_7d": count, "status": status, "cached": False}

    except Exception as e:
        print(f"[TikTok] check_saturation error for '{keyword}': {e}")
        return {"keyword": keyword, "video_count_7d": -1, "status": "error", "cached": False}


def batch_check(keywords: list[str]) -> list[dict]:
    results = []
    for kw in keywords:
        results.append(check_saturation(kw))
        time.sleep(random.uniform(1, 3))
    return results
