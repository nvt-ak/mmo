"""Tests for Google Trends discovery service (US-078)."""
from unittest.mock import MagicMock, patch

import pandas as pd

from videoscout.core_engine.candidate_generator import (
    fetch_discovery_sources,
    fetch_google_trends_candidates,
)
from videoscout.core_engine.trend_evidence import (
    EvidenceBuilder,
    LifecycleClassifier,
    serialize_evidence,
)
from videoscout.services.google_trends import (
    GoogleTrendsService,
    _SURFACE_WEB_WORLDWIDE,
    _SURFACE_YOUTUBE_REGIONAL,
    _parse_growth_value,
    google_trends_geo,
    google_trends_replace_emergence,
    reset_google_trends_service,
    rising_query_attempts,
    trend_seeds_from_db,
)


def test_parse_growth_value():
    assert _parse_growth_value("Breakout") == "breakout"
    assert _parse_growth_value("+450%") == 450
    assert _parse_growth_value(None) is None


def test_google_trends_geo_defaults_worldwide(monkeypatch):
    monkeypatch.delenv("GOOGLE_TRENDS_GEO", raising=False)
    assert google_trends_geo() == ""


def test_google_trends_geo_normalizes_worldwide_label(monkeypatch):
    monkeypatch.setenv("GOOGLE_TRENDS_GEO", "Worldwide")
    assert google_trends_geo() == ""


def test_trend_seeds_from_db_uses_niche_topics():
    assert trend_seeds_from_db(["K-Pop", "Dance"]) == ["k-pop", "dance"]
    seeds = trend_seeds_from_db([])
    assert len(seeds) >= 3


def test_fetch_rising_keywords_dedupes_and_limits():
    rising_df = pd.DataFrame([
        {"query": "viral dance challenge", "value": "Breakout"},
        {"query": "viral dance challenge", "value": "+200%"},
        {"query": "new sound remix", "value": "+120%"},
    ])
    service = GoogleTrendsService(geo="", gprop="youtube")
    mock_client = MagicMock()
    mock_client.related_queries.return_value = {
        "music": {"rising": rising_df, "top": None},
    }
    service._client = mock_client

    with patch.object(service, "_fetch_rising_dataframe", return_value=rising_df):
        rows = service.fetch_rising_keywords(["music"], limit=5)

    assert len(rows) == 2
    assert rows[0]["keyword"] == "viral dance challenge"
    assert rows[0]["gprop"] == ""
    assert rows[0]["surface_mode"] == _SURFACE_WEB_WORLDWIDE
    assert rows[0]["gprop_requested"] == "youtube"
    assert rows[0]["growth_pct"] == "breakout"


def test_rising_query_attempts_worldwide_youtube_falls_back_to_web():
    attempts = rising_query_attempts(geo="", gprop="youtube", youtube_geo_fallback="")
    assert attempts == [("", "", _SURFACE_WEB_WORLDWIDE)]


def test_rising_query_attempts_worldwide_youtube_with_regional_first():
    attempts = rising_query_attempts(geo="", gprop="youtube", youtube_geo_fallback="US")
    assert attempts[0] == ("US", "youtube", _SURFACE_YOUTUBE_REGIONAL)
    assert attempts[1] == ("", "", _SURFACE_WEB_WORLDWIDE)


def test_build_from_trends_evidence():
    builder = EvidenceBuilder(pipeline_run_id="job-1", region="DE")
    evidence = builder.build_from_trends(
        keyword="viral dance challenge",
        trends_raw={
            "keyword": "viral dance challenge",
            "geo": "",
            "gprop": "youtube",
            "interest_index": 80,
            "growth_pct": "breakout",
            "query_type": "rising",
            "seed_keyword": "music",
        },
    )
    serialized = serialize_evidence(evidence)
    assert serialized["provenance"]["source"] == "google_trends"
    assert serialized["raw"]["google_trends"]["gprop"] == "youtube"
    assert serialized["raw"]["youtube"] is None
    assert LifecycleClassifier.classify(serialized) == "early_accelerating"


def test_fetch_google_trends_candidates_disabled(monkeypatch, db_session):
    monkeypatch.setenv("GOOGLE_TRENDS_ENABLED", "false")
    reset_google_trends_service()
    assert fetch_google_trends_candidates(db_session, limit=10) == []


def test_fetch_google_trends_candidates_mocked(db_session):
    reset_google_trends_service()
    mock_rows = [{
        "keyword": "trending sound slowed",
        "geo": "",
        "gprop": "youtube",
        "interest_index": 60,
        "growth_pct": 300,
        "query_type": "rising",
        "seed_keyword": "music",
    }]
    with patch(
        "videoscout.services.google_trends.get_google_trends_service",
    ) as mock_get:
        mock_get.return_value.fetch_rising_keywords.return_value = mock_rows
        rows = fetch_google_trends_candidates(db_session, limit=10)
    assert len(rows) == 1
    assert rows[0]["keyword"] == "trending sound slowed"


def test_fetch_discovery_sources_skips_emergence_when_trends_replace(monkeypatch, db_session):
    monkeypatch.setenv("GOOGLE_TRENDS_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_TRENDS_REPLACE_EMERGENCE", "true")
    reset_google_trends_service()
    assert google_trends_replace_emergence() is True

    popular = [{"id": "p1", "title": "Popular"}]
    mock_yt = MagicMock()
    mock_yt.get_trending_videos.return_value = popular

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

    assert len(feeds) == 1
    assert feeds[0][0] == "most_popular"
    mock_yt.get_emergence_videos.assert_not_called()
