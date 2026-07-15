"""TikTok scoring enrichment tests for US-011 / US-053."""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from videoscout.core_engine.engine import SuggestionEngine
from videoscout.services import tiktok as tiktok_module
from videoscout.services.tiktok import TikTokService


@pytest.fixture(autouse=True)
def clear_tiktok_cache():
    tiktok_module._tiktok_cache.clear()
    tiktok_module._error_cache.clear()
    tiktok_module._batch_session = None
    tiktok_module._reset_search_pacing()
    yield
    tiktok_module._tiktok_cache.clear()
    tiktok_module._error_cache.clear()
    tiktok_module._batch_session = None
    tiktok_module._reset_search_pacing()


def test_search_page_url_encodes_query():
    url = tiktok_module._search_page_url("ảnh avatar")
    assert url.startswith("https://www.tiktok.com/search?q=")
    assert "t=" in url
    assert "%" in url.split("q=", 1)[1]


def test_search_api_params_match_tiktok_api():
    params = tiktok_module._search_api_params("test keyword", limit=20)
    assert params["from_page"] == "search"
    assert params["keyword"] == "test keyword"
    assert params["count"] == 20
    assert params["offset"] == 0
    assert params["search_source"] == "recom_search"
    assert params["is_non_personalized_search"] == 0
    assert "web_search_code" in params


def test_extract_raw_search_items_general_payload():
    now_ts = int(datetime.utcnow().timestamp())
    payload = {
        "data": [
            {"type": 4, "user_info": {"unique_id": "someuser"}},
            {
                "type": 1,
                "item": {
                    "createTime": now_ts,
                    "stats": {
                        "playCount": 100,
                        "diggCount": 10,
                        "commentCount": 1,
                        "shareCount": 0,
                    },
                },
            },
        ],
    }
    items = tiktok_module._extract_raw_search_items(payload)
    assert len(items) == 1
    parsed = tiktok_module._parse_search_payload(payload, limit=10)
    assert parsed[0]["view_count"] == 100


def test_extract_raw_search_items_item_list_payload():
    now_ts = int(datetime.utcnow().timestamp())
    payload = {
        "item_list": [{
            "createTime": now_ts,
            "stats": {"playCount": 42, "diggCount": 4, "commentCount": 1, "shareCount": 0},
        }],
    }
    assert len(tiktok_module._extract_raw_search_items(payload)) == 1


def test_tiktok_service_computes_avg_likes_and_comments():
    service = TikTokService()
    now_iso = datetime.utcnow().isoformat() + "Z"
    data = {
        "videos": [
            {
                "created_at": now_iso,
                "view_count": 1000,
                "like_count": 100,
                "comment_count": 10,
                "share_count": 5,
            },
            {
                "created_at": now_iso,
                "view_count": 3000,
                "like_count": 300,
                "comment_count": 30,
                "share_count": 10,
            },
        ]
    }

    result = service._process_response(data, days=7, cache_key="test:7d:50")

    assert result["total_count"] == 2
    assert result["avg_views"] == pytest.approx(2000.0)
    assert result["avg_likes"] == pytest.approx(200.0)
    assert result["avg_comments"] == pytest.approx(20.0)


def test_tiktok_service_handles_null_json_body():
    service = TikTokService()
    assert service._process_response(None, days=7, cache_key="null:7d:50")["total_count"] == 0
    assert service._process_response({"videos": None}, days=7, cache_key="nv:7d:50")["total_count"] == 0
    assert service._process_response({"videos": [None, {"view_count": 1}]}, days=7, cache_key="mix:7d:50")["total_count"] == 1


