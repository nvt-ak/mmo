"""Google Trends — free YouTube search interest via pytrends (US-078 / R7d)."""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_YOUTUBE_TREND_SEEDS = ("music", "gaming", "entertainment", "news", "sports")
_CACHE: Dict[str, Dict[str, Any]] = {}

# Google's explore UI allows Worldwide + YouTube, but the unofficial API rejects it (400).
_SURFACE_WEB_WORLDWIDE = "web_worldwide"
_SURFACE_YOUTUBE_REGIONAL = "youtube_regional"
_SURFACE_PRIMARY = "primary"


def google_trends_enabled() -> bool:
    raw = os.getenv("GOOGLE_TRENDS_ENABLED", "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def google_trends_replace_emergence() -> bool:
    if not google_trends_enabled():
        return False
    raw = os.getenv("GOOGLE_TRENDS_REPLACE_EMERGENCE", "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def google_trends_geo() -> str:
    """Empty string = Worldwide (pytrends convention)."""
    raw = os.getenv("GOOGLE_TRENDS_GEO", "").strip()
    if raw.lower() in ("worldwide", "global", "world"):
        return ""
    return raw


def google_trends_gprop() -> str:
    return os.getenv("GOOGLE_TRENDS_GPROP", "youtube").strip() or "youtube"


def _cache_ttl_seconds() -> int:
    raw = os.getenv("GOOGLE_TRENDS_CACHE_TTL_SECONDS", "21600").strip()
    try:
        return max(60, int(raw))
    except ValueError:
        return 21600


def _request_delay_seconds() -> float:
    raw = os.getenv("GOOGLE_TRENDS_REQUEST_DELAY_SECONDS", "4").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 4.0


def _seed_limit() -> int:
    raw = os.getenv("GOOGLE_TRENDS_SEED_LIMIT", "3").strip()
    try:
        return max(1, min(int(raw), 5))
    except ValueError:
        return 3


def _timeframe() -> str:
    return os.getenv("GOOGLE_TRENDS_TIMEFRAME", "today 3-m").strip() or "today 3-m"


def _fetch_interest_enabled() -> bool:
    raw = os.getenv("GOOGLE_TRENDS_FETCH_INTEREST", "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _youtube_geo_fallback() -> str:
    return os.getenv("GOOGLE_TRENDS_YOUTUBE_GEO_FALLBACK", "").strip()


def _parse_growth_value(value: Any) -> Optional[Any]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() == "breakout":
        return "breakout"
    match = re.search(r"(\d+)", text.replace(",", ""))
    if match:
        return int(match.group(1))
    return text


def _is_retryable_google_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "code 429" in message or "code 400" in message


def rising_query_attempts(
    *,
    geo: str,
    gprop: str,
    youtube_geo_fallback: str = "",
) -> List[Tuple[str, str, str]]:
    """Return (geo, gprop, surface_mode) attempts in priority order."""
    if gprop == "youtube" and not geo:
        attempts: List[Tuple[str, str, str]] = []
        if youtube_geo_fallback:
            attempts.append((youtube_geo_fallback, "youtube", _SURFACE_YOUTUBE_REGIONAL))
        attempts.append(("", "", _SURFACE_WEB_WORLDWIDE))
        return attempts
    return [(geo, gprop, _SURFACE_PRIMARY)]


class GoogleTrendsService:
    """Fetch YouTube search interest and rising queries (no API key)."""

    def __init__(
        self,
        *,
        geo: Optional[str] = None,
        gprop: Optional[str] = None,
        hl: str = "en-GB",
        tz: int = 0,
    ) -> None:
        self.geo = geo if geo is not None else google_trends_geo()
        self.gprop = gprop if gprop is not None else google_trends_gprop()
        self.hl = hl
        self.tz = tz
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from pytrends.request import TrendReq

            self._client = TrendReq(hl=self.hl, tz=self.tz, timeout=(10, 25))
        return self._client

    def _cache_get(self, key: str) -> Optional[Any]:
        entry = _CACHE.get(key)
        if entry and entry.get("expires_at", 0) > time.time():
            return entry.get("data")
        return None

    def _cache_set(self, key: str, data: Any) -> None:
        _CACHE[key] = {
            "data": data,
            "expires_at": time.time() + _cache_ttl_seconds(),
        }

    def fetch_rising_keywords(
        self,
        seeds: List[str],
        *,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Rising search queries from seed topics (gprop=youtube when supported)."""
        cache_key = (
            f"rising:{self.geo}:{self.gprop}:{_youtube_geo_fallback()}:"
            f"{':'.join(seeds[:5])}:{limit}"
        )
        cached = self._cache_get(cache_key)
        if cached is not None:
            return list(cached)

        collected: List[Dict[str, Any]] = []
        seen: set[str] = set()
        delay = _request_delay_seconds()

        for index, seed in enumerate(seeds[:_seed_limit()]):
            if index > 0 and delay:
                time.sleep(delay)
            try:
                rows = self._rising_for_seed(seed)
            except Exception as exc:
                logger.warning("Google Trends rising failed for seed %r: %s", seed, exc)
                continue
            for row in rows:
                keyword = str(row.get("keyword") or "").strip().lower()
                if not keyword or keyword in seen:
                    continue
                if len(keyword.split()) < 2:
                    continue
                seen.add(keyword)
                collected.append(row)
                if len(collected) >= limit:
                    break
            if len(collected) >= limit:
                break

        self._cache_set(cache_key, collected)
        logger.info(
            "Google Trends rising: %d keywords (geo=%r gprop=%r seeds=%d)",
            len(collected),
            self.geo or "Worldwide",
            self.gprop,
            min(len(seeds), _seed_limit()),
        )
        return collected[:limit]

    def _rising_for_seed(self, seed: str) -> List[Dict[str, Any]]:
        attempts = rising_query_attempts(
            geo=self.geo,
            gprop=self.gprop,
            youtube_geo_fallback=_youtube_geo_fallback(),
        )
        last_error: Optional[Exception] = None

        for attempt_geo, attempt_gprop, surface_mode in attempts:
            try:
                rising_df = self._fetch_rising_dataframe(
                    seed,
                    geo=attempt_geo,
                    gprop=attempt_gprop,
                )
            except Exception as exc:
                last_error = exc
                if _is_retryable_google_error(exc):
                    logger.debug(
                        "Google Trends attempt failed seed=%r geo=%r gprop=%r: %s",
                        seed,
                        attempt_geo or "Worldwide",
                        attempt_gprop or "web",
                        exc,
                    )
                    time.sleep(_request_delay_seconds())
                    continue
                raise

            if rising_df is None or rising_df.empty:
                continue

            if surface_mode == _SURFACE_WEB_WORLDWIDE and self.gprop == "youtube":
                logger.info(
                    "Google Trends: Worldwide + YouTube unsupported by API; "
                    "using web search trends (seed=%r)",
                    seed,
                )

            interest_index: Optional[int] = None
            if _fetch_interest_enabled():
                interest_index = self._latest_interest(
                    seed,
                    geo=attempt_geo,
                    gprop=attempt_gprop,
                )

            rows: List[Dict[str, Any]] = []
            for _, item in rising_df.iterrows():
                query = str(item.get("query") or "").strip()
                if not query:
                    continue
                rows.append({
                    "keyword": query,
                    "geo": attempt_geo,
                    "gprop": attempt_gprop,
                    "geo_requested": self.geo,
                    "gprop_requested": self.gprop,
                    "surface_mode": surface_mode,
                    "interest_index": interest_index,
                    "growth_value": str(item.get("value") or ""),
                    "growth_pct": _parse_growth_value(item.get("value")),
                    "query_type": "rising",
                    "seed_keyword": seed,
                })
            return rows

        if last_error is not None:
            raise last_error
        return []

    def _fetch_rising_dataframe(
        self,
        seed: str,
        *,
        geo: str,
        gprop: str,
    ) -> Any:
        client = self._get_client()
        payload_kwargs: Dict[str, Any] = {
            "timeframe": _timeframe(),
            "geo": geo,
        }
        if gprop:
            payload_kwargs["gprop"] = gprop
        client.build_payload([seed], **payload_kwargs)
        related = client.related_queries()
        block = (related or {}).get(seed) or {}
        return block.get("rising")

    def _latest_interest(
        self,
        keyword: str,
        *,
        geo: str,
        gprop: str,
    ) -> Optional[int]:
        try:
            client = self._get_client()
            payload_kwargs: Dict[str, Any] = {
                "timeframe": _timeframe(),
                "geo": geo,
            }
            if gprop:
                payload_kwargs["gprop"] = gprop
            client.build_payload([keyword], **payload_kwargs)
            frame = client.interest_over_time()
            if frame is None or frame.empty or keyword not in frame.columns:
                return None
            return int(frame[keyword].iloc[-1])
        except Exception as exc:
            logger.debug("Google Trends interest lookup failed for %r: %s", keyword, exc)
            return None


_service: Optional[GoogleTrendsService] = None


def get_google_trends_service() -> GoogleTrendsService:
    global _service
    if _service is None:
        _service = GoogleTrendsService()
    return _service


def reset_google_trends_service() -> None:
    """Test helper — clear singleton and cache."""
    global _service
    _service = None
    _CACHE.clear()


def trend_seeds_from_db(topics: Optional[List[str]]) -> List[str]:
    cleaned = [str(topic).strip().lower() for topic in (topics or []) if str(topic).strip()]
    if cleaned:
        return cleaned[:5]
    return list(DEFAULT_YOUTUBE_TREND_SEEDS)
