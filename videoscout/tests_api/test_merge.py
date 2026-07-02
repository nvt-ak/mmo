"""Tests for R5 merge engine (manual/random merge + finals registry)."""
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from videoscout.db.models import (
    ChannelModel,
    FinalVideoModel,
    MergeJobModel,
    VideoAssetModel,
)
from videoscout.workers.merge_job import run_merge_job


class _FakeMergeService:
    def __init__(self, finals_root: Path):
        self._finals_root = finals_root

    def finals_dir(self) -> Path:
        return self._finals_root

    def merge(self, input_paths, output_path: Path) -> bool:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-final-mp4")
        return True


def _seed_pool_pair(db_session, suggestion, tmp_path: Path):
    channel = ChannelModel(
        channel_id="UC_merge_test",
        name="Merge Channel",
        scan_enabled=True,
    )
    db_session.add(channel)
    db_session.flush()

    paths = []
    assets = []
    for idx in (1, 2):
        file_path = tmp_path / f"clip_{idx}.mp4"
        file_path.write_bytes(b"source")
        asset = VideoAssetModel(
            youtube_video_id=f"yt_merge_{idx}",
            channel_id=channel.id,
            suggestion_id=suggestion.id,
            title=f"Merge Clip {idx}",
            youtube_url=f"https://www.youtube.com/watch?v=yt_merge_{idx}",
            file_path=str(file_path),
            status="downloaded",
            review_status="in_pool",
            duration_sec=60,
            downloaded_at=datetime.utcnow(),
        )
        db_session.add(asset)
        assets.append(asset)
        paths.append(file_path)

    db_session.commit()
    for asset in assets:
        db_session.refresh(asset)
    return assets


def test_list_merge_pool(client, db_session, sample_suggestion, tmp_path):
    assets = _seed_pool_pair(db_session, sample_suggestion, tmp_path)

    resp = client.get("/api/v1/merge/pool")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    ids = {item["id"] for item in body["items"]}
    assert ids == {str(assets[0].id), str(assets[1].id)}


def test_manual_merge_creates_final(client, db_session, sample_suggestion, tmp_path):
    assets = _seed_pool_pair(db_session, sample_suggestion, tmp_path)
    fake = _FakeMergeService(tmp_path / "finals")

    with patch("videoscout.workers.merge_job.MergeService", return_value=fake):
        resp = client.post(
            "/api/v1/merge/manual",
            json={"video_ids": [str(assets[0].id), str(assets[1].id)]},
        )

    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    job_resp = client.get(f"/api/v1/merge/jobs/{job_id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] == "done"
    assert job_resp.json()["final_video_id"] is not None

    finals = client.get("/api/v1/finals")
    assert finals.status_code == 200
    assert finals.json()["total"] == 1
    assert finals.json()["items"][0]["keyword"] == sample_suggestion.keyword

    pool = client.get("/api/v1/merge/pool")
    assert pool.json()["total"] == 0

    db_session.expire_all()
    merged = db_session.query(VideoAssetModel).filter(
        VideoAssetModel.id.in_([assets[0].id, assets[1].id])
    ).all()
    assert all(v.review_status == "merged" for v in merged)


def test_random_merge_same_keyword(client, db_session, sample_suggestion, tmp_path):
    _seed_pool_pair(db_session, sample_suggestion, tmp_path)
    fake = _FakeMergeService(tmp_path / "finals")

    with patch("videoscout.workers.merge_job.MergeService", return_value=fake):
        resp = client.post("/api/v1/merge/random", json={})

    assert resp.status_code == 200
    assert len(resp.json()["video_ids"]) == 2


def test_manual_merge_rejects_non_pool(client, db_session, sample_suggestion, tmp_path):
    assets = _seed_pool_pair(db_session, sample_suggestion, tmp_path)
    assets[0].review_status = "pending"
    db_session.commit()

    resp = client.post(
        "/api/v1/merge/manual",
        json={"video_ids": [str(assets[0].id), str(assets[1].id)]},
    )
    assert resp.status_code == 409


def test_merge_worker_failure_marks_job_failed(db_session, sample_suggestion, tmp_path, monkeypatch):
    import videoscout.db as db_module

    monkeypatch.setattr(db_module, "get_session", lambda: db_session)

    assets = _seed_pool_pair(db_session, sample_suggestion, tmp_path)
    job = MergeJobModel(
        job_type="manual",
        status="queued",
        video_a_id=assets[0].id,
        video_b_id=assets[1].id,
        suggestion_id=sample_suggestion.id,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    class _FailMerge:
        def finals_dir(self):
            return tmp_path / "finals"

        def merge(self, *_args, **_kwargs):
            return False

    run_merge_job(str(job.id), merge_service=_FailMerge())

    db_session.expire_all()
    refreshed = db_session.query(MergeJobModel).filter(MergeJobModel.id == job.id).one()
    assert refreshed.status == "failed"
    assert refreshed.error_message

    finals_count = db_session.query(FinalVideoModel).count()
    assert finals_count == 0