@pytest.mark.asyncio
async def test_score_keywords_includes_tiktok_stats():
    engine = SuggestionEngine(llm_client=MagicMock(), db_session=MagicMock())
    engine.tiktok = MagicMock()
    engine.tiktok.search_videos_async = AsyncMock(return_value={
        "total_count": 15,
        "avg_views": 12000.0,
        "videos": [
            {"view_count": 10000, "like_count": 500, "comment_count": 30},
            {"view_count": 14000, "like_count": 700, "comment_count": 50},
        ],
    })

    candidates = [
        {
            "keyword": "ai marketing strategy",
            "source": "transcript",
            "llm_confidence": 0.9,
            "rationale": "specific and action-oriented",
            "video_id": "vid_001",
            "channel_id": "UC_test",
        }
    ]
    video_context = {
        "video_id": "vid_001",
        "channel_id": "UC_test",
        "title": "AI marketing strategy for 2026",
        "description": "Detailed breakdown",
        "tags": ["ai", "marketing"],
        "transcript": [{"text": "ai marketing strategy", "start": 1.0}],
        "view_count": 5000,
        "like_count": 250,
        "comment_count": 25,
    }

    scored = await engine.score_keywords(candidates, video_context)

    assert len(scored) == 1
    stats = scored[0]["tiktok_stats"]
    assert stats["video_count_7d"] == 15
    assert stats["avg_views"] == pytest.approx(12000.0)
    assert stats["avg_likes"] == pytest.approx(600.0)
    assert stats["avg_comments"] == pytest.approx(40.0)
    assert stats["saturation_tier"] == "moderate"
    assert scored[0]["tiktok_count"] == 15
    assert scored[0]["tiktok_status"] == "moderate"


def test_tiktok_service_no_ms_token_returns_error():
    with patch.object(tiktok_module, "get_ms_tokens", return_value=[]):
        result = TikTokService().search_videos("test keyword")
    assert result["total_count"] == 0
    assert result["error"] == "no_ms_token"


def test_get_ms_tokens_merges_env_and_dedupes(monkeypatch):
    monkeypatch.setenv("TIKTOK_MS_TOKEN", "token-a")
    monkeypatch.setenv("TIKTOK_MS_TOKENS", "token-b,token-a")
    monkeypatch.delenv("TIKTOK_MS_TOKEN_FILE", raising=False)
    monkeypatch.delenv("TIKTOK_COOKIES_FILE", raising=False)
    with patch.object(tiktok_module, "DEFAULT_MS_TOKEN_FILE", Path("/nonexistent/ms_tokens.txt")):
        with patch.object(
            tiktok_module,
            "DEFAULT_COOKIES_FILE",
            Path("/nonexistent/tiktok_cookies.json"),
        ):
            assert tiktok_module.get_ms_tokens() == ["token-a", "token-b"]


def test_parse_cookie_editor_export_keeps_longest_mstoken():
    payload = [
        {"name": "msToken", "value": "short", "domain": "www.tiktok.com"},
        {"name": "msToken", "value": "much-longer-mstoken-value", "domain": ".tiktok.com"},
        {"name": "sessionid", "value": "sid123", "domain": ".tiktok.com"},
    ]
    profiles = tiktok_module.parse_tiktok_cookies_payload(payload)
    assert len(profiles) == 1
    assert profiles[0]["msToken"] == "much-longer-mstoken-value"
    assert profiles[0]["sessionid"] == "sid123"


def test_parse_playwright_storage_state():
    payload = {
        "cookies": [
            {"name": "msToken", "value": "tok", "domain": ".tiktok.com", "path": "/"},
            {"name": "ttwid", "value": "tt", "domain": ".tiktok.com", "path": "/"},
        ]
    }
    profiles = tiktok_module.parse_tiktok_cookies_payload(payload)
    assert profiles == [{"msToken": "tok", "ttwid": "tt"}]


def test_get_ms_tokens_reads_from_cookies_file(monkeypatch, tmp_path):
    cookie_path = tmp_path / "cookies.json"
    cookie_path.write_text(
        json.dumps([{"name": "msToken", "value": "from-file", "domain": ".tiktok.com"}]),
        encoding="utf-8",
    )
    monkeypatch.delenv("TIKTOK_MS_TOKEN", raising=False)
    monkeypatch.delenv("TIKTOK_MS_TOKENS", raising=False)
    monkeypatch.delenv("TIKTOK_MS_TOKEN_FILE", raising=False)
    monkeypatch.setenv("TIKTOK_COOKIES_FILE", str(cookie_path))
    with patch.object(tiktok_module, "DEFAULT_MS_TOKEN_FILE", Path("/nonexistent/x.txt")):
        assert tiktok_module.get_ms_tokens() == ["from-file"]


