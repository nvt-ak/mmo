"""
TikTok search service for keyword saturation checks.

Uses TikTok search API (/api/search/general/full/) via TikTokApi + Playwright.
Falls back to /api/search/item/full/ when general returns no videos.
Requires ms_token from tiktok.com cookies (cookie name: msToken).

Configure tokens via TIKTOK_MS_TOKEN, TIKTOK_MS_TOKENS, TIKTOK_MS_TOKEN_FILE,
or videoscout/tiktok_ms_token.txt (one token per line).

Optional full profile: TIKTOK_COOKIES_FILE (Cookie-Editor / Playwright JSON) —
passed to TikTokApi create_sessions(cookies=[name→value dict, ...]).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlparse

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.tiktok.com/api/search/general/full/"
SEARCH_URL_FALLBACK = "https://www.tiktok.com/api/search/item/full/"
SEARCH_API_PATHS = ("/api/search/general/full/", "/api/search/item/full/")
WEB_SEARCH_CODE = (
    '{"tiktok":{"client_params_x":{"search_engine":'
    '{"ies_mt_user_live_video_card_use_libra":1,'
    '"mt_search_general_user_live_card":1}},'
    '"search_server":{}}}'
)
TIKTOK_SEARCH_TIMEOUT_SECONDS = float(os.getenv("TIKTOK_SEARCH_TIMEOUT_SECONDS", "30"))
ERROR_CACHE_TTL_SECONDS = 300
DEFAULT_MS_TOKEN_FILE = Path(__file__).parent.parent / "tiktok_ms_token.txt"
DEFAULT_COOKIES_FILE = Path(__file__).parent.parent / "tiktok_cookies.json"

_tiktok_cache: Dict[str, Dict] = {}
_error_cache: Dict[str, Dict] = {}
_batch_session: Optional[Dict[str, Any]] = None
_last_search_paced_at: float = 0.0


def _search_pacing_enabled() -> bool:
    raw = os.getenv("TIKTOK_SEARCH_PACING", "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _target_pre_search_delay(keyword: str) -> float:
    """Human-like gap before starting a new keyword search."""
    min_s = float(os.getenv("TIKTOK_SEARCH_INTERVAL_MIN_SECONDS", "8"))
    max_s = float(os.getenv("TIKTOK_SEARCH_INTERVAL_MAX_SECONDS", "18"))
    if max_s < min_s:
        max_s = min_s
    per_char = float(os.getenv("TIKTOK_SEARCH_TYPING_SECONDS_PER_CHAR", "0.06"))
    base = random.uniform(min_s, max_s)
    typing = len(keyword.strip()) * per_char
    return base + typing


async def _pace_before_search(keyword: str) -> None:
    """Wait between keyword searches so batch discovery looks human."""
    global _last_search_paced_at
    if not _search_pacing_enabled():
        return

    if _last_search_paced_at <= 0:
        initial_min = float(os.getenv("TIKTOK_SEARCH_INITIAL_DELAY_MIN_SECONDS", "1.5"))
        initial_max = float(os.getenv("TIKTOK_SEARCH_INITIAL_DELAY_MAX_SECONDS", "4"))
        if initial_max < initial_min:
            initial_max = initial_min
        wait = random.uniform(initial_min, initial_max)
        logger.debug("TikTok search pacing: initial wait %.1fs before %r", wait, keyword)
        await asyncio.sleep(wait)
        return

    target_delay = _target_pre_search_delay(keyword)
    elapsed = time.monotonic() - _last_search_paced_at
    wait = target_delay - elapsed
    if wait > 0:
        logger.debug(
            "TikTok search pacing: waiting %.1fs (target %.1fs, elapsed %.1fs) before %r",
            wait,
            target_delay,
            elapsed,
            keyword,
        )
        await asyncio.sleep(wait)


async def _post_search_dwell() -> None:
    """Simulate brief scroll/read after results load."""
    if not _search_pacing_enabled():
        return
    post_min = float(os.getenv("TIKTOK_SEARCH_POST_DWELL_MIN_SECONDS", "2"))
    post_max = float(os.getenv("TIKTOK_SEARCH_POST_DWELL_MAX_SECONDS", "5"))
    if post_max < post_min:
        post_max = post_min
    dwell = random.uniform(post_min, post_max)
    logger.debug("TikTok search pacing: post-search dwell %.1fs", dwell)
    await asyncio.sleep(dwell)


def _mark_search_paced() -> None:
    global _last_search_paced_at
    _last_search_paced_at = time.monotonic()


def _reset_search_pacing() -> None:
    global _last_search_paced_at
    _last_search_paced_at = 0.0


def _split_env_list(raw: str) -> List[str]:
    return [part.strip() for part in raw.replace("\n", ",").split(",") if part.strip()]


def _load_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    lines: List[str] = []
    for line in path.read_text().splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            lines.append(value)
    return lines


def _dedupe(values: List[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value))


def get_ms_tokens() -> List[str]:
    """Load msToken values from env, optional files, and cookie profiles."""
    tokens: List[str] = []

    tokens.extend(_split_env_list(os.getenv("TIKTOK_MS_TOKENS", "")))

    token_file = os.getenv("TIKTOK_MS_TOKEN_FILE", "").strip()
    if token_file:
        tokens.extend(_load_lines(Path(token_file)))

    single = os.getenv("TIKTOK_MS_TOKEN", "").strip()
    if single:
        tokens.insert(0, single)

    tokens.extend(_load_lines(DEFAULT_MS_TOKEN_FILE))
    tokens.extend(extract_ms_tokens_from_profiles(get_tiktok_cookie_profiles()))
    return _dedupe(tokens)


def _cookie_name_value(entry: Any) -> Optional[tuple[str, str]]:
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    value = entry.get("value")
    if name is None or value is None:
        return None
    name_s = str(name).strip()
    value_s = str(value)
    if not name_s:
        return None
    return name_s, value_s


def _cookie_entries_to_profile(entries: List[Any]) -> Dict[str, str]:
    """
    Build TikTokApi cookie dict (name → value).

    Duplicate names (e.g. two msToken rows): keep the longest value.
    """
    profile: Dict[str, str] = {}
    for entry in entries:
        pair = _cookie_name_value(entry)
        if not pair:
            continue
        name, value = pair
        existing = profile.get(name)
        if existing is None or len(value) > len(existing):
            profile[name] = value
    return profile


def parse_tiktok_cookies_payload(payload: Any) -> List[Dict[str, str]]:
    """
    Normalize exported cookie JSON into TikTokApi profiles.

    Supported shapes:
    - Cookie-Editor / EditThisCookie: [ {name, value, domain, ...}, ... ]
    - Playwright storage state: { "cookies": [ ... ] }
    - Already a name→value map: { "msToken": "...", "sessionid": "..." }
    - List of profiles: [ {name→value}, {name→value}, ... ]
    """
    if payload is None:
        return []

    if isinstance(payload, dict):
        if "cookies" in payload and isinstance(payload["cookies"], list):
            profile = _cookie_entries_to_profile(payload["cookies"])
            return [profile] if profile else []
        # name→value map (no nested cookie list)
        if all(isinstance(v, (str, int, float, type(None))) for v in payload.values()):
            profile = {
                str(k): str(v)
                for k, v in payload.items()
                if v is not None and str(k).strip()
            }
            return [profile] if profile else []
        return []

    if not isinstance(payload, list) or not payload:
        return []

    # List of cookie objects (Cookie-Editor)
    if all(isinstance(item, dict) and "name" in item for item in payload):
        profile = _cookie_entries_to_profile(payload)
        return [profile] if profile else []

    # List of name→value profiles
    profiles: List[Dict[str, str]] = []
    for item in payload:
        if isinstance(item, dict) and "name" not in item:
            profile = {
                str(k): str(v)
                for k, v in item.items()
                if v is not None and str(k).strip()
            }
            if profile:
                profiles.append(profile)
        elif isinstance(item, list):
            profile = _cookie_entries_to_profile(item)
            if profile:
                profiles.append(profile)
    return profiles


def load_tiktok_cookies_file(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load TikTok cookies from %s: %s", path, exc)
        return []
    profiles = parse_tiktok_cookies_payload(payload)
    if profiles:
        logger.info(
            "Loaded %d TikTok cookie profile(s) from %s (%d cookies in first)",
            len(profiles),
            path,
            len(profiles[0]),
        )
    return profiles


def get_tiktok_cookie_profiles() -> List[Dict[str, str]]:
    """Load cookie profiles for create_sessions(cookies=...)."""
    env_path = os.getenv("TIKTOK_COOKIES_FILE", "").strip()
    if env_path:
        return load_tiktok_cookies_file(Path(env_path).expanduser())
    return load_tiktok_cookies_file(DEFAULT_COOKIES_FILE)


def extract_ms_tokens_from_profiles(profiles: List[Dict[str, str]]) -> List[str]:
    tokens: List[str] = []
    for profile in profiles:
        value = (profile.get("msToken") or profile.get("mstoken") or "").strip()
        if value:
            tokens.append(value)
    return tokens


def _playwright_proxy(proxy_url: str) -> Dict[str, str]:
    parsed = urlparse(proxy_url.strip())
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"Invalid proxy URL: {proxy_url!r}")

    server = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        server = f"{server}:{parsed.port}"

    proxy: Dict[str, str] = {"server": server}
    if parsed.username:
        proxy["username"] = parsed.username
    if parsed.password:
        proxy["password"] = parsed.password
    return proxy


def get_proxies() -> List[Dict[str, str]]:
    """Load Playwright proxy dicts from env and optional files."""
    urls: List[str] = []
    urls.extend(_split_env_list(os.getenv("TIKTOK_PROXIES", "")))

    proxy_file = os.getenv("TIKTOK_PROXY_FILE", "").strip()
    if proxy_file:
        urls.extend(_load_lines(Path(proxy_file)))

    single = os.getenv("TIKTOK_PROXY", "").strip()
    if single:
        urls.insert(0, single)

    proxies: List[Dict[str, str]] = []
    for url in _dedupe(urls):
        try:
            proxies.append(_playwright_proxy(url))
        except ValueError as exc:
            logger.warning("Skipping invalid TikTok proxy %r: %s", url, exc)
    return proxies


def _browser_name() -> str:
    browser = os.getenv("TIKTOK_BROWSER", "webkit").strip().lower()
    if browser in ("chromium", "firefox", "webkit"):
        return browser
    logger.warning("Unknown TIKTOK_BROWSER=%r; using webkit", browser)
    return "webkit"


def _headless() -> bool:
    raw = os.getenv("TIKTOK_HEADLESS", "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _search_retries() -> int:
    return max(1, min(int(os.getenv("TIKTOK_SEARCH_RETRIES", "3")), 10))


def _session_count(ms_tokens: List[str]) -> int:
    configured = int(os.getenv("TIKTOK_NUM_SESSIONS", "3"))
    configured = max(1, min(configured, 5))
    if ms_tokens:
        return max(1, min(len(ms_tokens), configured))
    return 1


async def _create_api_sessions(
    api: Any,
    *,
    ms_tokens: List[str],
    proxies: Optional[List[Dict[str, str]]] = None,
    cookie_profiles: Optional[List[Dict[str, str]]] = None,
) -> None:
    kwargs: Dict[str, Any] = {
        "num_sessions": _session_count(ms_tokens),
        "headless": _headless(),
        "sleep_after": int(os.getenv("TIKTOK_SESSION_SLEEP_AFTER", "3")),
        "browser": _browser_name(),
        "allow_partial_sessions": True,
        "min_sessions": 1,
    }
    if ms_tokens:
        kwargs["ms_tokens"] = ms_tokens

    if cookie_profiles is None:
        cookie_profiles = get_tiktok_cookie_profiles()
    if cookie_profiles:
        # TikTokApi expects list of name→value maps; random_choice picks one per session.
        kwargs["cookies"] = cookie_profiles
        kwargs["num_sessions"] = max(
            1,
            min(len(cookie_profiles), int(os.getenv("TIKTOK_NUM_SESSIONS", "3")) or 1),
        )

    if proxies is None:
        proxies = get_proxies()
    if proxies:
        kwargs["proxies"] = proxies

    await api.create_sessions(**kwargs)


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


def _search_page_url(keyword: str) -> str:
    """Browser search URL (same as tiktok.com/search?q=…&t=…)."""
    ts = int(time.time() * 1000)
    return f"https://www.tiktok.com/search?q={quote(keyword)}&t={ts}"


def _is_search_api_url(url: str) -> bool:
    return any(path in url for path in SEARCH_API_PATHS)


def _search_api_params(keyword: str, *, limit: int) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "keyword": keyword,
        "count": min(limit, 30),
        "cursor": 0,
        "offset": 0,
        "from_page": "search",
        "web_search_code": WEB_SEARCH_CODE,
        "search_source": "recom_search",
        "is_non_personalized_search": 0,
    }
    region = os.getenv("TIKTOK_REGION", "").strip()
    if region:
        params["region"] = region
    return params


def _extract_raw_search_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalize item/full and general/full search JSON payloads."""
    item_list = payload.get("item_list")
    if isinstance(item_list, list) and item_list:
        return [item for item in item_list if isinstance(item, dict)]

    items: List[Dict[str, Any]] = []
    for entry in payload.get("data") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") == 1 and isinstance(entry.get("item"), dict):
            items.append(entry["item"])
            continue
        if entry.get("stats") or entry.get("createTime") or entry.get("create_time"):
            items.append(entry)
            continue
        nested = entry.get("item")
        if isinstance(nested, dict):
            items.append(nested)
    return items


