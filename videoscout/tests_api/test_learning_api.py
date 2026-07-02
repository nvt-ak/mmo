"""Tests for learning API endpoints."""
from datetime import datetime, timedelta
import uuid

from videoscout.db.models import LearningEventModel, SettingsModel, SuggestionModel, WeightProposalModel


def _insert_reported_suggestion(
    db_session,
    outcome="success",
    views=5000,
    likes=300,
    *,
    keyword_type="beta",
):
    """Helper: insert a suggestion that is already approved + reported."""
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
        outcome=outcome,
        keyword_type=keyword_type,
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
    assert data["proposals_created"] == 0


def test_insights_prediction_error(client, db_session):
    _insert_reported_suggestion(db_session, outcome="success")
    resp = client.get("/api/v1/learning/insights")
    data = resp.json()
    assert data["summary_metrics"]["total_reports"] == 1
    assert data["summary_metrics"]["avg_prediction_error"] >= 0


def test_learning_cycle_creates_pending_proposals_not_auto_apply(client, db_session):
    db_session.add(SettingsModel(weight_relevance=0.30, weight_specificity=0.25, weight_saturation=0.25))
    db_session.commit()

    for _ in range(5):
        _insert_reported_suggestion(db_session, keyword_type="beta")

    resp = client.post("/api/v1/learning/cycle")
    assert resp.status_code == 200
    data = resp.json()
    assert data["proposals_created"] >= 1

    settings = db_session.query(SettingsModel).first()
    assert settings.weight_relevance == 0.30

    pending = db_session.query(WeightProposalModel).filter(WeightProposalModel.status == "pending").all()
    assert len(pending) >= 1


def test_learning_cycle_ignores_nurture_reports_for_proposals(client, db_session):
    db_session.add(SettingsModel())
    db_session.commit()

    for _ in range(5):
        _insert_reported_suggestion(db_session, keyword_type="nurture")

    resp = client.post("/api/v1/learning/cycle")
    assert resp.status_code == 200
    assert resp.json()["proposals_created"] == 0


def test_list_weight_proposals(client, db_session):
    proposal = WeightProposalModel(
        factor="specificity",
        old_value=0.25,
        new_value=0.20,
        reason="Test proposal",
        confidence=0.7,
        status="pending",
    )
    db_session.add(proposal)
    db_session.commit()

    resp = client.get("/api/v1/learning/weight-proposals?status=pending")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["factor"] == "specificity"


def test_approve_weight_proposal_updates_settings(client, db_session):
    db_session.add(SettingsModel(weight_specificity=0.25))
    proposal = WeightProposalModel(
        factor="specificity",
        old_value=0.25,
        new_value=0.20,
        reason="Approve me",
        confidence=0.8,
        status="pending",
    )
    db_session.add(proposal)
    db_session.commit()

    resp = client.post(f"/api/v1/learning/weight-proposals/{proposal.id}/approve")
    assert resp.status_code == 200
    assert resp.json()["proposal"]["status"] == "approved"

    settings = db_session.query(SettingsModel).first()
    assert settings.weight_specificity == 0.20


def test_reject_weight_proposal(client, db_session):
    proposal = WeightProposalModel(
        factor="relevance",
        old_value=0.30,
        new_value=0.25,
        reason="Reject me",
        confidence=0.6,
        status="pending",
    )
    db_session.add(proposal)
    db_session.commit()

    resp = client.post(f"/api/v1/learning/weight-proposals/{proposal.id}/reject")
    assert resp.status_code == 200
    assert resp.json()["proposal"]["status"] == "rejected"

    db_session.refresh(proposal)
    assert proposal.status == "rejected"