@pytest.mark.asyncio
async def test_create_api_sessions_passes_cookie_profiles(monkeypatch):
    monkeypatch.setenv("TIKTOK_BROWSER", "webkit")
    monkeypatch.setenv("TIKTOK_NUM_SESSIONS", "2")
    api = AsyncMock()
    profiles = [{"msToken": "tok", "sessionid": "sid"}]
    await tiktok_module._create_api_sessions(
        api,
        ms_tokens=["tok"],
        cookie_profiles=profiles,
    )
    kwargs = api.create_sessions.await_args.kwargs
    assert kwargs["cookies"] == profiles
    assert kwargs["ms_tokens"] == ["tok"]


def test_get_proxies_builds_playwright_dict(monkeypatch):
    monkeypatch.setenv("TIKTOK_PROXY", "http://user:pass@proxy.example:8080")
    proxies = tiktok_module.get_proxies()
    assert proxies == [{
        "server": "http://proxy.example:8080",
        "username": "user",
        "password": "pass",
    }]


@pytest.mark.asyncio
async def test_create_api_sessions_passes_pool_config(monkeypatch):
    monkeypatch.setenv("TIKTOK_BROWSER", "webkit")
    monkeypatch.setenv("TIKTOK_NUM_SESSIONS", "2")
    api = AsyncMock()
    await tiktok_module._create_api_sessions(
        api,
        ms_tokens=["token-a", "token-b", "token-c"],
    )
    api.create_sessions.assert_awaited_once()
    kwargs = api.create_sessions.await_args.kwargs
    assert kwargs["browser"] == "webkit"
    assert kwargs["headless"] is False
    assert kwargs["num_sessions"] == 2
    assert kwargs["ms_tokens"] == ["token-a", "token-b", "token-c"]


@pytest.mark.asyncio
async def test_tiktok_service_search_via_mstoken():
    service = TikTokService(ms_token="test-token")
    now_ts = int(datetime.utcnow().timestamp())
    mock_items = [
        {
            "createTime": now_ts,
            "stats": {
                "playCount": 1000,
                "diggCount": 100,
                "commentCount": 10,
                "shareCount": 5,
            },
        },
        {
            "createTime": now_ts,
            "stats": {
                "playCount": 2000,
                "diggCount": 200,
                "commentCount": 20,
                "shareCount": 10,
            },
        },
    ]

    async def fake_fetch(keyword, ms_tokens, *, limit, proxies=None):
        assert keyword == "ai tips"
        assert ms_tokens == ["test-token"]
        return [tiktok_module._parse_search_item(item) for item in mock_items]

    with patch.object(tiktok_module, "_fetch_search_videos", side_effect=fake_fetch):
        result = service.search_videos("ai tips", period="7d", limit=30)

    assert result["total_count"] == 2
    assert result["avg_views"] == pytest.approx(1500.0)
    assert result["avg_likes"] == pytest.approx(150.0)
    assert "error" not in result


def test_tiktok_service_batch_reuses_fetcher():
    service = TikTokService(ms_token="test-token")
    calls = {"count": 0}

    async def fake_batch(keyword, ms_tokens, *, limit, proxies=None):
        calls["count"] += 1
        return [{"view_count": 10, "like_count": 1, "comment_count": 0, "share_count": 0, "created_at": ""}]

    async def run_batch():
        with patch.object(tiktok_module, "_fetch_search_videos_batch", side_effect=fake_batch):
            service.start_batch()
            try:
                first = await service.search_videos_async("alpha keyword")
                second = await service.search_videos_async("beta keyword phrase")
            finally:
                await service.end_batch_async()
        return first, second

    first, second = asyncio.run(run_batch())

    assert calls["count"] == 2
    assert first["total_count"] == 1
    assert second["total_count"] == 1


