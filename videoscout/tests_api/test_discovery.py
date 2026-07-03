"""Tests for trend discovery API and worker (R7a)."""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from videoscout.core_engine.trend_discovery import build_scored_candidate
from videoscout.db.models import DiscoveryJobModel, SuggestionModel


@pytest.fixture
def mock_trending():
    published = datetime.utcnow().isoformat() + "Z"
    return [
        {
            "id": "v1",
            "title": "Small Business TikTok Marketing Tips 2026",
            "channel_id": "UC1",
            "published_at": published,
            "view_count": 150_000,
            "category_id": "22",
        },
        {
            "id": "v2",
            "title": "Viral Dance Trend Challenge",
            "channel_id": "UC2",
            "published_at": published,
            "view_count": 80_000,
            "category_id": "22",
        },
    ]


async def _passthrough_enrich(items, **kwargs):
    return items


def test_discovery_run_creates_job(client, db_session):
    with patch("videoscout.api.discovery.run_trend_discovery_sync"):
        resp = client.post(
            "/api/v1/discovery/run",
            json={"keyword_type_filter": "both", "region_code": "DE"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"
    assert data["job_id"]
    assert data["max_keywords"] == 10

    job = db_session.query(DiscoveryJobModel).first()
    assert job is not None
    assert job.job_type == "trend_discovery"
    assert job.keyword_type_filter == "both"


def test_discovery_run_rejects_when_job_active(client, db_session):
    active = DiscoveryJobModel(
        id=uuid.uuid4(),
        status="running",
        job_type="trend_discovery",
        keyword_type_filter="nurture",
        started_at=datetime.utcnow(),
    )
    db_session.add(active)
    db_session.commit()

    with patch("videoscout.api.discovery.run_trend_discovery_sync"):
        resp = client.post(
            "/api/v1/discovery/run",
            json={"keyword_type_filter": "both", "region_code": "DE"},
        )

    assert resp.status_code == 409
    err = resp.json()["error"]
    assert err["details"]["active_job_id"] == str(active.id)


def test_discovery_run_force_cancels_active_job(client, db_session):
    active = DiscoveryJobModel(
        id=uuid.uuid4(),
        status="running",
        job_type="trend_discovery",
        keyword_type_filter="nurture",
        started_at=datetime.utcnow(),
    )
    db_session.add(active)
    db_session.commit()

    with patch("videoscout.api.discovery.run_trend_discovery_sync"):
        resp = client.post(
            "/api/v1/discovery/run",
            json={
                "keyword_type_filter": "both",
                "region_code": "DE",
                "force": True,
            },
        )

    assert resp.status_code == 200
    db_session.refresh(active)
    assert active.status == "failed"
    assert active.error_message == "Cancelled to start a new discovery run."


def test_cancel_discovery_job_marks_active_failed(client, db_session):
    active = DiscoveryJobModel(
        id=uuid.uuid4(),
        status="running",
        job_type="trend_discovery",
        keyword_type_filter="nurture",
        started_at=datetime.utcnow(),
    )
    db_session.add(active)
    db_session.commit()

    resp = client.post(f"/api/v1/discovery/jobs/{active.id}/cancel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "Cancelled by user."

    db_session.refresh(active)
    assert active.status == "failed"


def test_cancel_discovery_job_rejects_terminal(client, db_session):
    done = DiscoveryJobModel(
        id=uuid.uuid4(),
        status="completed",
        job_type="trend_discovery",
        keyword_type_filter="nurture",
        completed_at=datetime.utcnow(),
    )
    db_session.add(done)
    db_session.commit()

    resp = client.post(f"/api/v1/discovery/jobs/{done.id}/cancel")
    assert resp.status_code == 409


def test_discovery_run_expires_stale_job(client, db_session):
    from datetime import timedelta

    stale = DiscoveryJobModel(
        status="running",
        job_type="trend_discovery",
        keyword_type_filter="nurture",
        started_at=datetime.utcnow() - timedelta(hours=2),
        created_at=datetime.utcnow() - timedelta(hours=2),
    )
    db_session.add(stale)
    db_session.commit()

    with patch("videoscout.api.discovery.run_trend_discovery_sync"):
        resp = client.post(
            "/api/v1/discovery/run",
            json={"keyword_type_filter": "both", "region_code": "DE"},
        )

    assert resp.status_code == 200
    db_session.refresh(stale)
    assert stale.status == "failed"


def test_discovery_job_stream_emits_terminal_event(client, db_session):
    job = DiscoveryJobModel(
        status="completed",
        job_type="trend_discovery",
        keyword_type_filter="both",
        keywords_generated=3,
        sources_scanned=1,
        videos_scanned=10,
        candidates_checked=12,
        progress_phase="complete",
    )
    db_session.add(job)
    db_session.commit()

    with client.stream("GET", f"/api/v1/discovery/jobs/{job.id}/stream") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        body = "".join(resp.iter_text())

    assert "data:" in body
    assert '"progress_percent":100' in body.replace(" ", "")
    assert body.count("data:") == 1


def test_compute_discovery_progress_running_phase():
    from videoscout.core_engine.discovery_progress import compute_discovery_progress

    job = DiscoveryJobModel(
        status="running",
        job_type="trend_discovery",
        keyword_type_filter="nurture",
        progress_phase="scan_videos",
        videos_scanned=5,
        candidates_checked=8,
        keywords_generated=0,
    )
    progress = compute_discovery_progress(job)
    assert progress["progress_phase"] == "scan_videos"
    assert 20 < progress["progress_percent"] < 95
    assert progress["progress_label"] == "Checking TikTok gates…"


def test_compute_discovery_progress_completed():
    from videoscout.core_engine.discovery_progress import compute_discovery_progress

    job = DiscoveryJobModel(
        status="completed",
        job_type="trend_discovery",
        keyword_type_filter="both",
        keywords_generated=4,
        progress_phase="complete",
    )
    progress = compute_discovery_progress(job)
    assert progress["progress_percent"] == 100
    assert progress["progress_phase"] == "complete"


def test_discovery_job_stream_404_for_unknown_job(client):
    resp = client.get(f"/api/v1/discovery/jobs/{uuid.uuid4()}/stream")
    assert resp.status_code == 404


def test_list_suggestions_filter_keyword_type(client, db_session):
    db_session.add_all([
        SuggestionModel(
            keyword="nurture trend clip",
            final_score=0.55,
            component_scores={"relevance": 0.5, "specificity": 0.5, "saturation": 0.5, "trend": 0.5, "video_performance": 0.5},
            suggested_by=[{"source": "trend_discovery", "score": 0.55, "timestamp": "2026-07-02"}],
            status="pending",
            keyword_type="nurture",
            gate_profile="light",
        ),
        SuggestionModel(
            keyword="beta long tail keyword phrase",
            final_score=0.72,
            component_scores={"relevance": 0.5, "specificity": 0.8, "saturation": 0.6, "trend": 0.5, "video_performance": 0.5},
            suggested_by=[{"source": "trend_discovery", "score": 0.72, "timestamp": "2026-07-02"}],
            status="pending",
            keyword_type="beta",
            gate_profile="full",
            tiktok_unverified=False,
        ),
        SuggestionModel(
            keyword="beta blocked unverified",
            final_score=0.65,
            component_scores={"relevance": 0.5, "specificity": 0.7, "saturation": 0.5, "trend": 0.5, "video_performance": 0.5},
            suggested_by=[{"source": "trend_discovery", "score": 0.65, "timestamp": "2026-07-02"}],
            status="pending",
            keyword_type="beta",
            gate_profile="full",
            tiktok_unverified=True,
        ),
    ])
    db_session.commit()

    nurture = client.get("/api/v1/suggestions?status=pending&keyword_type=nurture")
    assert nurture.status_code == 200
    assert nurture.json()["total"] == 1
    assert nurture.json()["items"][0]["keyword_type"] == "nurture"

    beta = client.get("/api/v1/suggestions?status=pending&keyword_type=beta")
    assert beta.status_code == 200
    assert beta.json()["total"] == 1
    assert beta.json()["items"][0]["keyword"] == "beta long tail keyword phrase"


@pytest.mark.asyncio
async def test_trend_discovery_worker_respects_cancelled_job(db_session, mock_trending):
    from videoscout.workers.trend_discovery import run_trend_discovery

    job = DiscoveryJobModel(
        status="started",
        job_type="trend_discovery",
        keyword_type_filter="both",
    )
    db_session.add(job)
    db_session.commit()
    job_id = job.id

    mock_yt = MagicMock()
    mock_yt.get_trending_videos.return_value = mock_trending

    async def fake_gate(keyword, gate_profile):
        row = db_session.query(DiscoveryJobModel).filter(DiscoveryJobModel.id == job_id).first()
        row.status = "failed"
        row.error_message = "Cancelled to start a new discovery run."
        row.completed_at = datetime.utcnow()
        db_session.commit()
        return {
            "surface": True,
            "tiktok_unverified": False,
            "score": 0.6,
            "tiktok_stats": {"saturation_tier": "moderate"},
            "tiktok_status": "moderate",
        }

    with patch("videoscout.workers.trend_discovery.get_youtube_service", return_value=mock_yt), \
         patch("videoscout.workers.trend_discovery.get_session", return_value=db_session), \
         patch("videoscout.workers.trend_discovery.SuggestionEngine") as mock_engine_cls, \
         patch("videoscout.workers.trend_discovery.enrich_top_scored", side_effect=_passthrough_enrich):
        instance = mock_engine_cls.return_value
        instance.check_tiktok_gate = AsyncMock(side_effect=fake_gate)
        await run_trend_discovery(str(job_id), keyword_type_filter="both")

    row = db_session.query(DiscoveryJobModel).filter(DiscoveryJobModel.id == job_id).first()
    assert row is not None
    assert row.status == "failed"
    assert row.error_message == "Cancelled to start a new discovery run."
    assert row.progress_phase != "complete"


@pytest.mark.asyncio
async def test_trend_discovery_worker_upserts(db_session, mock_trending):
    from videoscout.workers.trend_discovery import run_trend_discovery

    job = DiscoveryJobModel(status="started", job_type="trend_discovery", keyword_type_filter="both")
    db_session.add(job)
    db_session.commit()
    job_id = job.id
    engine = db_session.get_bind()

    mock_yt = MagicMock()
    mock_yt.get_trending_videos.return_value = mock_trending

    async def fake_gate(keyword, gate_profile):
        return {
            "surface": True,
            "tiktok_unverified": False,
            "score": 0.6,
            "tiktok_stats": {
                "video_count_7d": 12,
                "avg_views": 5000.0,
                "avg_likes": 200.0,
                "avg_comments": 20.0,
                "saturation_tier": "moderate",
            },
            "tiktok_status": "moderate",
        }

    async def fake_beta_batch(items, *, db, keyword_type_filter="both", **kwargs):
        scored = []
        for item in items:
            row = build_scored_candidate(
                item["candidate"],
                tiktok_gate=item["tiktok_gate"],
                keyword_type_filter=keyword_type_filter,
            )
            if row:
                scored.append(row)
        return scored

    with patch("videoscout.workers.trend_discovery.get_youtube_service", return_value=mock_yt), \
         patch("videoscout.workers.trend_discovery.get_session", return_value=db_session), \
         patch("videoscout.workers.trend_discovery.SuggestionEngine") as mock_engine_cls, \
         patch("videoscout.workers.trend_discovery.score_beta_candidates_batch", side_effect=fake_beta_batch), \
         patch("videoscout.workers.trend_discovery.enrich_top_scored", side_effect=_passthrough_enrich):
        instance = mock_engine_cls.return_value
        instance.check_tiktok_gate = AsyncMock(side_effect=fake_gate)
        await run_trend_discovery(str(job_id), keyword_type_filter="both")

    from sqlalchemy.orm import sessionmaker
    verify = sessionmaker(bind=engine)()
    try:
        job_row = verify.query(DiscoveryJobModel).filter(DiscoveryJobModel.id == job_id).first()
        assert job_row is not None
        assert job_row.status == "completed"
        assert job_row.keywords_generated >= 1
        assert job_row.videos_scanned >= 1
        assert job_row.candidates_checked >= 1
        assert job_row.progress_phase == "complete"
        rows = verify.query(SuggestionModel).all()
        assert len(rows) >= 1
        assert any(r.discovery_source == "youtube_trend" for r in rows)
        assert any(
            r.trend_evidence and r.trend_evidence.get("schema_version") == "1"
            for r in rows
        )
    finally:
        verify.close()


@pytest.mark.asyncio
async def test_trend_discovery_respects_keyword_cap(db_session, mock_trending):
    from videoscout.workers.trend_discovery import (
        MAX_KEYWORDS_PER_JOB,
        run_trend_discovery,
    )

    trending = [
        {"id": f"v{i}", "title": f"Trend Topic Number {i} Goes Viral Today", "channel_id": f"UC{i}"}
        for i in range(12)
    ]

    job = DiscoveryJobModel(status="started", job_type="trend_discovery", keyword_type_filter="nurture")
    db_session.add(job)
    db_session.commit()
    job_id = job.id
    engine = db_session.get_bind()

    mock_yt = MagicMock()
    mock_yt.get_trending_videos.return_value = trending

    async def fake_gate(keyword, gate_profile):
        return {
            "surface": True,
            "tiktok_unverified": False,
            "score": 0.6,
            "tiktok_stats": {
                "video_count_7d": 12,
                "avg_views": 5000.0,
                "avg_likes": 200.0,
                "avg_comments": 20.0,
                "saturation_tier": "moderate",
            },
            "tiktok_status": "moderate",
        }

    with patch("videoscout.workers.trend_discovery.get_youtube_service", return_value=mock_yt), \
         patch("videoscout.workers.trend_discovery.get_session", return_value=db_session), \
         patch("videoscout.workers.trend_discovery.SuggestionEngine") as mock_engine_cls, \
         patch("videoscout.workers.trend_discovery.enrich_top_scored", side_effect=_passthrough_enrich):
        instance = mock_engine_cls.return_value
        instance.check_tiktok_gate = AsyncMock(side_effect=fake_gate)
        await run_trend_discovery(str(job_id), keyword_type_filter="nurture")

    from sqlalchemy.orm import sessionmaker
    verify = sessionmaker(bind=engine)()
    try:
        job_row = verify.query(DiscoveryJobModel).filter(DiscoveryJobModel.id == job_id).first()
        assert job_row is not None
        assert job_row.status == "completed"
        assert job_row.keywords_generated <= MAX_KEYWORDS_PER_JOB
        mock_yt.get_trending_videos.assert_called_once()
        assert mock_yt.get_trending_videos.call_args.kwargs["max_results"] == 10
    finally:
        verify.close()


@pytest.mark.asyncio
async def test_tiktok_gate_blocks_beta_on_failure():
    from videoscout.core_engine.engine import SuggestionEngine

    engine = SuggestionEngine()
    engine.calculate_saturation = AsyncMock(side_effect=RuntimeError("tiktok down"))

    result = await engine.check_tiktok_gate("test keyword phrase", "full")
    assert result["surface"] is False
    assert result["tiktok_unverified"] is True

    nurture = await engine.check_tiktok_gate("test keyword", "light")
    assert nurture["surface"] is True
    assert nurture["tiktok_unverified"] is True


def test_extract_keyword_candidates_nurture_width():
    from videoscout.core_engine.trend_discovery import extract_keyword_candidates

    title = "Small Business TikTok Marketing Tips 2026"
    wide = extract_keyword_candidates(title, max_word_width=5)
    narrow = extract_keyword_candidates(title, max_word_width=3)
    assert any(len(p["keyword"].split()) >= 4 for p in wide)
    assert all(len(p["keyword"].split()) <= 3 for p in narrow)
    assert len(narrow) >= 1


def test_upsert_reactivates_rejected_suggestion(db_session):
    from videoscout.workers.trend_discovery import _upsert_scored_suggestion

    db_session.add(
        SuggestionModel(
            keyword="viral dance trend",
            final_score=0.3,
            component_scores={},
            suggested_by=[],
            status="rejected",
            reject_reason="off_topic",
            keyword_type="nurture",
            gate_profile="light",
            tiktok_unverified=False,
        )
    )
    db_session.commit()

    scored = {
        "keyword": "viral dance trend",
        "final_score": 0.55,
        "component_scores": {"relevance": 0.5},
        "tiktok_status": "moderate",
        "tiktok_count": 5,
        "tiktok_stats": {},
        "keyword_type": "nurture",
        "discovery_source": "youtube_trend",
        "trend_signals": {},
        "gate_profile": "light",
        "tiktok_unverified": False,
    }
    assert _upsert_scored_suggestion(db_session, scored) is True

    row = db_session.query(SuggestionModel).filter_by(keyword="viral dance trend").one()
    assert row.status == "pending"
    assert row.reject_reason is None
