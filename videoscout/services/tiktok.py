"""
TikTok search service for keyword saturation checks.

Uses TikTok's internal JSON API (/api/search/item/full/) via TikTokApi library.
Requires ms_token from tiktok.com cookies (cookie name: msToken).

Set TIKTOK_MS_TOKEN in .env or create videoscout/tiktok_ms_token.txt.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.tiktok.com/api/search/item/full/"
TIKTOK_SEARCH_TIMEOUT_SECONDS = float(os.getenv("TIKTOK_SEARCH_TIMEOUT_SECONDS", "15"))
ERROR_CACHE_TTL_SECONDS = 300

# Cache for TikTok results (6 hours TTL)
_tiktok_cache: Dict[str, Dict] = {}
_error_cache: Dict[str, Dict] = {}
_batch_session: Optional[Dict[str, Any]] = None


def _get_ms_token() -> Optional[str]:
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


def _run_async(coro):
    """Run async coroutine safely from a sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _parse_search_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize TikTok search item to internal video dict."""
    stats = item.get("stats") or {}
    create_time = item.get("createTime") or item.get("create_time")
    created_at = ""
    if create_time is not None:
        try:
            created_at = datetime.utcfromtimestamp(int(create_time)).isoformat() + "Z"
        except (TypeError, ValueError):
            created_at = ""

    return {
        "view_count": stats.get("playCount") or stats.get("play_count") or 0,
        "like_count": stats.get("diggCount") or stats.get("digg_count") or 0,
        "comment_count": stats.get("commentCount") or stats.get("comment_count") or 0,
        "share_count": stats.get("shareCount") or stats.get("share_count") or 0,
        "created_at": created_at,
    }


async def _fetch_search_videos(keyword: str, ms_token: str, *, limit: int) -> List[Dict[str, Any]]:
    """Call TikTok internal search API and return normalized video rows."""
    from TikTokApi import TikTokApi

    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=1,
            headless=True,
        )

        params = {
            "keyword": keyword,
            "count": min(limit, 30),
            "cursor": 0,
            "source": "search_video",
        }
        response = await asyncio.wait_for(
            api.make_request(url=SEARCH_URL, params=params),
            timeout=TIKTOK_SEARCH_TIMEOUT_SECONDS,
        )

        if response is None:
            logger.warning("TikTok API returned None for keyword=%r", keyword)
            return []

        items = response.get("item_list") or []
        return [
            _parse_search_item(item)
            for item in items
            if isinstance(item, dict)
        ]


async def _ensure_batch_api(ms_token: str):
    global _batch_session
    if _batch_session is None:
        raise RuntimeError("TikTok batch session not started")
    if _batch_session.get("api") is None:
        from TikTokApi import TikTokApi

        api = TikTokApi()
        await api.__aenter__()
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=1,
            headless=True,
        )
        _batch_session["api"] = api
    return _batch_session["api"]


async def _fetch_search_videos_batch(
    keyword: str,
    ms_token: str,
    *,
    limit: int,
) -> List[Dict[str, Any]]:
    api = await _ensure_batch_api(ms_token)
    params = {
        "keyword": keyword,
        "count": min(limit, 30),
        "cursor": 0,
        "source": "search_video",
    }
    try:
        response = await asyncio.wait_for(
            api.make_request(url=SEARCH_URL, params=params),
            timeout=TIKTOK_SEARCH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise TimeoutError(
            f"Timeout {int(TIKTOK_SEARCH_TIMEOUT_SECONDS * 1000)}ms exceeded",
        ) from exc

    if response is None:
        logger.warning("TikTok API returned None for keyword=%r", keyword)
        return []

    items = response.get("item_list") or []
    return [
        _parse_search_item(item)
        for item in items
        if isinstance(item, dict)
    ]


async def _close_batch_api(api) -> None:
    await api.__aexit__(None, None, None)


def _empty_search_result(*, rate_limited: bool = False, error: Optional[str] = None) -> Dict:
    payload = {
        "videos": [],
        "total_count": 0,
        "avg_views": 0.0,
        "avg_likes": 0.0,
        "avg_comments": 0.0,
        "avg_engagement_rate": 0.0,
    }
    if rate_limited:
        payload["rate_limited"] = True
    if error:
        payload["error"] = error
    return payload


class TikTokService:
    """
    TikTok video search service.

    Uses TikTok internal search API to check keyword saturation.
    """

    def __init__(self, ms_token: Optional[str] = None):
        self.ms_token = ms_token

    def _resolve_ms_token(self) -> Optional[str]:
        if self.ms_token:
            return self.ms_token
        return _get_ms_token()

    def start_batch(self) -> None:
        """Reuse one browser session for multiple searches in a discovery job."""
        global _batch_session
        self.end_batch()
        _batch_session = {"api": None}

    def end_batch(self) -> None:
        """Close a batch browser session if open."""
        global _batch_session
        if _batch_session is None:
            return
        api = _batch_session.get("api")
        _batch_session = None
        if api is not None:
            try:
                _run_async(_close_batch_api(api))
            except Exception as exc:
                logger.warning("Error closing TikTok batch session: %s", exc)

    def search_videos(
        self,
        keyword: str,
        period: str = "7d",
        limit: int = 50,
    ) -> Dict:
        """
        Search TikTok videos by keyword.

        Returns:
            {
                "videos": List[dict],
                "total_count": int,
                "avg_views": float,
                "avg_likes": float,
                "avg_comments": float,
                "avg_engagement_rate": float
            }
        """
        cache_key = f"{keyword}:{period}:{limit}"
        cached = _tiktok_cache.get(cache_key)
        if cached:
            expires_at = cached.get("expires_at", 0)
            if expires_at > time.time():
                return cached["data"]

        error_cached = _error_cache.get(cache_key)
        if error_cached and error_cached.get("expires_at", 0) > time.time():
            return error_cached["data"]

        ms_token = self._resolve_ms_token()
        if not ms_token:
            return _empty_search_result(error="no_ms_token")

        days = {"1d": 1, "7d": 7, "30d": 30}.get(period, 7)

        try:
            if _batch_session is not None:
                videos = _run_async(
                    _fetch_search_videos_batch(keyword, ms_token, limit=limit),
                )
            else:
                videos = _run_async(
                    _fetch_search_videos(keyword, ms_token, limit=limit),
                )
            return self._process_response({"videos": videos}, days, cache_key=cache_key)
        except Exception as exc:
            logger.warning("TikTok search failed for keyword=%r: %s", keyword, exc)
            result = _empty_search_result(error=str(exc))
            _error_cache[cache_key] = {
                "data": result,
                "expires_at": time.time() + ERROR_CACHE_TTL_SECONDS,
            }
            return result

    def _process_response(self, data: Dict, days: int, *, cache_key: str) -> Dict:
        """Process API response and calculate metrics."""
        if not isinstance(data, dict):
            return _empty_search_result(error="invalid_response")

        raw_videos = data.get("videos")
        videos = raw_videos if isinstance(raw_videos, list) else []

        if not videos:
            result = _empty_search_result()
            _tiktok_cache[cache_key] = {
                "data": result,
                "expires_at": time.time() + 6 * 3600,
            }
            return result

        cutoff_date = datetime.now() - timedelta(days=days)

        filtered_videos = []
        total_views = 0
        total_likes = 0
        total_comments = 0
        total_engagement = 0

        def _include_video_stats(video_item: Dict) -> None:
            nonlocal total_views, total_likes, total_comments, total_engagement
            filtered_videos.append(video_item)
            views = video_item.get("view_count", 0) or 0
            likes = video_item.get("like_count", 0) or 0
            comments = video_item.get("comment_count", 0) or 0
            shares = video_item.get("share_count", 0) or 0
            total_views += views
            total_likes += likes
            total_comments += comments
            total_engagement += (likes + comments + shares)

        for video in videos:
            if not isinstance(video, dict):
                continue
            created_at = video.get("created_at", "")
            if created_at:
                try:
                    video_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if video_date >= cutoff_date:
                        _include_video_stats(video)
                except Exception:
                    _include_video_stats(video)
            else:
                _include_video_stats(video)

        total_count = len(filtered_videos)
        avg_views = total_views / total_count if total_count > 0 else 0
        avg_likes = total_likes / total_count if total_count > 0 else 0
        avg_comments = total_comments / total_count if total_count > 0 else 0
        avg_engagement_rate = (
            total_engagement / total_views
            if total_views > 0 else 0
        )

        result = {
            "videos": filtered_videos,
            "total_count": total_count,
            "avg_views": avg_views,
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "avg_engagement_rate": avg_engagement_rate,
        }

        _tiktok_cache[cache_key] = {
            "data": result,
            "expires_at": time.time() + 6 * 3600,
        }

        return result

    def get_keyword_saturation(
        self,
        keyword: str,
        period: str = "7d",
    ) -> Dict:
        """
        Get saturation score for a keyword.

        Returns:
            {
                "keyword": str,
                "video_count": int,
                "status": "low" | "moderate" | "saturated",
                "avg_views": float,
                "engagement_rate": float
            }
        """
        result = self.search_videos(keyword, period=period, limit=50)
        if not isinstance(result, dict):
            result = _empty_search_result(error="invalid_result")

        count = result.get("total_count", 0)

        if count <= 10:
            status = "low"
        elif count <= 50:
            status = "moderate"
        else:
            status = "saturated"

        return {
            "keyword": keyword,
            "video_count": count,
            "status": status,
            "avg_views": result.get("avg_views", 0),
            "engagement_rate": result.get("avg_engagement_rate", 0),
        }


_tiktok_service: Optional[TikTokService] = None


def get_tiktok_service() -> TikTokService:
    """Get or create singleton TikTok service instance."""
    global _tiktok_service
    if _tiktok_service is None:
        _tiktok_service = TikTokService()
    return _tiktok_service
