"""TikTok scoring enrichment tests for US-011 / US-053."""
from datetime import datetime
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
    yield
    tiktok_module._tiktok_cache.clear()
    tiktok_module._error_cache.clear()
    tiktok_module._batch_session = None


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
    engine.tiktok = AsyncMock()
    engine.tiktok.search_videos.return_value = {
        "total_count": 15,
        "avg_views": 12000.0,
        "videos": [
            {"view_count": 10000, "like_count": 500, "comment_count": 30},
            {"view_count": 14000, "like_count": 700, "comment_count": 50},
        ],
    }

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
    with patch.object(tiktok_module, "_get_ms_token", return_value=None):
        result = TikTokService().search_videos("test keyword")
    assert result["total_count"] == 0
    assert result["error"] == "no_ms_token"


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

    async def fake_fetch(keyword, ms_token, *, limit):
        assert keyword == "ai tips"
        assert ms_token == "test-token"
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

    async def fake_batch(keyword, ms_token, *, limit):
        calls["count"] += 1
        return [{"view_count": 10, "like_count": 1, "comment_count": 0, "share_count": 0, "created_at": ""}]

    with patch.object(tiktok_module, "_fetch_search_videos_batch", side_effect=fake_batch):
        service.start_batch()
        try:
            first = service.search_videos("alpha keyword")
            second = service.search_videos("beta keyword phrase")
        finally:
            service.end_batch()

    assert calls["count"] == 2
    assert first["total_count"] == 1
    assert second["total_count"] == 1


def test_tiktok_service_caches_search_errors():
    service = TikTokService(ms_token="test-token")
    calls = {"n": 0}

    async def boom(keyword, ms_token, *, limit):
        calls["n"] += 1
        raise TimeoutError("timeout")

    with patch.object(tiktok_module, "_fetch_search_videos", side_effect=boom):
        first = service.search_videos("slow keyword phrase")
        second = service.search_videos("slow keyword phrase")

    assert first["error"] == "timeout"
    assert second["error"] == "timeout"
    assert calls["n"] == 1
