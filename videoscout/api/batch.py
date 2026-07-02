"""Daily batch review API — Keep / Skip downloaded videos."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from videoscout.db import get_db
from videoscout.db.models import ChannelModel, SuggestionModel, VideoAssetModel
from videoscout.schemas import (
    BatchListResponse,
    BatchVideoAsset,
    BulkVideoReviewRequest,
    BulkVideoReviewResponse,
    VideoReviewAction,
    VideoReviewResponse,
)

router = APIRouter()

_REVIEW_TARGETS = {"keep": "in_pool", "skip": "skipped"}


def _thumbnail_url(row: VideoAssetModel, channel: ChannelModel | None) -> str | None:
    metadata = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    thumb = metadata.get("thumbnail_url") or metadata.get("thumbnail")
    if thumb:
        return str(thumb)
    if channel and channel.thumbnail_url:
        return channel.thumbnail_url
    return f"https://img.youtube.com/vi/{row.youtube_video_id}/mqdefault.jpg"


def _to_batch_video(
    row: VideoAssetModel,
    channel: ChannelModel | None,
    suggestion: SuggestionModel | None,
) -> BatchVideoAsset:
    return BatchVideoAsset(
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
        channel_name=channel.name if channel else None,
        keyword=suggestion.keyword if suggestion else None,
        thumbnail_url=_thumbnail_url(row, channel),
    )


def _get_video_or_404(db: Session, video_id: str) -> VideoAssetModel:
    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid video_id") from exc

    row = db.query(VideoAssetModel).filter(VideoAssetModel.id == video_uuid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Video not found")
    return row


def _apply_review(row: VideoAssetModel, action: str) -> str:
    if row.review_status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Video already reviewed ({row.review_status})",
        )
    target = _REVIEW_TARGETS[action]
    row.review_status = target
    return target


@router.get("/batch", response_model=BatchListResponse)
async def list_batch_videos(
    review_status: str | None = Query(default="pending"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(VideoAssetModel).filter(VideoAssetModel.status == "downloaded")
    if review_status:
        query = query.filter(VideoAssetModel.review_status == review_status)

    total = query.count()
    rows = query.order_by(VideoAssetModel.downloaded_at.desc()).limit(limit).all()

    channel_ids = {row.channel_id for row in rows}
    suggestion_ids = {row.suggestion_id for row in rows if row.suggestion_id}

    channels = {
        c.id: c
        for c in db.query(ChannelModel).filter(ChannelModel.id.in_(channel_ids)).all()
    } if channel_ids else {}
    suggestions = {
        s.id: s
        for s in db.query(SuggestionModel).filter(SuggestionModel.id.in_(suggestion_ids)).all()
    } if suggestion_ids else {}

    items = [
        _to_batch_video(
            row,
            channels.get(row.channel_id),
            suggestions.get(row.suggestion_id) if row.suggestion_id else None,
        )
        for row in rows
    ]

    base = db.query(VideoAssetModel).filter(VideoAssetModel.status == "downloaded")
    pending_count = base.filter(VideoAssetModel.review_status == "pending").count()
    in_pool_count = base.filter(VideoAssetModel.review_status == "in_pool").count()
    skipped_count = base.filter(VideoAssetModel.review_status == "skipped").count()

    return BatchListResponse(
        items=items,
        total=total,
        limit=limit,
        pending_count=pending_count,
        in_pool_count=in_pool_count,
        skipped_count=skipped_count,
    )


@router.post("/videos/{video_id}/review", response_model=VideoReviewResponse)
async def review_video(
    video_id: str,
    payload: VideoReviewAction,
    db: Session = Depends(get_db),
):
    row = _get_video_or_404(db, video_id)
    target = _apply_review(row, payload.action)
    db.commit()
    db.refresh(row)
    return VideoReviewResponse(id=str(row.id), review_status=target)


@router.post("/batch/review", response_model=BulkVideoReviewResponse)
async def bulk_review_videos(
    payload: BulkVideoReviewRequest,
    db: Session = Depends(get_db),
):
    target = _REVIEW_TARGETS[payload.action]
    updated = 0

    for video_id in payload.video_ids:
        row = _get_video_or_404(db, video_id)
        if row.review_status != "pending":
            continue
        row.review_status = target
        updated += 1

    db.commit()
    return BulkVideoReviewResponse(updated_count=updated, review_status=target)