def _parse_search_payload(payload: Dict[str, Any], *, limit: int) -> List[Dict[str, Any]]:
    return [
        _parse_search_item(item)
        for item in _extract_raw_search_items(payload)
        if isinstance(item, dict)
    ][:limit]


async def _get_playwright_session(api: Any) -> tuple[int, Any]:
    if hasattr(api, "_get_valid_session_index"):
        return await api._get_valid_session_index()
    return api._get_session()


async def _capture_search_from_navigation(
    api: Any,
    keyword: str,
    *,
    limit: int,
    session: Any,
) -> Optional[List[Dict[str, Any]]]:
    """Navigate to /search?q=… and capture search API JSON from the page."""
    page = session.page
    url = _search_page_url(keyword)
    timeout_ms = int(TIKTOK_SEARCH_TIMEOUT_SECONDS * 1000)

    try:
        async with page.expect_response(
            lambda r: _is_search_api_url(r.url) and r.status == 200,
            timeout=timeout_ms,
        ) as response_info:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        data = await (await response_info.value).json()
        parsed = _parse_search_payload(data, limit=limit)
        if parsed:
            logger.info(
                "TikTok search captured %d items via page navigation for %r",
                len(parsed),
                keyword,
            )
            return parsed
    except Exception as exc:
        logger.debug("Search page capture missed for %r: %s", keyword, exc)

    try:
        if "search" not in (page.url or ""):
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        await asyncio.sleep(float(os.getenv("TIKTOK_SEARCH_WARM_SLEEP", "3")))
    except Exception as exc:
        logger.debug("Search page warm-up failed for %r: %s", keyword, exc)

    return None


