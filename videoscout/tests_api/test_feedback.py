"""Tests for R6 feedback loop API."""
from datetime import datetime

from videoscout.db.models import (
    FinalVideoModel,
    PerformanceReportModel,
    SuggestionModel,
)


def test_feedback_accuracy_empty(client):
    resp = client.get("/api/v1/feedback/accuracy")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_reports"] == 0
    assert body["pending_finals"] == 0


def test_performance_report_links_final_and_marks_suggestion(client, db_session, sample_suggestion):
    sample_suggestion.status = "approved"
    db_session.commit()

    final = FinalVideoModel(
        file_path="data/finals/test-final.mp4",
        keyword=sample_suggestion.keyword,
        suggestion_id=sample_suggestion.id,
        source_video_ids=["a", "b"],
        created_at=datetime.utcnow(),
    )
    db_session.add(final)
    db_session.commit()
    db_session.refresh(final)

    resp = client.post(
        "/api/v1/performance/reports",
        json={
            "keyword": sample_suggestion.keyword,
            "actual_views": 8000,
            "actual_likes": 640,
            "actual_comments": 55,
            "actual_shares": 12,
            "followers_gained": 20,
            "outcome": "success",
            "notes": "Strong retention on hook",
            "suggestion_id": str(sample_suggestion.id),
            "final_video_id": str(final.id),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["final_video_id"] == str(final.id)
    assert data["notes"] == "Strong retention on hook"

    db_session.expire_all()
    suggestion = db_session.query(SuggestionModel).filter_by(id=sample_suggestion.id).one()
    assert suggestion.status == "reported"
    assert suggestion.actual_views == 8000

    accuracy = client.get("/api/v1/feedback/accuracy")
    assert accuracy.json()["total_reports"] == 1
    assert accuracy.json()["linked_suggestions"] == 1
    assert accuracy.json()["pending_finals"] == 0

    pending = client.get("/api/v1/feedback/pending-finals")
    assert pending.status_code == 200
    assert pending.json()["total"] == 0


def test_pending_finals_excludes_reported(client, db_session, sample_suggestion):
    final = FinalVideoModel(
        file_path="data/finals/pending.mp4",
        keyword=sample_suggestion.keyword,
        suggestion_id=sample_suggestion.id,
        source_video_ids=["x", "y"],
    )
    db_session.add(final)
    db_session.commit()
    db_session.refresh(final)

    pending_before = client.get("/api/v1/feedback/pending-finals")
    assert pending_before.json()["total"] == 1

    client.post(
        "/api/v1/performance/reports",
        json={
            "keyword": sample_suggestion.keyword,
            "actual_views": 1000,
            "outcome": "neutral",
            "final_video_id": str(final.id),
        },
    )

    pending_after = client.get("/api/v1/feedback/pending-finals")
    assert pending_after.json()["total"] == 0

    report = db_session.query(PerformanceReportModel).one()
    assert str(report.final_video_id) == str(final.id)
