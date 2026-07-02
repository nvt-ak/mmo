"""Tests for suggestions API endpoints."""
import math


def test_list_suggestions_empty(client):
    resp = client.get("/api/v1/suggestions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_suggestions_with_filter(client, sample_suggestion):
    resp = client.get("/api/v1/suggestions?status=pending")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["keyword"] == "ai marketing for small business"


def test_list_suggestions_wrong_status(client, sample_suggestion):
    resp = client.get("/api/v1/suggestions?status=approved")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_bulk_approve(client, sample_suggestion):
    resp = client.post("/api/v1/suggestions/bulk-approve", json={
        "keyword_ids": [str(sample_suggestion.id)]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["approved_count"] == 1
    assert "ai marketing" in data["approved_keywords"][0]


def test_bulk_reject_creates_learning_event(client, sample_suggestion, db_session):
    resp = client.post("/api/v1/suggestions/bulk-reject", json={
        "keyword_ids": [str(sample_suggestion.id)],
        "reason": "too_broad"
    })
    assert resp.status_code == 200
    assert resp.json()["rejected_count"] == 1

    from videoscout.db.models import LearningEventModel
    events = db_session.query(LearningEventModel).all()
    assert len(events) == 1
    assert events[0].type == "rejection"
    assert events[0].reason == "too_broad"


def test_report_only_approved(client, sample_suggestion):
    # pending → not allowed
    resp = client.post(f"/api/v1/suggestions/{sample_suggestion.id}/report", json={
        "actual_views": 5000,
        "actual_likes": 300,
        "outcome": "success"
    })
    assert resp.status_code == 400


def test_report_success_creates_event(client, sample_suggestion, db_session):
    # approve first
    client.post("/api/v1/suggestions/bulk-approve", json={
        "keyword_ids": [str(sample_suggestion.id)]
    })

    resp = client.post(f"/api/v1/suggestions/{sample_suggestion.id}/report", json={
        "actual_views": 5000,
        "actual_likes": 300,
        "actual_comments": 50,
        "actual_shares": 20,
        "outcome": "success"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["reported"] is True
    assert math.isclose(data["engagement_rate"], (300 + 50 + 20) / 5000, rel_tol=0.01)

    from videoscout.db.models import LearningEventModel, SuggestionModel
    events = db_session.query(LearningEventModel).filter(LearningEventModel.type == "report").all()
    assert len(events) == 1
    assert events[0].outcome == "success"

    s = db_session.query(SuggestionModel).first()
    assert s.status == "reported"
    assert s.actual_views == 5000


def test_report_high_engagement_warning(client, sample_suggestion, db_session):
    client.post("/api/v1/suggestions/bulk-approve", json={
        "keyword_ids": [str(sample_suggestion.id)]
    })
    resp = client.post(f"/api/v1/suggestions/{sample_suggestion.id}/report", json={
        "actual_views": 100,
        "actual_likes": 80,
        "outcome": "success"
    })
    assert resp.status_code == 200
    assert resp.json()["warning"] is not None
    assert "high" in resp.json()["warning"].lower()


def test_improve_cooldown(client, sample_suggestion, db_session):
    # approve + report
    client.post("/api/v1/suggestions/bulk-approve", json={
        "keyword_ids": [str(sample_suggestion.id)]
    })
    client.post(f"/api/v1/suggestions/{sample_suggestion.id}/report", json={
        "actual_views": 5000,
        "actual_likes": 300,
        "outcome": "success"
    })

    # First improve — OK
    resp = client.post("/api/v1/suggestions/improve", json={
        "keyword_id": str(sample_suggestion.id)
    })
    assert resp.status_code == 200
    assert resp.json()["new_keywords_generated"] >= 1

    # Second improve — cooldown blocked
    resp = client.post("/api/v1/suggestions/improve", json={
        "keyword_id": str(sample_suggestion.id)
    })
    assert resp.status_code == 429


def test_improve_force_bypass_cooldown(client, sample_suggestion):
    client.post("/api/v1/suggestions/bulk-approve", json={
        "keyword_ids": [str(sample_suggestion.id)]
    })
    client.post(f"/api/v1/suggestions/{sample_suggestion.id}/report", json={
        "actual_views": 5000,
        "actual_likes": 300,
        "outcome": "success"
    })
    client.post("/api/v1/suggestions/improve", json={
        "keyword_id": str(sample_suggestion.id)
    })
    # Force bypass
    resp = client.post("/api/v1/suggestions/improve", json={
        "keyword_id": str(sample_suggestion.id),
        "force": True
    })
    assert resp.status_code == 200
