"""Tests for dual-source candidate generator (US-064)."""
from unittest.mock import MagicMock, patch

from videoscout.core_engine.candidate_generator import (
    fetch_discovery_sources,
    iter_scored_source_videos,
)


def test_iter_scored_source_videos_keeps_sources_separate():
    sources = [
        ("most_popular", [{
            "id": "a",
            "title": "Popular Video",
            "channel_id": "UC1",
            "published_at": "2026-07-03T08:00:00Z",
            "view_count": 100_000,
            "category_id": "22",
        }]),
        ("velocity", [{
            "id": "b",
            "title": "Emerging Video",
            "channel_id": "UC2",
            "published_at": "2026-07-03T09:00:00Z",
            "view_count": 50_000,
            "category_id": "22",
        }]),
    ]
    rows = list(iter_scored_source_videos(sources, region_code="DE"))
    assert len(rows) == 2
    kinds = {kind for kind, _, _ in rows}
    assert kinds == {"most_popular", "velocity"}
    for _, video, percentiles in rows:
        assert video.get("velocity_raw") is not None
        assert percentiles.get(video["id"]) is not None


def test_fetch_discovery_sources_returns_two_feeds(db_session):
    popular = [{"id": "p1", "title": "Popular"}]
    velocity = [{"id": "v1", "title": "Velocity"}]
    mock_yt = MagicMock()
    mock_yt.get_trending_videos.return_value = popular
    mock_yt.get_emergence_videos.return_value = velocity

    with patch(
        "videoscout.core_engine.candidate_generator.get_youtube_service",
        return_value=mock_yt,
    ):
        feeds = fetch_discovery_sources(
            region_code="DE",
            popular_limit=10,
            velocity_limit=10,
            db=db_session,
        )

    assert feeds[0][0] == "most_popular"
    assert feeds[1][0] == "velocity"
    assert feeds[0][1] == popular
    assert feeds[1][1] == velocity