def test_tiktok_service_caches_search_errors():
    service = TikTokService(ms_token="test-token")
    calls = {"n": 0}

    async def boom(keyword, ms_tokens, *, limit, proxies=None):
        calls["n"] += 1
        raise TimeoutError("timeout")

    with patch.object(tiktok_module, "_fetch_search_videos", side_effect=boom):
        first = service.search_videos("slow keyword phrase")
        second = service.search_videos("slow keyword phrase")

    assert first["error"] == "timeout"
    assert second["error"] == "timeout"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_tiktok_service_retries_with_next_token():
    service = TikTokService(ms_tokens=["bad-token", "good-token"])
    calls = {"n": 0}

    async def fake_fetch(keyword, ms_tokens, *, limit, proxies=None):
        calls["n"] += 1
        if ms_tokens[0] == "bad-token":
            raise RuntimeError("blocked")
        return [{"view_count": 5, "like_count": 1, "comment_count": 0, "share_count": 0, "created_at": ""}]

    with patch.object(tiktok_module, "_fetch_search_videos", side_effect=fake_fetch):
        result = await service.search_videos_async("retry keyword phrase")

    assert result["total_count"] == 1
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_tiktok_service_retries_single_token(monkeypatch):
    monkeypatch.setenv("TIKTOK_SEARCH_RETRIES", "3")
    service = TikTokService(ms_token="solo-token")
    calls = {"n": 0}

    async def fake_fetch(keyword, ms_tokens, *, limit, proxies=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("bot blocked")
        return [{"view_count": 5, "like_count": 1, "comment_count": 0, "share_count": 0, "created_at": ""}]

    with patch.object(tiktok_module, "_fetch_search_videos", side_effect=fake_fetch):
        result = await service.search_videos_async("retry solo keyword")

    assert result["total_count"] == 1
    assert calls["n"] == 3


def test_target_pre_search_delay_includes_typing(monkeypatch):
    monkeypatch.setenv("TIKTOK_SEARCH_INTERVAL_MIN_SECONDS", "8")
    monkeypatch.setenv("TIKTOK_SEARCH_INTERVAL_MAX_SECONDS", "10")
    monkeypatch.setenv("TIKTOK_SEARCH_TYPING_SECONDS_PER_CHAR", "0.1")
    with patch("videoscout.services.tiktok.random.uniform", return_value=9.0):
        delay = tiktok_module._target_pre_search_delay("abcd")
    assert delay == pytest.approx(9.4)


@pytest.mark.asyncio
async def test_pace_before_search_waits_when_too_soon(monkeypatch):
    monkeypatch.setenv("TIKTOK_SEARCH_PACING", "true")
    monkeypatch.setenv("TIKTOK_SEARCH_INTERVAL_MIN_SECONDS", "10")
    monkeypatch.setenv("TIKTOK_SEARCH_INTERVAL_MAX_SECONDS", "10")
    monkeypatch.setenv("TIKTOK_SEARCH_TYPING_SECONDS_PER_CHAR", "0")
    tiktok_module._mark_search_paced()
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    with patch("videoscout.services.tiktok.random.uniform", return_value=10.0):
        with patch("videoscout.services.tiktok.asyncio.sleep", side_effect=record_sleep):
            await tiktok_module._pace_before_search("test keyword")

    assert len(sleeps) == 1
    assert sleeps[0] > 0


@pytest.mark.asyncio
async def test_pace_before_search_skipped_when_disabled(monkeypatch):
    monkeypatch.setenv("TIKTOK_SEARCH_PACING", "false")
    with patch("videoscout.services.tiktok.asyncio.sleep", new_callable=AsyncMock) as sleep_mock:
        await tiktok_module._pace_before_search("test keyword")
    sleep_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_videos_async_paces_uncached_requests(monkeypatch):
    monkeypatch.setenv("TIKTOK_SEARCH_PACING", "true")
    monkeypatch.setenv("TIKTOK_SEARCH_INITIAL_DELAY_MIN_SECONDS", "0")
    monkeypatch.setenv("TIKTOK_SEARCH_INITIAL_DELAY_MAX_SECONDS", "0")
    monkeypatch.setenv("TIKTOK_SEARCH_POST_DWELL_MIN_SECONDS", "0")
    monkeypatch.setenv("TIKTOK_SEARCH_POST_DWELL_MAX_SECONDS", "0")
    service = TikTokService(ms_token="test-token")
    pace_calls: list[str] = []

    async def fake_pace(keyword: str) -> None:
        pace_calls.append(keyword)

    async def fake_fetch(keyword, ms_tokens, *, limit, proxies=None):
        return [{"view_count": 1, "like_count": 0, "comment_count": 0, "share_count": 0, "created_at": ""}]

    with patch.object(tiktok_module, "_pace_before_search", side_effect=fake_pace):
        with patch.object(tiktok_module, "_fetch_search_videos", side_effect=fake_fetch):
            await service.search_videos_async("paced keyword")
    assert pace_calls == ["paced keyword"]
