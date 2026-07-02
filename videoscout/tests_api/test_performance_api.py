"""Tests for performance report API endpoints."""
from videoscout.db.models import LearningEventModel


def test_submit_performance_report_creates_learning_event(client, db_session):
    response = client.post(
        "/api/v1/performance/reports",
        json={
            "keyword": "aespa winter",
            "actual_views": 4500,
            "actual_likes": 320,
            "actual_comments": 45,
            "followers_gained": 12,
            "outcome": "success",
            "notes": "Strong hook in first 3 seconds",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["keyword"] == "aespa winter"
    assert data["actual_views"] == 4500
    assert data["actual_likes"] == 320
    assert data["actual_comments"] == 45
    assert data["followers_gained"] == 12
    assert data["outcome"] == "success"
    assert data["engagement_rate"] > 0

    event = db_session.query(LearningEventModel).filter(
        LearningEventModel.type == "report",
        LearningEventModel.keyword == "aespa winter",
    ).first()
    assert event is not None
    assert event.actual_views == 4500
    assert event.outcome == "success"


def test_list_performance_reports_by_keyword(client):
    client.post(
        "/api/v1/performance/reports",
        json={
            "keyword": "aespa winter",
            "actual_views": 3200,
            "actual_likes": 220,
            "actual_comments": 20,
            "followers_gained": 9,
            "outcome": "success",
        },
    )
    client.post(
        "/api/v1/performance/reports",
        json={
            "keyword": "kpop dance",
            "actual_views": 2100,
            "actual_likes": 90,
            "actual_comments": 8,
            "followers_gained": 3,
            "outcome": "neutral",
        },
    )

    response = client.get("/api/v1/performance/reports?keyword=aespa")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["keyword"] == "aespa winter"
