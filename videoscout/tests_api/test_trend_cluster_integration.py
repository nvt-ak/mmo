"""Integration tests for trend cluster persistence and inbox API (US-066)."""
import uuid

from videoscout.db.models import SuggestionModel, TrendClusterModel


def test_suggestions_api_returns_cluster_metadata(client, db_session):
    cluster = TrendClusterModel(
        id=uuid.uuid4(),
        canonical_keyword="home workout routine",
        member_keywords=["home workout routine", "home workout routines"],
        member_keyword_ids=[],
    )
    db_session.add(cluster)
    db_session.flush()

    canonical = SuggestionModel(
        keyword="home workout routine",
        final_score=0.82,
        component_scores={
            "relevance": 0.8,
            "specificity": 0.8,
            "saturation": 0.7,
            "trend": 0.8,
            "video_performance": 0.7,
        },
        suggested_by=[{"source": "trend_discovery", "score": 0.82, "timestamp": "2026-07-13T00:00:00"}],
        status="pending",
        keyword_type="nurture",
        cluster_id=cluster.id,
    )
    variant = SuggestionModel(
        keyword="home workout routines",
        final_score=0.71,
        component_scores={
            "relevance": 0.75,
            "specificity": 0.75,
            "saturation": 0.7,
            "trend": 0.7,
            "video_performance": 0.65,
        },
        suggested_by=[{"source": "trend_discovery", "score": 0.71, "timestamp": "2026-07-13T00:00:00"}],
        status="pending",
        keyword_type="nurture",
        cluster_id=cluster.id,
    )
    db_session.add_all([canonical, variant])
    cluster.member_keyword_ids = []
    db_session.commit()

    response = client.get("/api/v1/suggestions?keyword_type=nurture&status=pending")
    assert response.status_code == 200
    payload = response.json()
    clustered = [row for row in payload["items"] if row.get("cluster_id") == str(cluster.id)]
    assert len(clustered) == 2
    assert all(row["cluster_canonical_keyword"] == "home workout routine" for row in clustered)
    assert all(row["cluster_member_count"] == 2 for row in clustered)
    assert sum(1 for row in clustered if row["is_cluster_canonical"]) == 1


def test_cluster_persistence_round_trip(db_session):
    cluster = TrendClusterModel(
        canonical_keyword="skincare routine night",
        member_keywords=["skincare routine night", "night skincare routine"],
        member_keyword_ids=[],
        pipeline_run_id=uuid.uuid4(),
    )
    db_session.add(cluster)
    db_session.commit()

    loaded = db_session.query(TrendClusterModel).filter_by(id=cluster.id).one()
    assert loaded.canonical_keyword == "skincare routine night"
    assert len(loaded.member_keywords) == 2
