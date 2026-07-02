"""Performance report API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from videoscout.db import get_db
from videoscout.db.models import (
    FinalVideoModel,
    LearningEventModel,
    PerformanceReportModel,
    SuggestionModel,
)

router = APIRouter()


class PerformanceReportCreateRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=255)
    actual_views: int = Field(..., ge=0)
    actual_likes: Optional[int] = Field(0, ge=0)
    actual_comments: Optional[int] = Field(0, ge=0)
    actual_shares: Optional[int] = Field(0, ge=0)
    followers_gained: Optional[int] = Field(0, ge=0)
    outcome: Optional[str] = None
    notes: Optional[str] = None
    suggestion_id: Optional[str] = None
    final_video_id: Optional[str] = None


class PerformanceReportResponse(BaseModel):
    id: str
    keyword: str
    suggestion_id: Optional[str]
    final_video_id: Optional[str]
    actual_views: int
    actual_likes: Optional[int]
    actual_comments: Optional[int]
    actual_shares: Optional[int]
    followers_gained: Optional[int]
    engagement_rate: Optional[float]
    outcome: Optional[str]
    notes: Optional[str]
    reported_at: datetime


def _to_schema(model: PerformanceReportModel) -> PerformanceReportResponse:
    return PerformanceReportResponse(
        id=str(model.id),
        keyword=model.keyword,
        suggestion_id=str(model.suggestion_id) if model.suggestion_id else None,
        final_video_id=str(model.final_video_id) if model.final_video_id else None,
        actual_views=model.actual_views,
        actual_likes=model.actual_likes,
        actual_comments=model.actual_comments,
        actual_shares=model.actual_shares,
        followers_gained=model.followers_gained,
        engagement_rate=model.engagement_rate,
        outcome=model.outcome,
        notes=model.notes,
        reported_at=model.reported_at,
    )


def _apply_suggestion_report(
    db: Session,
    suggestion: SuggestionModel,
    *,
    actual_views: int,
    actual_likes: int,
    actual_comments: int,
    actual_shares: int,
    outcome: str | None,
    engagement_rate: float,
    now: datetime,
) -> None:
    if suggestion.status not in {"approved", "reported"}:
        return
    suggestion.status = "reported"
    suggestion.reported_at = now
    suggestion.actual_views = actual_views
    suggestion.actual_likes = actual_likes
    suggestion.actual_comments = actual_comments
    suggestion.actual_shares = actual_shares
    suggestion.outcome = outcome


@router.post("/performance/reports", response_model=PerformanceReportResponse, status_code=201)
async def create_performance_report(
    payload: PerformanceReportCreateRequest,
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    engagement_rate = 0.0
    if payload.actual_views > 0:
        engagement_rate = (
            (payload.actual_likes or 0)
            + (payload.actual_comments or 0)
            + (payload.actual_shares or 0)
        ) / payload.actual_views

    suggestion_uuid = None
    suggested_score = None
    component_scores = None
    suggestion = None
    if payload.suggestion_id:
        try:
            suggestion_uuid = uuid.UUID(payload.suggestion_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid suggestion_id") from exc
        suggestion = db.query(SuggestionModel).filter(SuggestionModel.id == suggestion_uuid).first()
        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        suggested_score = suggestion.final_score
        component_scores = suggestion.component_scores

    final_video_uuid = None
    if payload.final_video_id:
        try:
            final_video_uuid = uuid.UUID(payload.final_video_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid final_video_id") from exc
        final_video = db.query(FinalVideoModel).filter(FinalVideoModel.id == final_video_uuid).first()
        if not final_video:
            raise HTTPException(status_code=404, detail="Final video not found")
        if not suggestion_uuid and final_video.suggestion_id:
            suggestion_uuid = final_video.suggestion_id
            suggestion = db.query(SuggestionModel).filter(SuggestionModel.id == suggestion_uuid).first()
            if suggestion:
                suggested_score = suggestion.final_score
                component_scores = suggestion.component_scores

    report = PerformanceReportModel(
        keyword=payload.keyword.strip(),
        suggestion_id=suggestion_uuid,
        final_video_id=final_video_uuid,
        actual_views=payload.actual_views,
        actual_likes=payload.actual_likes or 0,
        actual_comments=payload.actual_comments or 0,
        actual_shares=payload.actual_shares or 0,
        followers_gained=payload.followers_gained or 0,
        engagement_rate=engagement_rate,
        outcome=payload.outcome,
        notes=payload.notes,
        reported_at=now,
    )
    db.add(report)

    if suggestion:
        _apply_suggestion_report(
            db,
            suggestion,
            actual_views=payload.actual_views,
            actual_likes=payload.actual_likes or 0,
            actual_comments=payload.actual_comments or 0,
            actual_shares=payload.actual_shares or 0,
            outcome=payload.outcome,
            engagement_rate=engagement_rate,
            now=now,
        )

    event = LearningEventModel(
        type="report",
        keyword=payload.keyword.strip(),
        outcome=payload.outcome,
        predicted_score=suggested_score,
        actual_views=payload.actual_views,
        actual_engagement_rate=engagement_rate,
        scores=component_scores,
        final_score=suggested_score,
        timestamp=now,
        suggestion_id=suggestion_uuid,
    )
    db.add(event)

    db.commit()
    db.refresh(report)
    return _to_schema(report)


@router.get("/performance/reports", response_model=List[PerformanceReportResponse])
async def list_performance_reports(
    keyword: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(PerformanceReportModel)
    if keyword:
        query = query.filter(PerformanceReportModel.keyword.ilike(f"%{keyword}%"))
    reports = query.order_by(PerformanceReportModel.reported_at.desc()).limit(limit).all()
    return [_to_schema(item) for item in reports]
