"""Feedback loop status — accuracy metrics and pending finals."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from videoscout.core_engine.feedback import compute_accuracy_metrics, list_pending_finals
from videoscout.db import get_db
from videoscout.schemas import FinalVideo

router = APIRouter()


class FeedbackAccuracyResponse(BaseModel):
    total_reports: int
    linked_suggestions: int
    success_rate: float
    avg_views: int
    high_score_success_rate: float
    pending_finals: int


class PendingFinalsResponse(BaseModel):
    items: list[FinalVideo]
    total: int


def _final_to_schema(row) -> FinalVideo:
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


@router.get("/feedback/accuracy", response_model=FeedbackAccuracyResponse)
async def get_feedback_accuracy(db: Session = Depends(get_db)):
    return FeedbackAccuracyResponse(**compute_accuracy_metrics(db))


@router.get("/feedback/pending-finals", response_model=PendingFinalsResponse)
async def get_pending_finals(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = list_pending_finals(db, limit=limit)
    return PendingFinalsResponse(
        items=[_final_to_schema(row) for row in items],
        total=len(items),
    )
