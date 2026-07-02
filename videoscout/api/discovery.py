"""Trend discovery API — primary keyword generation path (R7a)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from videoscout.db import get_db
from videoscout.db.models import DiscoveryJobModel
from videoscout.schemas import (
    DiscoveryJobListResponse,
    DiscoveryJobResponse,
    DiscoveryRunRequest,
    DiscoveryRunResponse,
)
from videoscout.workers.trend_discovery import (
    MAX_KEYWORDS_PER_JOB,
    run_trend_discovery_sync,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _job_to_response(job: DiscoveryJobModel) -> DiscoveryJobResponse:
    return DiscoveryJobResponse(
        id=str(job.id),
        status=job.status,
        job_type=job.job_type,
        keyword_type_filter=job.keyword_type_filter,
        sources_scanned=job.sources_scanned or 0,
        keywords_generated=job.keywords_generated or 0,
        max_keywords=MAX_KEYWORDS_PER_JOB,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
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