def _parse_search_item(item: Dict[str, Any]) -> Dict[str, Any]:
    stats = item.get("stats") or {}
    create_time = item.get("createTime") or item.get("create_time")
    created_at = ""
    if create_time is not None:
        try:
            created_at = datetime.utcfromtimestamp(int(create_time)).isoformat() + "Z"
        except (TypeError, ValueError):
            created_at = ""

    author = item.get("author") or {}
    author_meta = item.get("authorMeta") or {}
    author_id = (
        author.get("uniqueId")
        or author.get("id")
        or author_meta.get("uniqueId")
        or author_meta.get("id")
        or item.get("authorId")
        or ""
    )

    return {
        "view_count": stats.get("playCount") or stats.get("play_count") or 0,
        "like_count": stats.get("diggCount") or stats.get("digg_count") or 0,
        "comment_count": stats.get("commentCount") or stats.get("comment_count") or 0,
        "share_count": stats.get("shareCount") or stats.get("share_count") or 0,
        "created_at": created_at,
        "author_id": str(author_id) if author_id else "",
    }


async def _request_search_items(api: Any, keyword: str, *, limit: int) -> List[Dict[str, Any]]:
    session_index, session = await _get_playwright_session(api)

    captured = await _capture_search_from_navigation(
        api,
        keyword,
        limit=limit,
        session=session,
    )
    if captured:
        await _post_search_dwell()
        _mark_search_paced()
        return captured

    params = _search_api_params(keyword, limit=limit)
    last_response: Optional[Dict[str, Any]] = None
    for search_url in (SEARCH_URL, SEARCH_URL_FALLBACK):
        try:
            response = await asyncio.wait_for(
                api.make_request(
                    url=search_url,
                    params=params,
                    session_index=session_index,
                ),
                timeout=TIKTOK_SEARCH_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            raise TimeoutError(
                f"Timeout {int(TIKTOK_SEARCH_TIMEOUT_SECONDS * 1000)}ms exceeded",
            ) from exc

        if response is None:
            continue

        last_response = response
        parsed = _parse_search_payload(response, limit=limit)
        if parsed:
            logger.info(
                "TikTok search API returned %d items from %s for %r",
                len(parsed),
                search_url.rsplit("/", 2)[-2],
                keyword,
            )
            await _post_search_dwell()
            _mark_search_paced()
            return parsed

    if last_response is None:
        raise RuntimeError(
            "TikTok returned an empty response. They are detecting you're a bot, "
            "try some of these: headless=False, browser='webkit', consider using a proxy",
        )

    logger.warning(
        "TikTok API returned 0 video items for %r after search page warm-up",
        keyword,
    )
    await _post_search_dwell()
    _mark_search_paced()
    return []


async def _fetch_search_videos(
    keyword: str,
    ms_tokens: List[str],
    *,
    limit: int,
    proxies: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    from TikTokApi import TikTokApi

    async with TikTokApi() as api:
        await _create_api_sessions(api, ms_tokens=ms_tokens, proxies=proxies)
        return await _request_search_items(api, keyword, limit=limit)


async def _ensure_batch_api(
    ms_tokens: List[str],
    *,
    proxies: Optional[List[Dict[str, str]]] = None,
):
    global _batch_session
    if _batch_session is None:
        raise RuntimeError("TikTok batch session not started")

    loop_id = id(asyncio.get_running_loop())
    if _batch_session.get("loop_id") is None:
        _batch_session["loop_id"] = loop_id
    elif _batch_session["loop_id"] != loop_id:
        raise RuntimeError("TikTok batch session belongs to a different event loop")

    if _batch_session.get("api") is None:
        from TikTokApi import TikTokApi

        api = TikTokApi()
        await api.__aenter__()
        await _create_api_sessions(api, ms_tokens=ms_tokens, proxies=proxies)
        _batch_session["api"] = api
        _batch_session["ms_tokens"] = ms_tokens
        _batch_session["proxies"] = proxies
    return _batch_session["api"]


async def _reset_batch_api(
    ms_tokens: List[str],
    *,
    proxies: Optional[List[Dict[str, str]]] = None,
) -> None:
    global _batch_session
    if _batch_session is None:
        return
    api = _batch_session.get("api")
    _batch_session["api"] = None
    if api is not None:
        try:
            await _close_batch_api(api)
        except Exception as exc:
            logger.warning("Error resetting TikTok batch session: %s", exc)
    await _ensure_batch_api(ms_tokens, proxies=proxies)


async def _fetch_search_videos_batch(
    keyword: str,
    ms_tokens: List[str],
    *,
    limit: int,
    proxies: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    api = await _ensure_batch_api(ms_tokens, proxies=proxies)
    return await _request_search_items(api, keyword, limit=limit)


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
    """TikTok video search service for keyword saturation checks."""

    def __init__(self, ms_token: Optional[str] = None, ms_tokens: Optional[List[str]] = None):
        self.ms_token = ms_token
        self.ms_tokens = ms_tokens

    def _resolve_ms_tokens(self) -> List[str]:
        if self.ms_tokens:
            return _dedupe(self.ms_tokens)
        if self.ms_token:
            return [self.ms_token]
        return get_ms_tokens()

    def start_batch(self) -> None:
        global _batch_session
        if _batch_session and _batch_session.get("api") is not None:
            logger.warning(
                "start_batch() replacing an open TikTok session; "
                "call await end_batch_async() first",
            )
        _reset_search_pacing()
        _batch_session = {
            "api": None,
            "loop_id": None,
            "ms_tokens": self._resolve_ms_tokens(),
        }

    async def end_batch_async(self) -> None:
        global _batch_session
        if _batch_session is None:
            return
        api = _batch_session.get("api")
        _batch_session = None
        _reset_search_pacing()
        if api is not None:
            try:
                await _close_batch_api(api)
            except Exception as exc:
                logger.warning("Error closing TikTok batch session: %s", exc)

    def end_batch(self) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            _run_async(self.end_batch_async())
            return
        logger.warning(
            "end_batch() called with a running event loop; use await end_batch_async()",
        )

    async def _fetch_videos_for_keyword(
        self,
        keyword: str,
        ms_tokens: List[str],
        *,
        limit: int,
        proxies: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        if _batch_session is not None:
            return await _fetch_search_videos_batch(
                keyword, ms_tokens, limit=limit, proxies=proxies,
            )
        return await _fetch_search_videos(
            keyword, ms_tokens, limit=limit, proxies=proxies,
        )

    def _search_attempts(
        self,
        ms_tokens: List[str],
        *,
        proxies: List[Dict[str, str]],
    ) -> List[tuple[List[str], Optional[List[Dict[str, str]]]]]:
        """Build (rotated tokens, proxy slice) plans for retries."""
        token_order = list(ms_tokens)
        if len(token_order) > 1:
            token_order = [token_order[0]] + random.sample(token_order[1:], len(token_order) - 1)

        attempts: List[tuple[List[str], Optional[List[Dict[str, str]]]]] = []
        retries = _search_retries()
        for attempt in range(retries):
            rotated = token_order[attempt % len(token_order):] + token_order[: attempt % len(token_order)]
            if proxies:
                proxy = proxies[attempt % len(proxies)]
                attempts.append((rotated, [proxy]))
            else:
                attempts.append((rotated, None))
        return attempts

    async def search_videos_async(
        self,
        keyword: str,
        period: str = "7d",
        limit: int = 50,
    ) -> Dict:
        cache_key = f"{keyword}:{period}:{limit}"
        cached = _tiktok_cache.get(cache_key)
        if cached and cached.get("expires_at", 0) > time.time():
            return cached["data"]

        error_cached = _error_cache.get(cache_key)
        if error_cached and error_cached.get("expires_at", 0) > time.time():
            return error_cached["data"]

        ms_tokens = self._resolve_ms_tokens()
        if not ms_tokens:
            return _empty_search_result(error="no_ms_token")

        await _pace_before_search(keyword)

        days = {"1d": 1, "7d": 7, "30d": 30}.get(period, 7)
        proxies = get_proxies()
        attempts = self._search_attempts(ms_tokens, proxies=proxies)

        last_error: Optional[Exception] = None
        for index, (rotated, attempt_proxies) in enumerate(attempts):
            try:
                videos = await self._fetch_videos_for_keyword(
                    keyword,
                    rotated,
                    limit=limit,
                    proxies=attempt_proxies,
                )
                return self._process_response({"videos": videos}, days, cache_key=cache_key)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "TikTok search failed for keyword=%r (attempt %d/%d): %s",
                    keyword,
                    index + 1,
                    len(attempts),
                    exc,
                )
                if _batch_session is not None and index < len(attempts) - 1:
                    await _reset_batch_api(rotated, proxies=attempt_proxies)
                elif _batch_session is None and index < len(attempts) - 1:
                    await asyncio.sleep(float(os.getenv("TIKTOK_RETRY_SLEEP_SECONDS", "2")))

        assert last_error is not None
        if _search_pacing_enabled():
            fail_min = float(os.getenv("TIKTOK_SEARCH_FAIL_DWELL_MIN_SECONDS", "3"))
            fail_max = float(os.getenv("TIKTOK_SEARCH_FAIL_DWELL_MAX_SECONDS", "6"))
            if fail_max < fail_min:
                fail_max = fail_min
            await asyncio.sleep(random.uniform(fail_min, fail_max))
        _mark_search_paced()
        result = _empty_search_result(error=str(last_error))
        _error_cache[cache_key] = {
            "data": result,
            "expires_at": time.time() + ERROR_CACHE_TTL_SECONDS,
        }
        return result

    def search_videos(
        self,
        keyword: str,
        period: str = "7d",
        limit: int = 50,
    ) -> Dict:
        return _run_async(
            self.search_videos_async(keyword, period=period, limit=limit),
        )

    def _process_response(self, data: Dict, days: int, *, cache_key: str) -> Dict:
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
    global _tiktok_service
    if _tiktok_service is None:
        _tiktok_service = TikTokService()
    return _tiktok_service
