"""Trend discovery API — primary keyword generation path (R7a)."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from videoscout.db import get_db
from videoscout.db.models import DiscoveryJobModel
from videoscout.schemas import (
    DiscoveryJobListResponse,
    DiscoveryJobResponse,
    DiscoveryRunRequest,
    DiscoveryRunResponse,
)
from videoscout.core_engine.discovery_progress import (
    MAX_KEYWORDS_PER_JOB,
    TRENDING_VIDEO_LIMIT,
    compute_discovery_progress,
)
from videoscout.workers.trend_discovery import run_trend_discovery_sync

logger = logging.getLogger(__name__)
router = APIRouter()

ACTIVE_JOB_STATUSES = ("started", "running")
TERMINAL_JOB_STATUSES = ("completed", "failed")
SSE_POLL_INTERVAL_SECONDS = 1.0


def _job_to_response(job: DiscoveryJobModel) -> DiscoveryJobResponse:
    progress = compute_discovery_progress(job)
    return DiscoveryJobResponse(
        id=str(job.id),
        status=job.status,
        job_type=job.job_type,
        keyword_type_filter=job.keyword_type_filter,
        sources_scanned=job.sources_scanned or 0,
        videos_scanned=job.videos_scanned or 0,
        candidates_checked=job.candidates_checked or 0,
        keywords_generated=job.keywords_generated or 0,
        max_keywords=MAX_KEYWORDS_PER_JOB,
        max_videos=TRENDING_VIDEO_LIMIT,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        **progress,
    )


def _get_active_discovery_job(db: Session) -> DiscoveryJobModel | None:
    return (
        db.query(DiscoveryJobModel)
        .filter(DiscoveryJobModel.status.in_(ACTIVE_JOB_STATUSES))
        .order_by(DiscoveryJobModel.created_at.desc())
        .first()
    )


@router.post("/discovery/run", response_model=DiscoveryRunResponse)
async def run_discovery(
    payload: DiscoveryRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start trend discovery job. Primary path for keyword generation."""
    keyword_type_filter = payload.keyword_type_filter or "both"
    if keyword_type_filter not in ("nurture", "beta", "both"):
        raise HTTPException(400, "keyword_type_filter must be nurture, beta, or both")

    active_job = _get_active_discovery_job(db)
    if active_job is not None:
        raise HTTPException(
            409,
            f"Discovery job {active_job.id} is already in progress",
        )

    job = DiscoveryJobModel(
        id=uuid.uuid4(),
        status="started",
        job_type="trend_discovery",
        keyword_type_filter=keyword_type_filter,
        created_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        run_trend_discovery_sync,
        str(job.id),
        keyword_type_filter=keyword_type_filter,
        region_code=payload.region_code or "DE",
    )

    return DiscoveryRunResponse(
        job_id=str(job.id),
        status="started",
        estimated_duration_seconds=60,
        max_keywords=MAX_KEYWORDS_PER_JOB,
    )


@router.get("/discovery/jobs/{job_id}", response_model=DiscoveryJobResponse)
async def get_discovery_job(job_id: str, db: Session = Depends(get_db)):
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(404, "Job not found") from exc

    job = db.query(DiscoveryJobModel).filter(DiscoveryJobModel.id == job_uuid).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return _job_to_response(job)


@router.get("/discovery/jobs/{job_id}/stream")
async def stream_discovery_job(job_id: str, db: Session = Depends(get_db)):
    """SSE stream of discovery job status until completed or failed."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(404, "Job not found") from exc

    job = db.query(DiscoveryJobModel).filter(DiscoveryJobModel.id == job_uuid).first()
    if not job:
        raise HTTPException(404, "Job not found")

    async def event_stream():
        from videoscout.db import get_session

        while True:
            stream_db = get_session()
            try:
                row = (
                    stream_db.query(DiscoveryJobModel)
                    .filter(DiscoveryJobModel.id == job_uuid)
                    .first()
                )
                if not row:
                    break

                payload = json.dumps(
                    _job_to_response(row).model_dump(mode="json"),
                )
                yield f"data: {payload}\n\n"
                if row.status in TERMINAL_JOB_STATUSES:
                    break
            finally:
                stream_db.close()

            await asyncio.sleep(SSE_POLL_INTERVAL_SECONDS)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/discovery/jobs", response_model=DiscoveryJobListResponse)
async def list_discovery_jobs(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(DiscoveryJobModel)
        .order_by(DiscoveryJobModel.created_at.desc())
        .limit(limit)
        .all()
    )
    return DiscoveryJobListResponse(
        items=[_job_to_response(row) for row in rows],
        total=len(rows),
    )
