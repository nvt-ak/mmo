"""
Suggestions API endpoints.
Implements Section 3 API contract.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import logging
import uuid

from videoscout.db import get_db
from videoscout.db.models import (
    SuggestionModel,
    LearningEventModel,
    ChannelModel,
    ChannelKeywordLinkModel,
    KeywordCascadeJobModel,
)
from videoscout.core_engine.learning import LearningAgent
from videoscout.workers.keyword_cascade import run_keyword_cascade
from videoscout.schemas import (
    SuggestionListResponse, Suggestion,
    BulkApproveRequest, BulkApproveResponse,
    BulkRejectRequest, BulkRejectResponse,
    ReportRequest, ReportResponse,
    ImproveRequest, ImproveResponse,
    SuggestionChannelListResponse,
    SuggestionChannelLink,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/suggestions", response_model=SuggestionListResponse)
async def list_suggestions(
    status: Optional[str] = None,
    keyword_type: Optional[str] = None,
    limit: int = Query(50, le=200, ge=1),
    offset: int = Query(0, ge=0),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    search: Optional[str] = None,
    channel_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List suggestions with filtering and pagination."""
    query = db.query(SuggestionModel)
    
    if status:
        query = query.filter(SuggestionModel.status == status)

    if keyword_type:
        if keyword_type not in ("nurture", "beta"):
            raise HTTPException(400, "keyword_type must be nurture or beta")
        query = query.filter(SuggestionModel.keyword_type == keyword_type)
        # Beta full gate: hide unverified pending from inbox
        if keyword_type == "beta" and (status is None or status == "pending"):
            query = query.filter(SuggestionModel.tiktok_unverified.is_(False))
    
    if search:
        query = query.filter(SuggestionModel.keyword.ilike(f"%{search}%"))
    
    if channel_id:
        query = query.filter(
            SuggestionModel.suggested_by.op('@>')(
                f'[{{"channel_id": "{channel_id}"}}]'
            )
        )
    
    total = query.count()
    
    sort_column = getattr(SuggestionModel, sort, SuggestionModel.created_at)
    if order == "desc":
        sort_column = sort_column.desc()
    else:
        sort_column = sort_column.asc()
    
    items = query.order_by(sort_column).limit(limit).offset(offset).all()
    
    suggestions = [
        Suggestion(
            id=str(item.id),
            keyword=item.keyword,
            status=item.status,
            final_score=item.final_score,
            component_scores=item.component_scores,
            suggested_by=item.suggested_by,
            keyword_type=item.keyword_type or "beta",
            discovery_source=item.discovery_source,
            trend_signals=item.trend_signals,
            trend_evidence=item.trend_evidence,
            platform_signals=item.platform_signals,
            gate_profile=item.gate_profile,
            tiktok_unverified=bool(item.tiktok_unverified),
            tiktok_status=item.tiktok_status,
            tiktok_count_at_suggest=item.tiktok_count_at_suggest,
            tiktok_stats=item.tiktok_stats,
            tiktok_checked_at=item.tiktok_checked_at,
            created_at=item.created_at,
            approved_at=item.approved_at,
            rejected_at=item.rejected_at,
            reject_reason=item.reject_reason,
            reject_note=item.reject_note,
            reported_at=item.reported_at,
            actual_views=item.actual_views,
            actual_likes=item.actual_likes,
            actual_comments=item.actual_comments,
            actual_shares=item.actual_shares,
            outcome=item.outcome,
            last_learned_at=item.last_learned_at
        )
        for item in items
    ]
    
    return SuggestionListResponse(
        items=suggestions, total=total, limit=limit, offset=offset
    )


