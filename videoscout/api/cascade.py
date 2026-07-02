"""Cascade job API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from videoscout.db import get_db
from videoscout.db.models import KeywordCascadeJobModel
from videoscout.schemas import CascadeJobResponse

router = APIRouter()


@router.get("/cascade/jobs/{job_id}", response_model=CascadeJobResponse)
async def get_cascade_job(job_id: str, db: Session = Depends(get_db)):
    """Get status for a keyword cascade job."""
    jobs = db.query(KeywordCascadeJobModel).all()
    job = next((candidate for candidate in jobs if str(candidate.id) == str(job_id)), None)
    if not job:
        raise HTTPException(status_code=404, detail="Cascade job not found")

    return CascadeJobResponse(
        id=str(job.id),
        suggestion_id=str(job.suggestion_id),
        keyword=job.keyword,
        status=job.status,
        channels_discovered=job.channels_discovered,
        channels_subscribed=job.channels_subscribed,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )
