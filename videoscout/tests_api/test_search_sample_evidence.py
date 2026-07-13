"""Tests for search-sample evidence (US-065)."""
import pytest

from videoscout.core_engine.search_sample import (
    build_search_queries,
    compute_distribution_stats,
    compute_representation_quality,
    merge_search_sample_evidence,
)
from videoscout.core_engine.trend_evidence import EvidenceBuilder, serialize_evidence


def test_compute_distribution_detects_viral_outlier():
    videos = [
        {"view_count": 12_000_000, "channel_id": "c1", "published_at": "2026-07-01T00:00:00Z"},
        {"view_count": 8_000, "channel_id": "c2", "published_at": "2026-07-02T00:00:00Z"},
        {"view_count": 7_000, "channel_id": "c3", "published_at": "2026-07-02T01:00:00Z"},
        {"view_count": 6_000, "channel_id": "c4", "published_at": "2026-07-02T02:00:00Z"},
        {"view_count": 5_000, "channel_id": "c5", "published_at": "2026-07-02T03:00:00Z"},
    ]
    stats = compute_distribution_stats(videos)
    assert stats["viral_outlier"] is True
    assert stats["median_views"] == pytest.approx(7000, rel=0.01)
    assert stats["median_views"] < 100_000
    assert stats["top_contribution_pct"] > 90


def test_build_search_queries_strips_generic_tokens():
    queries = build_search_queries(
        "viral trending dance bollywood",
        "Saiyaara Official Dance #shorts",
    )
    assert "viral trending dance bollywood" in queries
    assert any("dance bollywood" in q for q in queries)
    assert any("saiyaara" in q for q in queries)


def test_merge_search_sample_sets_schema_v2():
    builder = EvidenceBuilder(pipeline_run_id="job-1", region="DE")
    evidence = serialize_evidence(
        builder.build(
            keyword="saiyaara dance",
            source_video={
                "id": "v1",
                "title": "Saiyaara Dance Trend",
                "channel_id": "UC1",
                "published_at": "2026-07-03T10:00:00Z",
                "view_count": 1_000_000,
            },
        )
    )
    videos = [
        {
            "video_id": "a",
            "title": "Saiyaara dance challenge",
            "channel_id": "c1",
            "view_count": 5000,
            "published_at": "2026-07-01T00:00:00Z",
        },
        {
            "video_id": "b",
            "title": "Saiyaara dance remix",
            "channel_id": "c2",
            "view_count": 7000,
            "published_at": "2026-07-02T00:00:00Z",
        },
    ]
    merged = merge_search_sample_evidence(
        evidence,
        youtube_videos=videos,
        youtube_population_contexts=[{
            "sample_size": 2,
            "estimated_result_count": 120_000,
            "query_used": "saiyaara dance",
            "search_order": "date",
            "time_window_days": 7,
            "ranking_bias": "recency_ranked",
            "newest_upload": "2026-07-02T00:00:00Z",
            "oldest_upload": "2026-07-01T00:00:00Z",
        }],
        tiktok_videos=[],
        tiktok_population_context=None,
        search_queries_used=["saiyaara dance"],
        source_title="Saiyaara Dance Trend",
        keyword="saiyaara dance",
    )
    assert merged["schema_version"] == "2"
    assert merged["derived"]["search_sample"]["youtube"]["sample_size"] == 2
    assert merged["derived"]["population_context"]["youtube"][0]["estimated_result_count"] == 120_000
    assert merged["derived"]["representation_quality"]["representation_confidence"] in (
        "high",
        "mixed",
        "low",
    )


def test_representation_quality_low_for_unrelated_titles():
    rq = compute_representation_quality(
        "saiyaara dance",
        "Saiyaara Dance Trend",
        ["Random cooking tips", "Car review 2026"],
    )
    assert rq["representation_confidence"] == "low"
    assert rq["pattern_purity"] < 0.5