@router.post("/suggestions/bulk-approve", response_model=BulkApproveResponse)
async def bulk_approve(
    payload: BulkApproveRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Bulk approve suggestions."""
    now = datetime.utcnow()
    keyword_uuids = [uuid.UUID(k) for k in payload.keyword_ids]

    newly_approved = db.query(SuggestionModel).filter(
        SuggestionModel.id.in_(keyword_uuids),
        SuggestionModel.status == "pending",
    ).all()

    cascade_job_ids: List[str] = []
    for suggestion in newly_approved:
        suggestion.status = "approved"
        suggestion.approved_at = now

        job = KeywordCascadeJobModel(
            suggestion_id=suggestion.id,
            keyword=suggestion.keyword,
            status="started",
        )
        db.add(job)
        db.flush()
        cascade_job_ids.append(str(job.id))
        background_tasks.add_task(run_keyword_cascade, str(job.id))

    db.commit()
    keywords = [s.keyword for s in newly_approved]
    return BulkApproveResponse(
        approved_count=len(newly_approved),
        approved_keywords=keywords,
        cascade_job_ids=cascade_job_ids,
    )


@router.get(
    "/suggestions/{id}/channels",
    response_model=SuggestionChannelListResponse,
)
async def list_suggestion_channels(id: str, db: Session = Depends(get_db)):
    """List channels linked to a suggestion via keyword cascade."""
    try:
        suggestion_id = uuid.UUID(id)
    except ValueError as exc:
        raise HTTPException(404, "Suggestion not found") from exc

    suggestion = db.query(SuggestionModel).filter(
        SuggestionModel.id == suggestion_id
    ).first()
    if not suggestion:
        raise HTTPException(404, "Suggestion not found")

    rows = (
        db.query(ChannelKeywordLinkModel, ChannelModel)
        .join(ChannelModel, ChannelKeywordLinkModel.channel_id == ChannelModel.id)
        .filter(ChannelKeywordLinkModel.suggestion_id == suggestion_id)
        .order_by(ChannelKeywordLinkModel.discovery_score.desc())
        .all()
    )

    items = [
        SuggestionChannelLink(
            channel_id=str(channel.id),
            youtube_channel_id=link.youtube_channel_id,
            name=channel.name,
            description=channel.description,
            thumbnail_url=channel.thumbnail_url,
            subscriber_count=channel.subscriber_count,
            discovery_score=link.discovery_score,
            linked_at=link.created_at,
        )
        for link, channel in rows
    ]
    return SuggestionChannelListResponse(items=items, total=len(items))


@router.post("/suggestions/bulk-reject", response_model=BulkRejectResponse)
async def bulk_reject(payload: BulkRejectRequest, db: Session = Depends(get_db)):
    """Bulk reject with immediate learning feedback."""
    now = datetime.utcnow()
    rejected_count = 0
    
    for kid in payload.keyword_ids:
        specific = payload.per_item.get(kid) if payload.per_item else None
        reason = specific.get('reason') if specific else payload.reason
        note = specific.get('note') if specific else payload.note
        
        suggestion = db.query(SuggestionModel).filter(
            SuggestionModel.id == uuid.UUID(kid)
        ).first()
        
        if not suggestion:
            continue
        
        suggestion.status = 'rejected'
        suggestion.reject_reason = reason
        suggestion.reject_note = note
        suggestion.rejected_at = now
        
        # G3: Create learning event for rejection
        event = LearningEventModel(
            type='rejection',
            keyword=suggestion.keyword,
            reason=reason,
            note=note,
            scores=suggestion.component_scores,
            final_score=suggestion.final_score,
            timestamp=now,
            suggestion_id=suggestion.id
        )
        db.add(event)
        rejected_count += 1
    
    db.commit()
    
    return BulkRejectResponse(
        rejected_count=rejected_count,
        learning_triggered=True
    )


@router.post("/suggestions/{id}/report", response_model=ReportResponse)
async def report_keyword(id: str, payload: ReportRequest, db: Session = Depends(get_db)):
    """Report results after upload."""
    suggestion = db.query(SuggestionModel).filter(
        SuggestionModel.id == uuid.UUID(id)
    ).first()
    
    if not suggestion:
        raise HTTPException(404, "Suggestion not found")
    
    if suggestion.status != 'approved':
        raise HTTPException(400, "Only approved keywords can be reported")
    
    # Calculate engagement rate
    engagement_rate = 0.0
    if payload.actual_views > 0:
        engagement_rate = (
            payload.actual_likes +
            payload.actual_comments +
            payload.actual_shares
        ) / payload.actual_views
    
    warning = None
    if engagement_rate > 0.5:
        warning = "Unusually high engagement rate - double check numbers"
    
    # Update suggestion
    now = datetime.utcnow()
    suggestion.status = 'reported'
    suggestion.reported_at = now
    suggestion.actual_views = payload.actual_views
    suggestion.actual_likes = payload.actual_likes
    suggestion.actual_comments = payload.actual_comments
    suggestion.actual_shares = payload.actual_shares
    suggestion.outcome = payload.outcome
    
    # G3: Create learning event for report
    event = LearningEventModel(
        type='report',
        keyword=suggestion.keyword,
        outcome=payload.outcome,
        predicted_score=suggestion.final_score,
        actual_views=payload.actual_views,
        actual_engagement_rate=engagement_rate,
        scores=suggestion.component_scores,
        final_score=suggestion.final_score,
        timestamp=now,
        suggestion_id=suggestion.id
    )
    db.add(event)
    db.commit()
    
    return ReportResponse(reported=True, engagement_rate=engagement_rate, warning=warning)


@router.post("/suggestions/improve", response_model=ImproveResponse)
async def trigger_improve(payload: ImproveRequest, db: Session = Depends(get_db)):
    """Trigger learning from reported keyword (24h cooldown)."""
    suggestion = db.query(SuggestionModel).filter(
        SuggestionModel.id == uuid.UUID(payload.keyword_id)
    ).first()
    
    if not suggestion:
        raise HTTPException(404, "Keyword not found")
    
    if suggestion.status != 'reported':
        raise HTTPException(400, "Only reported keywords can trigger learning")
    
    # Cooldown check
    if not payload.force and suggestion.last_learned_at:
        hours_since = (
            datetime.utcnow() - suggestion.last_learned_at
        ).total_seconds() / 3600
        
        if hours_since < 24:
            raise HTTPException(
                429,
                f"Can improve again in {int(24 - hours_since)} hours"
            )
    
    # G2: Wire LearningAgent
    agent = LearningAgent(db)
    
    # Calculate weight adjustments
    weight_adjustments = []
    if suggestion.component_scores and suggestion.outcome:
        actual_engagement = 0.5
        if suggestion.actual_views and suggestion.actual_views > 0 and suggestion.actual_likes:
            actual_engagement = suggestion.actual_likes / suggestion.actual_views
        
        report_data = {
            'predicted_score': suggestion.final_score,
            'actual_engagement_rate': actual_engagement
        }
        raw_adjustments = agent.calibrate_weights(report_data)
        weight_adjustments = [
            {
                'factor': a['factor'],
                'old_value': a['old_value'],
                'new_value': a['new_value'],
                'reason': a['reason'],
                'confidence': a['confidence']
            }
            for a in raw_adjustments
        ]
    
    # Generate similar keywords if success
    new_keywords = []
    if suggestion.outcome == 'success':
        cs = suggestion.component_scores or {}
        if not isinstance(cs, dict):
            cs = cs.model_dump() if hasattr(cs, 'model_dump') else cs.dict() if hasattr(cs, 'dict') else {}
        scores = {
            'relevance': cs.get('relevance', 0.5),
            'specificity': cs.get('specificity', 0.5),
            'saturation': cs.get('saturation', 0.5),
            'trend': cs.get('trend', 0.5),
            'video_performance': cs.get('video_performance', 0.5)
        }
        new_keywords = agent.generate_similar_keywords(suggestion.keyword, scores)
    
    # Update cooldown
    suggestion.last_learned_at = datetime.utcnow()
    db.commit()
    
    # Format weight adjustments for response schema
    from videoscout.schemas import WeightAdjustment
    adjustments_schema = [
        WeightAdjustment(
            factor=a['factor'],
            old_value=a['old_value'],
            new_value=a['new_value'],
            reason=a['reason'],
            confidence=a['confidence']
        )
        for a in weight_adjustments
    ] if weight_adjustments else None
    
    return ImproveResponse(
        message="Learning complete",
        new_keywords_generated=len(new_keywords),
        new_keywords=new_keywords,
        weight_adjustments=adjustments_schema
    )
