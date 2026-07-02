"""Merge pool, job enqueue, and finals registry API."""
from __future__ import annotations

import random
import uuid
from collections import defaultdict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from videoscout.api.batch import _to_batch_video
from videoscout.db import get_db
from videoscout.db.models import (
    ChannelModel,
    FinalVideoModel,
    MergeJobModel,
    SuggestionModel,
    VideoAssetModel,
)
from videoscout.schemas import (
    FinalVideo,
    FinalVideoListResponse,
    ManualMergeRequest,
    MergeEnqueueResponse,
    MergeJobResponse,
    MergePoolResponse,
    MergePoolVideo,
    RandomMergeRequest,
)
from videoscout.workers.merge_job import run_merge_job

router = APIRouter()


def _final_for_row(row: FinalVideoModel) -> FinalVideo:
    return FinalVideo(
        id=str(row.id),
        merge_job_id=str(row.merge_job_id) if row.merge_job_id else None,
        file_path=row.file_path,
        keyword=row.keyword,
        suggestion_id=str(row.suggestion_id) if row.suggestion_id else None,
        source_video_ids=list(row.source_video_ids or []),
        duration_sec=row.duration_sec,
        created_at=row.created_at,
        metadata=row.metadata_json,
    )


def _job_response(db: Session, job: MergeJobModel) -> MergeJobResponse:
    final = (
        db.query(FinalVideoModel)
        .filter(FinalVideoModel.merge_job_id == job.id)
        .order_by(FinalVideoModel.created_at.desc())
        .first()
    )
    return MergeJobResponse(
        id=str(job.id),
        job_type=job.job_type,
        status=job.status,
        video_a_id=str(job.video_a_id) if job.video_a_id else None,
        video_b_id=str(job.video_b_id) if job.video_b_id else None,
        suggestion_id=str(job.suggestion_id) if job.suggestion_id else None,
        error_message=job.error_message,
        final_video_id=str(final.id) if final else None,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def _load_pool_videos(db: Session, suggestion_id: str | None, limit: int):
    query = db.query(VideoAssetModel).filter(
        VideoAssetModel.status == "downloaded",
        VideoAssetModel.review_status == "in_pool",
    )
    if suggestion_id:
        try:
            suggestion_uuid = uuid.UUID(suggestion_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid suggestion_id") from exc
        query = query.filter(VideoAssetModel.suggestion_id == suggestion_uuid)

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
        MergePoolVideo(
            **_to_batch_video(
                row,
                channels.get(row.channel_id),
                suggestions.get(row.suggestion_id) if row.suggestion_id else None,
            ).model_dump()
        )
        for row in rows
    ]
    return items, total


def _pick_random_pair(db: Session, suggestion_id: str | None) -> tuple[VideoAssetModel, VideoAssetModel]:
    query = db.query(VideoAssetModel).filter(
        VideoAssetModel.review_status == "in_pool",
        VideoAssetModel.status == "downloaded",
    )
    if suggestion_id:
        try:
            suggestion_uuid = uuid.UUID(suggestion_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid suggestion_id") from exc
        query = query.filter(VideoAssetModel.suggestion_id == suggestion_uuid)

    rows = query.all()
    grouped: dict[uuid.UUID | None, list[VideoAssetModel]] = defaultdict(list)
    for row in rows:
        grouped[row.suggestion_id].append(row)

    eligible = [videos for videos in grouped.values() if len(videos) >= 2]
    if not eligible:
        raise HTTPException(status_code=409, detail="Need at least two pool videos with same keyword")

    pair = random.choice(eligible)
    return tuple(random.sample(pair, 2))


def _validate_manual_pair(db: Session, video_ids: list[str]) -> tuple[VideoAssetModel, VideoAssetModel]:
    if len(video_ids) != 2:
        raise HTTPException(status_code=400, detail="Manual merge requires exactly two videos")
    if video_ids[0] == video_ids[1]:
        raise HTTPException(status_code=400, detail="Select two distinct videos")

    videos: list[VideoAssetModel] = []
    for video_id in video_ids:
        try:
            video_uuid = uuid.UUID(video_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid video_id") from exc
        row = db.query(VideoAssetModel).filter(VideoAssetModel.id == video_uuid).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")
        if row.review_status != "in_pool":
            raise HTTPException(status_code=409, detail=f"Video not in merge pool: {video_id}")
        videos.append(row)
    return videos[0], videos[1]


def _enqueue_merge(
    db: Session,
    background_tasks: BackgroundTasks,
    *,
    job_type: str,
    video_a: VideoAssetModel,
    video_b: VideoAssetModel,
    suggestion_id=None,
) -> MergeJobModel:
    job = MergeJobModel(
        job_type=job_type,
        status="queued",
        video_a_id=video_a.id,
        video_b_id=video_b.id,
        suggestion_id=suggestion_id or video_a.suggestion_id or video_b.suggestion_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(run_merge_job, str(job.id))
    return job


@router.get("/merge/pool", response_model=MergePoolResponse)
async def list_merge_pool(
    suggestion_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = _load_pool_videos(db, suggestion_id, limit)
    return MergePoolResponse(items=items, total=total, limit=limit)


@router.post("/merge/manual", response_model=MergeEnqueueResponse)
async def enqueue_manual_merge(
    payload: ManualMergeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    video_a, video_b = _validate_manual_pair(db, payload.video_ids)
    job = _enqueue_merge(
        db,
        background_tasks,
        job_type="manual",
        video_a=video_a,
        video_b=video_b,
    )
    return MergeEnqueueResponse(
        job_id=str(job.id),
        video_ids=[str(video_a.id), str(video_b.id)],
        status=job.status,
    )


@router.post("/merge/random", response_model=MergeEnqueueResponse)
async def enqueue_random_merge(
    payload: RandomMergeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    video_a, video_b = _pick_random_pair(db, payload.suggestion_id)
    job = _enqueue_merge(
        db,
        background_tasks,
        job_type="random",
        video_a=video_a,
        video_b=video_b,
        suggestion_id=video_a.suggestion_id,
    )
    return MergeEnqueueResponse(
        job_id=str(job.id),
        video_ids=[str(video_a.id), str(video_b.id)],
        status=job.status,
    )


@router.get("/merge/jobs/{job_id}", response_model=MergeJobResponse)
async def get_merge_job(job_id: str, db: Session = Depends(get_db)):
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid job_id") from exc

    job = db.query(MergeJobModel).filter(MergeJobModel.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Merge job not found")
    return _job_response(db, job)


@router.get("/finals", response_model=FinalVideoListResponse)
async def list_finals(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(FinalVideoModel)
    total = query.count()
    rows = query.order_by(FinalVideoModel.created_at.desc()).limit(limit).all()
    return FinalVideoListResponse(
        items=[_final_for_row(row) for row in rows],
        total=total,
        limit=limit,
    )
