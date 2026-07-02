"""Worker to execute merge jobs and register final videos."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path

from videoscout.core_engine.pools import resolve_pool_type
from videoscout import db as db_module
from videoscout.db.models import (
    FinalVideoModel,
    MergeJobModel,
    SuggestionModel,
    VideoAssetModel,
)
from videoscout.services.merge import MergeService

logger = logging.getLogger(__name__)


def _resolve_keyword(db, suggestion_id) -> str | None:
    if not suggestion_id:
        return None
    row = db.query(SuggestionModel).filter(SuggestionModel.id == suggestion_id).first()
    return row.keyword if row else None


def run_merge_job(job_id: str, merge_service: MergeService | None = None) -> None:
    """Load merge job, concat sources, write final file, mark sources merged."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        logger.error("Invalid merge job id: %s", job_id)
        return

    service = merge_service or MergeService()
    db = db_module.get_session()
    job = db.query(MergeJobModel).filter(MergeJobModel.id == job_uuid).first()
    if not job:
        logger.error("Merge job not found: %s", job_id)
        return

    job.status = "processing"
    job.started_at = datetime.utcnow()
    db.commit()

    try:
        video_a = db.query(VideoAssetModel).filter(VideoAssetModel.id == job.video_a_id).first()
        video_b = db.query(VideoAssetModel).filter(VideoAssetModel.id == job.video_b_id).first()
        if not video_a or not video_b:
            raise ValueError("Source videos not found")
        if video_a.review_status != "in_pool" or video_b.review_status != "in_pool":
            raise ValueError("Source videos must be in merge pool")

        path_a = Path(video_a.file_path)
        path_b = Path(video_b.file_path)
        output_path = service.finals_dir() / f"{job.id}.mp4"

        ok = service.merge([path_a, path_b], output_path)
        if not ok:
            raise RuntimeError("ffmpeg merge failed")

        suggestion_id = job.suggestion_id or video_a.suggestion_id or video_b.suggestion_id
        keyword = _resolve_keyword(db, suggestion_id)
        pool_type = resolve_pool_type(db, suggestion_id)
        duration = (video_a.duration_sec or 0) + (video_b.duration_sec or 0)

        final = FinalVideoModel(
            merge_job_id=job.id,
            file_path=str(output_path),
            keyword=keyword,
            suggestion_id=suggestion_id,
            source_video_ids=[str(video_a.id), str(video_b.id)],
            duration_sec=duration or None,
            pool_type=pool_type,
            pool_status="ready",
            metadata_json={
                "source_titles": [video_a.title, video_b.title],
                "job_type": job.job_type,
            },
        )
        db.add(final)

        video_a.review_status = "merged"
        video_b.review_status = "merged"
        job.status = "done"
        job.completed_at = datetime.utcnow()
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Merge job failed: %s", job_id)
        job = db.query(MergeJobModel).filter(MergeJobModel.id == job_uuid).first()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.utcnow()
            db.commit()
