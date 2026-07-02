"""Tests for R4 daily batch review API."""
from datetime import datetime

from videoscout.db.models import ChannelModel, SuggestionModel, VideoAssetModel


def _seed_batch_video(db_session, suggestion, *, review_status="pending"):
    channel = ChannelModel(
        channel_id="UC_batch_test",
        name="Batch Test Channel",
        thumbnail_url="https://img/channel.jpg",
        scan_enabled=True,
    )
    db_session.add(channel)
    db_session.flush()

    asset = VideoAssetModel(
        youtube_video_id="yt_batch_001",
        channel_id=channel.id,
        suggestion_id=suggestion.id,
        title="Test Video For Batch",
        view_count=12000,
        duration_sec=95,
        youtube_url="https://www.youtube.com/watch?v=yt_batch_001",
        file_path="data/downloads/UC_batch_test/yt_batch_001.mp4",
        status="downloaded",
        review_status=review_status,
        downloaded_at=datetime.utcnow(),
        metadata_json={"thumbnail_url": "https://img/video.jpg"},
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset, channel


def test_list_batch_pending_enriched(client, db_session, sample_suggestion):
    asset, _channel = _seed_batch_video(db_session, sample_suggestion)

    resp = client.get("/api/v1/batch?review_status=pending")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pending_count"] == 1
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == str(asset.id)
    assert item["channel_name"] == "Batch Test Channel"
    assert item["keyword"] == sample_suggestion.keyword
    assert item["thumbnail_url"] == "https://img/video.jpg"


def test_review_keep_and_skip(client, db_session, sample_suggestion):
    asset, channel = _seed_batch_video(db_session, sample_suggestion)

    keep = client.post(f"/api/v1/videos/{asset.id}/review", json={"action": "keep"})
    assert keep.status_code == 200
    assert keep.json()["review_status"] == "in_pool"

    asset2 = VideoAssetModel(
        youtube_video_id="yt_batch_002",
        channel_id=channel.id,
        suggestion_id=sample_suggestion.id,
        title="Second Batch Video",
        youtube_url="https://www.youtube.com/watch?v=yt_batch_002",
        file_path="data/downloads/UC_batch_test/yt_batch_002.mp4",
        status="downloaded",
        review_status="pending",
        downloaded_at=datetime.utcnow(),
    )
    db_session.add(asset2)
    db_session.commit()
    db_session.refresh(asset2)

    skip = client.post(f"/api/v1/videos/{asset2.id}/review", json={"action": "skip"})
    assert skip.status_code == 200
    assert skip.json()["review_status"] == "skipped"


def test_review_already_reviewed_returns_409(client, db_session, sample_suggestion):
    asset, _ = _seed_batch_video(db_session, sample_suggestion, review_status="in_pool")

    resp = client.post(f"/api/v1/videos/{asset.id}/review", json={"action": "skip"})
    assert resp.status_code == 409


def test_bulk_review(client, db_session, sample_suggestion):
    a1, _ = _seed_batch_video(db_session, sample_suggestion)
    channel = db_session.query(ChannelModel).filter_by(channel_id="UC_batch_test").one()
    a2 = VideoAssetModel(
        youtube_video_id="yt_batch_bulk_002",
        channel_id=channel.id,
        suggestion_id=sample_suggestion.id,
        title="Bulk Two",
        youtube_url="https://www.youtube.com/watch?v=yt_batch_bulk_002",
        file_path="data/x2.mp4",
        status="downloaded",
        review_status="pending",
        downloaded_at=datetime.utcnow(),
    )
    db_session.add(a2)
    db_session.commit()
    db_session.refresh(a2)

    resp = client.post(
        "/api/v1/batch/review",
        json={"video_ids": [str(a1.id), str(a2.id)], "action": "keep"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated_count"] == 2
    assert resp.json()["review_status"] == "in_pool"

    pending = client.get("/api/v1/batch?review_status=pending")
    assert pending.json()["total"] == 0

    kept = client.get("/api/v1/batch?review_status=in_pool")
    assert kept.json()["total"] == 2
