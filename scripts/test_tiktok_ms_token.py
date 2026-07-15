#!/usr/bin/env python3
"""
Smoke-test / diagnose TikTok msToken + Playwright search session.

Loads videoscout/.env (does not print raw token values).

Usage (from repo root):
  PYTHONPATH=. python scripts/test_tiktok_ms_token.py --no-cache
  PYTHONPATH=. python scripts/test_tiktok_ms_token.py --keyword aespa --no-cache
  PYTHONPATH=. python scripts/test_tiktok_ms_token.py --diagnose --no-cache

Exit codes:
  0 — search path usable (total_count may be 0 for obscure keywords)
  1 — no token / bot empty response / session failure
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

ENV_PATH = REPO_ROOT / "videoscout" / ".env"
load_dotenv(ENV_PATH, override=True)

from videoscout.services.tiktok import (  # noqa: E402
    SEARCH_URL,
    SEARCH_URL_FALLBACK,
    TIKTOK_SEARCH_TIMEOUT_SECONDS,
    TikTokService,
    _create_api_sessions,
    _error_cache,
    _extract_raw_search_items,
    _get_playwright_session,
    _headless,
    _is_search_api_url,
    _parse_search_payload,
    _search_api_params,
    _search_page_url,
    _tiktok_cache,
    _browser_name,
    get_ms_tokens,
    get_proxies,
    get_tiktok_cookie_profiles,
)


def _mask(token: str) -> str:
    if len(token) <= 12:
        return "***"
    return f"{token[:6]}…{token[-4:]} (len={len(token)})"


def _print_config(tokens: list[str], proxies: list) -> None:
    print(f"env_file: {ENV_PATH} ({'found' if ENV_PATH.exists() else 'MISSING'})")
    print(f"browser: {_browser_name()}  headless={_headless()}")
    print(f"ms_tokens: {len(tokens)}")
    for i, token in enumerate(tokens[:5]):
        print(f"  [{i}] {_mask(token)}")
    if len(tokens) > 5:
        print(f"  … +{len(tokens) - 5} more")
    profiles = get_tiktok_cookie_profiles()
    print(f"cookie_profiles: {len(profiles)}")
    if profiles:
        keys = sorted(profiles[0].keys())
        print(f"  first_profile_cookies: {len(keys)} ({', '.join(keys[:12])}{'…' if len(keys) > 12 else ''})")
    print(f"proxies: {len(proxies)}")
    if not proxies:
        print(
            "note: no TIKTOK_PROXY / TIKTOK_PROXIES set. "
            "Empty/bot responses usually need a residential proxy even with a fresh msToken.",
        )


def _print_next_steps(*, has_proxy: bool) -> None:
    print()
    print("Next steps:")
    print("  1. Export full cookies while logged in (recommended):")
    print("       - Chrome: Cookie-Editor → Export JSON on tiktok.com")
    print("       - Save as videoscout/tiktok_cookies.json (or set TIKTOK_COOKIES_FILE)")
    print("       - See videoscout/tiktok_cookies.example.json")
    print("  2. Or copy msToken only: F12 → Application → Cookies → msToken")
    print("       → replace TIKTOK_MS_TOKEN in videoscout/.env")
    print("  3. Restart shell / re-source .env, run this script again with --no-cache.")
    if not has_proxy:
        print("  4. Add residential proxy, e.g. in videoscout/.env:")
        print("       TIKTOK_PROXY=http://user:pass@host:port")
        print("     Then re-run. Without proxy, empty/bot is common from home/DC IPs.")
    print("  5. Prefer a popular keyword first: --keyword aespa")
    print("     (obscure keywords can return 0 videos AFTER a healthy session.)")


async def _diagnose(keyword: str, *, limit: int, tokens: list[str], proxies: list) -> int:
    from TikTokApi import TikTokApi

    print()
    print("=== diagnose: create_sessions ===")
    async with TikTokApi() as api:
        await _create_api_sessions(
            api,
            ms_tokens=tokens,
            proxies=proxies or None,
        )
        sessions = getattr(api, "sessions", None) or getattr(api, "_sessions", None) or []
        print(f"sessions_created: {len(sessions)}")
        if not sessions:
            print("FAIL: TikTokApi created 0 sessions (token rejected or browser blocked).")
            _print_next_steps(has_proxy=bool(proxies))
            return 1

        print("=== diagnose: page navigation + capture search API ===")
        session_index, session = await _get_playwright_session(api)
        page = session.page
        url = _search_page_url(keyword)
        timeout_ms = int(TIKTOK_SEARCH_TIMEOUT_SECONDS * 1000)
        print(f"goto: {url}")

        captured_status: str | None = None
        captured_count = 0
        try:
            async with page.expect_response(
                lambda r: _is_search_api_url(r.url) and r.status == 200,
                timeout=timeout_ms,
            ) as response_info:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            resp = await response_info.value
            captured_status = f"{resp.status} {resp.url[:120]}"
            data = await resp.json()
            items = _extract_raw_search_items(data) if isinstance(data, dict) else []
            captured_count = len(items)
            print(f"captured_response: {captured_status}")
            print(f"captured_items: {captured_count}")
        except Exception as exc:
            print(f"capture_missed: {type(exc).__name__}: {exc}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                await asyncio.sleep(float(os.getenv("TIKTOK_SEARCH_WARM_SLEEP", "1.5")))
            except Exception as warm_exc:
                print(f"warmup_failed: {warm_exc}")

        try:
            title = await page.title()
        except Exception:
            title = "?"
        print(f"page_url: {page.url}")
        print(f"page_title: {title!r}")

        print("=== diagnose: make_request search APIs ===")
        params = _search_api_params(keyword, limit=limit)
        any_body = False
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
            except Exception as exc:
                print(f"  {search_url.rsplit('/', 2)[-2]}: EXCEPTION {exc}")
                continue
            if response is None:
                print(f"  {search_url.rsplit('/', 2)[-2]}: None (bot / blocked)")
                continue
            any_body = True
            n = len(_parse_search_payload(response, limit=limit))
            keys = list(response.keys())[:8] if isinstance(response, dict) else type(response)
            print(f"  {search_url.rsplit('/', 2)[-2]}: body_keys={keys} parsed_videos={n}")

        if captured_count > 0 or any_body:
            print("OK — session can talk to TikTok (diagnose path succeeded).")
            return 0

        print("FAIL: session up but TikTok returns empty (token stale and/or IP blocked).")
        _print_next_steps(has_proxy=bool(proxies))
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Test / diagnose TIKTOK_MS_TOKEN")
    parser.add_argument("--keyword", default="aespa", help='Search keyword (default: "aespa")')
    parser.add_argument("--limit", type=int, default=10, help="Max videos (default: 10)")
    parser.add_argument("--no-cache", action="store_true", help="Clear in-process caches")
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Step through create_sessions / page capture / make_request",
    )
    args = parser.parse_args()

    tokens = get_ms_tokens()
    proxies = get_proxies()
    _print_config(tokens, proxies)

    if not tokens:
        print("FAIL: no msToken loaded. Set TIKTOK_MS_TOKEN in videoscout/.env")
        return 1

    if args.no_cache:
        _tiktok_cache.clear()
        _error_cache.clear()
        print("cache: cleared")

    if args.diagnose:
        print("(visible WebKit window is normal when TIKTOK_HEADLESS=false)")
        return asyncio.run(
            _diagnose(args.keyword, limit=args.limit, tokens=tokens, proxies=proxies),
        )

    print(f"searching: {args.keyword!r} (limit={args.limit}) …")
    print("(visible WebKit window is normal when TIKTOK_HEADLESS=false)")

    result = TikTokService().search_videos(
        args.keyword,
        period="7d",
        limit=args.limit,
    )

    error = result.get("error")
    total = result.get("total_count", 0)
    print(f"error: {error}")
    print(f"total_count: {total}")
    print(f"avg_views: {result.get('avg_views')}")
    print(f"avg_likes: {result.get('avg_likes')}")
    print(f"rate_limited: {result.get('rate_limited', False)}")

    if error == "no_ms_token":
        print("FAIL: no_ms_token")
        return 1
    if error:
        print(f"FAIL: {error}")
        if "empty response" in str(error).lower() or "bot" in str(error).lower():
            print(
                "Interpretation: env token IS loaded, but TikTok rejected the Playwright "
                "session (stale msToken and/or IP reputation). Not a missing-.env issue.",
            )
        _print_next_steps(has_proxy=bool(proxies))
        return 1

    if total <= 0:
        print(
            "WARN: transport OK but 0 videos. Retry --keyword aespa; "
            "if still 0, treat as soft failure.",
        )
        print("OK (empty result)")
        return 0

    print("OK — msToken / session usable")
    return 0


if __name__ == "__main__":
    if os.getenv("TIKTOK_TEST_DEBUG", "").strip().lower() not in ("1", "true", "yes"):
        logging.getLogger("videoscout.services.tiktok").setLevel(logging.INFO)
    raise SystemExit(main())
