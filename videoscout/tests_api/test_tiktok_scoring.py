"""TikTok scoring enrichment tests for US-011."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from videoscout.core_engine.engine import SuggestionEngine
from videoscout.services.tiktok import TikTokService


def test_tiktok_service_computes_avg_likes_and_comments():
    service = TikTokService(api_key="test")
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

    result = service._process_response(data, days=7)

    assert result["total_count"] == 2
    assert result["avg_views"] == pytest.approx(2000.0)
    assert result["avg_likes"] == pytest.approx(200.0)
    assert result["avg_comments"] == pytest.approx(20.0)


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
