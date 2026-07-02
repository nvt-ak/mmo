"""Tests for learning API endpoints."""
from datetime import datetime, timedelta
import uuid


def _insert_reported_suggestion(db_session, outcome="success", views=5000, likes=300):
    """Helper: insert a suggestion that is already approved + reported."""
    from videoscout.db.models import SuggestionModel, LearningEventModel

    s = SuggestionModel(
        keyword=f"test keyword {uuid.uuid4().hex[:6]}",
        final_score=0.72,
        component_scores={
            "relevance": 0.80, "specificity": 0.70,
            "saturation": 0.60, "trend": 0.50, "video_performance": 0.75
        },
        suggested_by=[{"source": "digest_scan", "score": 0.72, "timestamp": "2026-07-01T05:00:00"}],
        status="reported",
        reported_at=datetime.utcnow(),
        actual_views=views,
        actual_likes=likes,
        outcome=outcome
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)

    evt = LearningEventModel(
        type="report",
        keyword=s.keyword,
        outcome=outcome,
        predicted_score=0.72,
        actual_views=views,
        actual_engagement_rate=likes / views if views else 0,
        scores=s.component_scores,
        final_score=0.72,
        timestamp=datetime.utcnow(),
        suggestion_id=s.id
    )
    db_session.add(evt)
    db_session.commit()
    return s


def test_insights_empty(client):
    resp = client.get("/api/v1/learning/insights")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary_metrics"]["total_rejections"] == 0
    assert data["summary_metrics"]["total_reports"] == 0


def test_insights_with_rejection(client, sample_suggestion, db_session):
    # Create rejection event
    client.post("/api/v1/suggestions/bulk-reject", json={
        "keyword_ids": [str(sample_suggestion.id)],
        "reason": "too_broad"
    })
    resp = client.get("/api/v1/learning/insights")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary_metrics"]["total_rejections"] == 1


def test_learning_cycle_no_data(client):
    resp = client.post("/api/v1/learning/cycle")
    assert resp.status_code == 200
    data = resp.json()
    assert "report_id" in data
    assert data["adjustments_made"] == 0


def test_insights_prediction_error(client, db_session):
    _insert_reported_suggestion(db_session, outcome="success")
    resp = client.get("/api/v1/learning/insights")
    data = resp.json()
    assert data["summary_metrics"]["total_reports"] == 1
    assert data["summary_metrics"]["avg_prediction_error"] >= 0
