"""Integration tests: full API workflow from scan → approve → report → improve."""
import uuid
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from videoscout.db.models import (
    SuggestionModel, LearningEventModel, ChannelModel, ScanJobModel,
)


# ═══════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════

def _create_channel(db_session, channel_id="UC_test001", name="Test Channel"):
    ch = ChannelModel(
        id=uuid.uuid4(),
        channel_id=channel_id,
        name=name,
        scan_enabled=True,
        last_scan_at=datetime.utcnow() - timedelta(days=2)
    )
    db_session.add(ch)
    db_session.commit()
    return ch


def _mock_scored_keywords():
    return [{
        "keyword": "ai marketing for small business",
        "final_score": 0.85,
        "component_scores": {
            "relevance": 0.92, "specificity": 0.88,
            "saturation": 0.72, "trend": 0.50, "video_performance": 0.78
        },
        "tiktok_status": "moderate",
        "tiktok_count": 15,
        "video_id": "vid_abc",
        "channel_id": "UC_test001",
        "source": "transcript",
        "llm_confidence": 0.88,
        "rationale": "Long-tail keyword"
    }, {
        "keyword": "content strategy tips 2026",
        "final_score": 0.72,
        "component_scores": {
            "relevance": 0.78, "specificity": 0.70,
            "saturation": 0.55, "trend": 0.50, "video_performance": 0.78
        },
        "tiktok_status": "moderate",
        "tiktok_count": 22,
        "video_id": "vid_abc",
        "channel_id": "UC_test001",
        "source": "theme",
        "llm_confidence": 0.75,
        "rationale": "Trending topic"
    }]


def _setup_engine_mock(mock_engine_cls, scored=None):
    """Return async-capable mock engine (scan awaits extract/score)."""
    mock_engine = MagicMock()
    mock_engine.extract_keywords = AsyncMock(return_value=[])
    mock_engine.score_keywords = AsyncMock(return_value=scored or _mock_scored_keywords())
    mock_engine_cls.return_value = mock_engine
    return mock_engine


def _setup_youtube_mock(mock_yt_service):
    mock_yt = MagicMock()
    mock_yt.get_recent_videos.return_value = [{
        "id": "vid_abc",
        "title": "How AI is changing marketing",
        "description": "AI marketing for small business",
        "view_count": 15000,
        "like_count": 800,
        "comment_count": 45,
        "upload_date": "2026-07-01",
        "thumbnail_url": "http://img/thumb.jpg",
        "duration_sec": 480,
        "channel_id": "UC_test001",
    }]
    mock_yt_service.return_value = mock_yt
    return mock_yt


def _create_reported_suggestion(db_session, keyword="ai content tips"):
    """Create suggestion at 'reported' stage with full data."""
    s = SuggestionModel(
        keyword=keyword,
        final_score=0.82,
        component_scores={
            "relevance": 0.90, "specificity": 0.85,
            "saturation": 0.65, "trend": 0.50, "video_performance": 0.70
        },
        suggested_by=[{
            "source": "digest_scan", "video_id": "vid_001",
            "channel_id": "UC_test001", "score": 0.82,
            "timestamp": "2026-07-02T05:00:00"
        }],
        tiktok_status="moderate",
        tiktok_count_at_suggest=18,
        status="reported",
        reported_at=datetime.utcnow(),
        actual_views=8200,
        actual_likes=420,
        actual_comments=35,
        actual_shares=12,
        outcome="success"
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)

    # Also create the report learning event (normally created by /report endpoint)
    evt = LearningEventModel(
        type="report",
        keyword=s.keyword,
        outcome="success",
        predicted_score=s.final_score,
        actual_views=s.actual_views,
        actual_engagement_rate=s.actual_likes / s.actual_views if s.actual_views else 0,
        scores=s.component_scores,
        final_score=s.final_score,
        timestamp=s.reported_at or datetime.utcnow(),
        suggestion_id=s.id
    )
    db_session.add(evt)
    db_session.commit()
    return s


# ═══════════════════════════════════════════════════════
# 1. Full Workflow: Scan → Suggest → Approve → Report → Improve
# ═══════════════════════════════════════════════════════

