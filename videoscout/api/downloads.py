"""Download jobs and video assets API."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import uuid

from videoscout.db import get_db
from videoscout.db.models import DownloadJobModel, VideoAssetModel
from videoscout.schemas import DownloadJobResponse, VideoAsset, VideoAssetListResponse

router = APIRouter()


@router.get("/downloads/jobs/{job_id}", response_model=DownloadJobResponse)
async def get_download_job(job_id: str, db: Session = Depends(get_db)):
    jobs = db.query(DownloadJobModel).all()
    job = next((candidate for candidate in jobs if str(candidate.id) == str(job_id)), None)
    if not job:
        raise HTTPException(status_code=404, detail="Download job not found")

    return DownloadJobResponse(
        id=str(job.id),
        job_type=job.job_type,
        suggestion_id=str(job.suggestion_id) if job.suggestion_id else None,
        cascade_job_id=str(job.cascade_job_id) if job.cascade_job_id else None,
        status=job.status,
        channels_total=job.channels_total,
        videos_found=job.videos_found,
        videos_downloaded=job.videos_downloaded,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/videos", response_model=VideoAssetListResponse)
async def list_videos(
    suggestion_id: str | None = None,
    review_status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(VideoAssetModel)
    if suggestion_id:
        try:
            suggestion_uuid = uuid.UUID(suggestion_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid suggestion_id") from exc
        query = query.filter(VideoAssetModel.suggestion_id == suggestion_uuid)
    if review_status:
        query = query.filter(VideoAssetModel.review_status == review_status)

    total = query.count()
    rows = query.order_by(VideoAssetModel.downloaded_at.desc()).limit(limit).all()
    items = [
        VideoAsset(
            id=str(row.id),
            youtube_video_id=row.youtube_video_id,
            channel_id=str(row.channel_id),
            suggestion_id=str(row.suggestion_id) if row.suggestion_id else None,
            title=row.title,
            view_count=row.view_count,
            duration_sec=row.duration_sec,
            youtube_url=row.youtube_url,
            file_path=row.file_path,
            status=row.status,
            review_status=row.review_status,
            downloaded_at=row.downloaded_at,
            metadata=row.metadata_json,
        )
        for row in rows
    ]
    return VideoAssetListResponse(items=items, total=total, limit=limit)
