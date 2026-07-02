"""Tests for typed media pools API (R7b)."""
from datetime import datetime

from videoscout.db.models import FinalVideoModel, VideoAssetModel


def _seed_video(db_session, sample_suggestion, channel, *, pool_type="nurture"):
    asset = VideoAssetModel(
        youtube_video_id=f"yt_pool_{pool_type}",
        channel_id=channel.id,
        suggestion_id=sample_suggestion.id,
        title="Pool clip",
        view_count=100,
        duration_sec=60,
        youtube_url="https://www.youtube.com/watch?v=yt_pool",
        file_path=f"/data/downloads/pool_{pool_type}.mp4",
        status="downloaded",
        review_status="in_pool",
        pool_type=pool_type,
        pool_status="ready",
        downloaded_at=datetime.utcnow(),
    )
    db_session.add(asset)
    db_session.commit()
    return asset


def test_list_pool_filters_by_type(client, db_session, sample_suggestion):
    from videoscout.db.models import ChannelModel

    channel = ChannelModel(
        channel_id="UC_pool_test",
        name="Pool Channel",
        scan_enabled=True,
    )
    db_session.add(channel)
    db_session.commit()

    sample_suggestion.keyword_type = "nurture"
    db_session.commit()
    _seed_video(db_session, sample_suggestion, channel, pool_type="nurture")

    beta_suggestion = sample_suggestion
    beta_asset = VideoAssetModel(
        youtube_video_id="yt_pool_beta_only",
        channel_id=channel.id,
        suggestion_id=beta_suggestion.id,
        title="Beta clip",
        view_count=50,
        duration_sec=30,
        youtube_url="https://www.youtube.com/watch?v=beta",
        file_path="/data/downloads/beta.mp4",
        status="downloaded",
        review_status="in_pool",
        pool_type="beta",
        pool_status="ready",
        downloaded_at=datetime.utcnow(),
    )
    db_session.add(beta_asset)
    db_session.commit()

    nurture = client.get("/api/v1/pools?pool_type=nurture")
    assert nurture.status_code == 200
    assert nurture.json()["total"] == 1
    assert nurture.json()["items"][0]["pool_type"] == "nurture"

    beta = client.get("/api/v1/pools?pool_type=beta")
    assert beta.json()["total"] == 1


def test_batch_keep_sets_pool_fields(client, db_session, sample_suggestion):
    from videoscout.db.models import ChannelModel

    sample_suggestion.keyword_type = "nurture"
    db_session.commit()

    channel = ChannelModel(channel_id="UC_keep_pool", name="Keep", scan_enabled=True)
    db_session.add(channel)
    db_session.commit()

    asset = VideoAssetModel(
        youtube_video_id="yt_keep_pool",
        channel_id=channel.id,
        suggestion_id=sample_suggestion.id,
        title="Pending clip",
        view_count=10,
        duration_sec=15,
        youtube_url="https://www.youtube.com/watch?v=keep",
        file_path="/data/downloads/keep.mp4",
        status="downloaded",
        review_status="pending",
        downloaded_at=datetime.utcnow(),
    )
    db_session.add(asset)
    db_session.commit()

    keep = client.post(f"/api/v1/videos/{asset.id}/review", json={"action": "keep"})
    assert keep.status_code == 200

    db_session.refresh(asset)
    assert asset.pool_type == "nurture"
    assert asset.pool_status == "ready"


def test_pool_includes_final_video(client, db_session, sample_suggestion):
    final = FinalVideoModel(
        file_path="/data/finals/merged.mp4",
        keyword="beta keyword phrase",
        suggestion_id=sample_suggestion.id,
        source_video_ids=["a", "b"],
        pool_type="beta",
        pool_status="ready",
    )
    db_session.add(final)
    db_session.commit()

    resp = client.get("/api/v1/pools?pool_type=beta")
    assert resp.status_code == 200
    kinds = {item["kind"] for item in resp.json()["items"]}
    assert "final_video" in kinds