@patch("videoscout.api.scan.get_youtube_service")
@patch("videoscout.api.scan.SuggestionEngine")
def test_full_workflow_scan_to_improve(
    mock_engine_cls, mock_yt_service, client, db_session
):
    """
    End-to-end: run scan → see pending → approve → report → improve.
    YouTube + LLM are fully mocked.
    """
    _setup_youtube_mock(mock_yt_service)
    _setup_engine_mock(mock_engine_cls)
    _create_channel(db_session)

    # Step 1: Run scan
    resp = client.post("/api/v1/scan/run", json={"channel_ids": [], "force": True})
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    assert job_id

    # Verify scan job completed
    status_resp = client.get(f"/api/v1/scan/status/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "completed"
    assert status_data["progress"]["suggestions_generated"] >= 1

    # The scan is a background task — in TestClient it runs synchronously
    # Check suggestions were created (from mock engine output)
    suggestions_resp = client.get("/api/v1/suggestions?status=pending")
    assert suggestions_resp.status_code == 200
    pending = suggestions_resp.json()["items"]
    assert len(pending) >= 1
    keywords = {p["keyword"] for p in pending}
    assert "ai marketing for small business" in keywords
    first_id = next(
        p["id"] for p in pending if p["keyword"] == "ai marketing for small business"
    )

    # Step 2: Approve
    approve_resp = client.post("/api/v1/suggestions/bulk-approve", json={
        "keyword_ids": [first_id]
    })
    assert approve_resp.status_code == 200
    assert approve_resp.json()["approved_count"] == 1

    # Step 3: Report
    report_resp = client.post(f"/api/v1/suggestions/{first_id}/report", json={
        "actual_views": 5000,
        "actual_likes": 300,
        "actual_comments": 50,
        "actual_shares": 20,
        "outcome": "success"
    })
    assert report_resp.status_code == 200
    assert report_resp.json()["reported"] is True

    # Verify learning event was created
    events = db_session.query(LearningEventModel).filter(
        LearningEventModel.type == "report"
    ).all()
    assert len(events) == 1
    assert events[0].outcome == "success"

    # Step 4: Improve
    improve_resp = client.post("/api/v1/suggestions/improve", json={
        "keyword_id": first_id
    })
    assert improve_resp.status_code == 200
    data = improve_resp.json()
    assert data["new_keywords_generated"] >= 1
    assert data["message"] == "Learning complete"

    # Verify cooldown is set
    updated = db_session.query(SuggestionModel).filter(
        SuggestionModel.id == uuid.UUID(first_id)
    ).first()
    assert updated.last_learned_at is not None


# ═══════════════════════════════════════════════════════
# 2. Rejection Workflow
# ═══════════════════════════════════════════════════════

def test_rejection_creates_learning_events(client, db_session):
    """Reject keyword → learning event created immediately."""
    s1 = SuggestionModel(
        keyword="too generic keyword",
        final_score=0.45,
        component_scores={
            "relevance": 0.40, "specificity": 0.25,
            "saturation": 0.60, "trend": 0.50, "video_performance": 0.30
        },
        suggested_by=[{"source": "digest_scan", "score": 0.45, "timestamp": "2026-07-02"}],
        status="pending"
    )
    s2 = SuggestionModel(
        keyword="off-topic keyword",
        final_score=0.50,
        component_scores={
            "relevance": 0.30, "specificity": 0.70,
            "saturation": 0.55, "trend": 0.50, "video_performance": 0.40
        },
        suggested_by=[{"source": "digest_scan", "score": 0.50, "timestamp": "2026-07-02"}],
        status="pending"
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    # Reject with per-item reasons
    resp = client.post("/api/v1/suggestions/bulk-reject", json={
        "keyword_ids": [str(s1.id), str(s2.id)],
        "reason": "too_broad",
        "per_item": {
            str(s2.id): {"reason": "off_topic", "note": "Not relevant to niche"}
        }
    })
    assert resp.status_code == 200
    assert resp.json()["rejected_count"] == 2
    assert resp.json()["learning_triggered"] is True

    # Verify learning events
    events = db_session.query(LearningEventModel).filter(
        LearningEventModel.type == "rejection"
    ).order_by(LearningEventModel.timestamp).all()
    assert len(events) == 2
    assert events[0].reason == "too_broad"
    assert events[1].reason == "off_topic"
    assert events[1].note == "Not relevant to niche"

    # Verify suggestions are rejected
    for s in [s1, s2]:
        db_session.refresh(s)
        assert s.status == "rejected"
        assert s.rejected_at is not None


# ═══════════════════════════════════════════════════════
# 3. Settings Persistence
# ═══════════════════════════════════════════════════════

def test_settings_roundtrip(client, db_session):
    """Update settings → GET returns updated values."""
    # Read defaults
    r1 = client.get("/api/v1/settings")
    assert r1.json()["weights"]["relevance"] == 0.30

    # Update weights
    client.put("/api/v1/settings", json={
        "weights": {
            "relevance": 0.40,
            "specificity": 0.20,
            "saturation": 0.20,
            "trend": 0.10,
            "video_performance": 0.10
        }
    })
    client.put("/api/v1/settings", json={
        "niche": {"topics": ["AI", "marketing"], "preferred_language": "vi"}
    })

    # Verify persistence
    r2 = client.get("/api/v1/settings")
    data = r2.json()
    assert data["weights"]["relevance"] == 0.40
    assert data["weights"]["specificity"] == 0.20
    assert "AI" in data["niche"]["topics"]
    assert data["niche"]["preferred_language"] == "vi"


# ═══════════════════════════════════════════════════════
# 4. Learning Insights With Data
# ═══════════════════════════════════════════════════════

def test_insights_reflects_rejection_and_report_data(client, db_session):
    """Learning insights endpoint aggregates rejection + report events."""
    s = _create_reported_suggestion(db_session, keyword="successful keyword")

    # Add rejection events
    for i in range(3):
        db_session.add(LearningEventModel(
            type="rejection",
            keyword=f"rejected_{i}",
            reason="too_competitive",
            scores=s.component_scores,
            final_score=0.45,
            timestamp=datetime.utcnow()
        ))
    db_session.commit()

    resp = client.get("/api/v1/learning/insights")
    assert resp.status_code == 200
    data = resp.json()

    assert data["summary_metrics"]["total_rejections"] == 3
    assert data["summary_metrics"]["total_reports"] >= 1
    assert isinstance(data["summary_metrics"]["avg_prediction_error"], float)
    assert isinstance(data["rejection_patterns"], list)
    assert isinstance(data["success_patterns"], list)


# ═══════════════════════════════════════════════════════
# 5. Learning Cycle Generates Report
# ═══════════════════════════════════════════════════════

def test_learning_cycle_with_data(client, db_session):
    """Learning cycle runs and stores a learning report."""
    # Add enough report events to trigger adjustments (>= 5)
    for i in range(5):
        s = _create_reported_suggestion(db_session, keyword=f"keyword_{i}")
        db_session.add(LearningEventModel(
            type="report",
            keyword=s.keyword,
            outcome="success",
            predicted_score=0.80,
            actual_views=5000 + i * 1000,
            actual_engagement_rate=0.06,
            scores=s.component_scores,
            final_score=0.80,
            timestamp=datetime.utcnow(),
            suggestion_id=s.id
        ))
    db_session.commit()

    resp = client.post("/api/v1/learning/cycle")
    assert resp.status_code == 200
    data = resp.json()
    assert "report_id" in data
    assert data["adjustments_made"] >= 0
    assert data["new_keywords_generated"] >= 0

    # Verify report persisted in DB
    from videoscout.db.models import LearningReportModel
    reports = db_session.query(LearningReportModel).all()
    assert len(reports) == 1
    assert reports[0].new_keywords_generated == data["new_keywords_generated"]


# ═══════════════════════════════════════════════════════
# 6. Channel Management (sources)
# ═══════════════════════════════════════════════════════

@patch("videoscout.api.sources.get_youtube_service")
def test_add_channel_persists(mock_yt, client, db_session):
    """Add channel → persisted in DB → returned in list."""
    mock_svc = MagicMock()
    mock_svc.extract_channel_id.return_value = "UC_ch001"
    mock_svc.get_channel_info.return_value = {
        "name": "AI Marketing Hub",
        "description": "AI & marketing automation",
        "thumbnail_url": "http://x.com/thumb.jpg",
        "subscribers": 50000
    }
    mock_yt.return_value = mock_svc

    # Add
    r1 = client.post("/api/v1/sources/channels", json={"channel_id": "@ai_hub"})
    assert r1.status_code == 200
    assert r1.json()["name"] == "AI Marketing Hub"
    channel_id = r1.json()["channel_id"]

    # List
    r2 = client.get("/api/v1/sources/channels")
    assert r2.status_code == 200
    assert r2.json()["total"] == 1
    assert r2.json()["items"][0]["channel_id"] == "UC_ch001"

    # Toggle scan
    r3 = client.put(f"/api/v1/sources/channels/{channel_id}?scan_enabled=false")
    assert r3.status_code == 200

    ch = db_session.query(ChannelModel).first()
    assert ch.scan_enabled is False

    # Remove
    r4 = client.delete(f"/api/v1/sources/channels/{channel_id}")
    assert r4.status_code == 200
    assert db_session.query(ChannelModel).count() == 0


# ═══════════════════════════════════════════════════════
# 7. Pagination & Filtering
# ═══════════════════════════════════════════════════════

def test_suggestions_pagination(client, db_session):
    """Create 12 pending suggestions → test offset/limit."""
    for i in range(12):
        db_session.add(SuggestionModel(
            keyword=f"keyword_{i:02d}",
            final_score=0.5,
            component_scores={
                "relevance": 0.5, "specificity": 0.5,
                "saturation": 0.5, "trend": 0.5, "video_performance": 0.5
            },
            suggested_by=[{"source": "test", "score": 0.5, "timestamp": "2026-07-02"}],
            status="pending"
        ))
    db_session.commit()

    # First page (limit=5)
    r1 = client.get("/api/v1/suggestions?limit=5&offset=0")
    assert r1.status_code == 200
    data = r1.json()
    assert data["total"] == 12
    assert len(data["items"]) == 5
    assert data["limit"] == 5
    assert data["offset"] == 0

    # Second page
    r2 = client.get("/api/v1/suggestions?limit=5&offset=5")
    assert len(r2.json()["items"]) == 5

    # Third page (remaining 2)
    r3 = client.get("/api/v1/suggestions?limit=5&offset=10")
    assert len(r3.json()["items"]) == 2


# ═══════════════════════════════════════════════════════
# 8. Search
# ═══════════════════════════════════════════════════════

def test_suggestions_search(client, db_session):
    """Search filters by keyword substring."""
    db_session.add_all([
        SuggestionModel(keyword="ai marketing guide", final_score=0.8,
                        component_scores={"relevance": 0.8, "specificity": 0.7, "saturation": 0.6, "trend": 0.5, "video_performance": 0.7},
                        suggested_by=[{"source": "test", "score": 0.8, "timestamp": "2026-07-02"}]),
        SuggestionModel(keyword="python tutorial", final_score=0.6,
                        component_scores={"relevance": 0.6, "specificity": 0.5, "saturation": 0.5, "trend": 0.5, "video_performance": 0.5},
                        suggested_by=[{"source": "test", "score": 0.6, "timestamp": "2026-07-02"}]),
    ])
    db_session.commit()

    r = client.get("/api/v1/suggestions?search=marketing")
    assert r.json()["total"] == 1
    assert "ai marketing" in r.json()["items"][0]["keyword"]

    r2 = client.get("/api/v1/suggestions?search=python")
    assert r2.json()["total"] == 1


# ═══════════════════════════════════════════════════════
# 9. Scan Status & History
# ═══════════════════════════════════════════════════════

@patch("videoscout.api.scan.get_youtube_service")
@patch("videoscout.api.scan.SuggestionEngine")
def test_scan_status_and_history(mock_engine_cls, mock_yt_service, client, db_session):
    """Scan completes → status endpoint + history list reflect job."""
    _setup_youtube_mock(mock_yt_service)
    _setup_engine_mock(mock_engine_cls)
    _create_channel(db_session)

    resp = client.post("/api/v1/scan/run", json={"channel_ids": [], "force": True})
    job_id = resp.json()["job_id"]

    status = client.get(f"/api/v1/scan/status/{job_id}").json()
    assert status["status"] == "completed"
    assert status["progress"]["channels_processed"] == 1
    assert status["progress"]["videos_processed"] == 1
    assert status["progress"]["suggestions_generated"] == 2

    history = client.get("/api/v1/scan/history?limit=5").json()
    assert len(history) == 1
    assert history[0]["status"] == "completed"
    assert history[0]["suggestions_generated"] == 2

    job = db_session.query(ScanJobModel).filter(
        ScanJobModel.id == uuid.UUID(job_id)
    ).first()
    assert job is not None
    assert job.completed_at is not None


# ═══════════════════════════════════════════════════════
# 10. Scan Deduplication
# ═══════════════════════════════════════════════════════

@patch("videoscout.api.scan.get_youtube_service")
@patch("videoscout.api.scan.SuggestionEngine")
def test_scan_deduplication_on_rerun(mock_engine_cls, mock_yt_service, client, db_session):
    """Second scan with same keywords updates existing rows, no duplicates."""
    _setup_youtube_mock(mock_yt_service)
    _setup_engine_mock(mock_engine_cls)
    _create_channel(db_session)

    client.post("/api/v1/scan/run", json={"channel_ids": [], "force": True})
    assert db_session.query(SuggestionModel).count() == 2

    # Re-run scan — same mock output
    client.post("/api/v1/scan/run", json={"channel_ids": [], "force": True})
    assert db_session.query(SuggestionModel).count() == 2

    kw = db_session.query(SuggestionModel).filter(
        SuggestionModel.keyword == "ai marketing for small business"
    ).first()
    assert len(kw.suggested_by) == 2
    assert all(entry["source"] == "digest_scan" for entry in kw.suggested_by)


# ═══════════════════════════════════════════════════════
# 11. Report Engagement Calculation
# ═══════════════════════════════════════════════════════

def test_report_engagement_rate_in_workflow(client, db_session):
    """Approve → report returns correct engagement_rate."""
    s = SuggestionModel(
        keyword="engagement test keyword",
        final_score=0.75,
        component_scores={
            "relevance": 0.8, "specificity": 0.7,
            "saturation": 0.6, "trend": 0.5, "video_performance": 0.7
        },
        suggested_by=[{"source": "test", "score": 0.75, "timestamp": "2026-07-02"}],
        status="approved",
        approved_at=datetime.utcnow(),
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)

    resp = client.post(f"/api/v1/suggestions/{s.id}/report", json={
        "actual_views": 1000,
        "actual_likes": 100,
        "actual_comments": 50,
        "actual_shares": 50,
        "outcome": "success",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["reported"] is True
    assert data["engagement_rate"] == pytest.approx(0.2)
    assert data["warning"] is None


# ═══════════════════════════════════════════════════════
# 12. Improve Cooldown in Workflow
# ═══════════════════════════════════════════════════════

def test_improve_cooldown_blocks_second_call(client, db_session):
    """After improve, second call within 24h returns 429."""
    s = SuggestionModel(
        keyword="cooldown keyword",
        final_score=0.82,
        component_scores={
            "relevance": 0.90, "specificity": 0.85,
            "saturation": 0.65, "trend": 0.50, "video_performance": 0.70
        },
        suggested_by=[{"source": "test", "score": 0.82, "timestamp": "2026-07-02"}],
        status="pending",
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)

    client.post("/api/v1/suggestions/bulk-approve", json={"keyword_ids": [str(s.id)]})
    client.post(f"/api/v1/suggestions/{s.id}/report", json={
        "actual_views": 5000,
        "actual_likes": 300,
        "actual_comments": 50,
        "actual_shares": 20,
        "outcome": "success",
    })

    r1 = client.post("/api/v1/suggestions/improve", json={"keyword_id": str(s.id)})
    assert r1.status_code == 200

    r2 = client.post("/api/v1/suggestions/improve", json={"keyword_id": str(s.id)})
    assert r2.status_code == 429
