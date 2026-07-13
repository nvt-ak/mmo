"""Tests for Top-N evidence enrichment (US-063)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from videoscout.core_engine.evidence_enrichment import (
    TOP_N_ENRICHMENT,
    compute_supply_pressure,
    enrich_top_scored,
    load_tier1_channel,
    merge_enrichment_into_evidence,
)
from videoscout.core_engine.trend_evidence import EvidenceBuilder, serialize_evidence
from videoscout.db.models import ChannelModel


def _base_evidence(keyword: str = "business tips") -> dict:
    builder = EvidenceBuilder(pipeline_run_id="job-1", region="DE")
    return serialize_evidence(
        builder.build(
            keyword=keyword,
            source_video={
                "id": "vid1",
                "title": "Business Tips Today",
                "channel_id": "UC_known",
                "published_at": "2026-07-03T10:00:00Z",
                "view_count": 100_000,
                "category_id": "22",
                "velocity_raw": 2.0,
            },
            velocity_percentile=0.7,
        )
    )


def test_compute_supply_pressure_creator_diversity():
    youtube_videos = [
        {"channel_id": "UC1"},
        {"channel_id": "UC1"},
        {"channel_id": "UC2"},
    ]
    tiktok_result = {
        "total_count": 2,
        "videos": [
            {"author_id": "creator_a"},
            {"author_id": "creator_b"},
        ],
        "avg_engagement_rate": 0.05,
    }
    pressure = compute_supply_pressure(
        youtube_videos=youtube_videos,
        tiktok_result=tiktok_result,
    )
    assert pressure["youtube"]["video_count"] == 3
    assert pressure["youtube"]["unique_creators"] == 2
    assert pressure["youtube"]["creator_diversity"] == pytest.approx(2 / 3, rel=0.01)
    assert pressure["tiktok"]["unique_creators"] == 2
    assert pressure["pressure_score"] >= 0.0


def test_low_diversity_increases_pressure_score():
    concentrated = compute_supply_pressure(
        youtube_videos=[{"channel_id": "UC1"}] * 10,
        tiktok_result={"total_count": 0, "videos": []},
    )
    spread = compute_supply_pressure(
        youtube_videos=[{"channel_id": f"UC{i}"} for i in range(10)],
        tiktok_result={"total_count": 0, "videos": []},
    )
    assert concentrated["pressure_score"] > spread["pressure_score"]


def test_merge_enrichment_sets_tier_and_supply_pressure():
    evidence = _base_evidence()
    merged = merge_enrichment_into_evidence(
        evidence,
        channel_raw={"tier": 1, "channel_id": "UC_known", "subscriber_count": 5000},
        youtube_search_raw={
            "keyword": "business tips",
            "days": 7,
            "videos": [
                {
                    "video_id": "v1",
                    "title": "Business Tips Today",
                    "channel_id": "c1",
                    "view_count": 1000,
                    "published_at": "2026-07-01T00:00:00Z",
                }
            ],
            "population_contexts": [{
                "sample_size": 1,
                "estimated_result_count": 5000,
                "query_used": "business tips",
                "search_order": "date",
                "time_window_days": 7,
                "ranking_bias": "recency_ranked",
            }],
        },
        tiktok_raw={"keyword": "business tips", "total_count": 5, "videos": []},
        supply_pressure={"pressure_score": 0.4},
        keyword="business tips",
        source_title="Business Tips Today",
    )
    assert merged["schema_version"] == "2"
    assert merged["metadata"]["enrichment_tier"] == 2
    assert merged["raw"]["channel"]["tier"] == 1
    assert merged["derived"]["supply_pressure"]["pressure_score"] == 0.4
    assert merged["derived"]["search_sample"]["youtube"]["sample_size"] == 1
    assert "lifecycle" not in merged


def test_load_tier1_channel_from_db(db_session):
    db_session.add(
        ChannelModel(
            channel_id="UC_known",
            name="Known Channel",
            subscriber_count=12_000,
            last_video_count=45,
        )
    )
    db_session.commit()
    row = load_tier1_channel(db_session, "UC_known")
    assert row is not None
    assert row["tier"] == 1
    assert row["subscriber_count"] == 12_000
    assert load_tier1_channel(db_session, "UC_missing") is None


@pytest.mark.asyncio
async def test_enrich_top_scored_only_top_n(db_session):
    from videoscout.core_engine.evidence_enrichment import enrich_scored_candidate

    scored = [
        {
            "keyword": f"keyword {i}",
            "final_score": i / 10.0,
            "trend_evidence": _base_evidence(f"keyword {i}"),
            "platform_signals": {"agent": {"scored_with": "test"}},
            "component_scores": {},
            "tiktok_stats": {},
        }
        for i in range(1, 15)
    ]
    engine = MagicMock()

    with patch(
        "videoscout.core_engine.evidence_enrichment.enrich_scored_candidate",
        new_callable=AsyncMock,
    ) as mock_enrich:
        mock_enrich.side_effect = lambda row, **kwargs: {**row, "enriched": True}
        result = await enrich_top_scored(
            scored,
            db=db_session,
            engine=engine,
            top_n=10,
        )
    assert mock_enrich.await_count == 10
    enriched_count = sum(1 for row in result if row.get("enriched"))
    assert enriched_count == 10
