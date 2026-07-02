"""Learning API endpoints - Full implementation with pattern analysis."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from videoscout.db import get_db
from videoscout.db.models import SuggestionModel, LearningEventModel, LearningReportModel, SettingsModel
from videoscout.core_engine.learning import LearningAgent
from videoscout.core_engine.weight_proposals import (
    approve_weight_proposal,
    list_weight_proposals,
    propose_beta_weight_adjustments,
    reject_weight_proposal,
)
from videoscout.schemas import (
    LearningInsightsResponse, LearningCycleResponse,
    RejectionPattern, SuccessPattern, WeightAdjustment, FilterUpdate,
    WeightProposal, WeightProposalListResponse, WeightProposalActionResponse,
)

router = APIRouter()


def _serialize_proposal(row) -> WeightProposal:
    return WeightProposal(
        id=str(row.id),
        factor=row.factor,
        old_value=row.old_value,
        new_value=row.new_value,
        reason=row.reason,
        confidence=row.confidence,
        status=row.status,
        keyword_type=row.keyword_type,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
    )


@router.get("/learning/weight-proposals", response_model=WeightProposalListResponse)
async def get_weight_proposals(
    status: str = Query(default="pending"),
    db: Session = Depends(get_db),
):
    """List pending or historical beta weight proposals."""
    rows = list_weight_proposals(db, status=status)
    items = [_serialize_proposal(row) for row in rows]
    return WeightProposalListResponse(items=items, total=len(items))


@router.post("/learning/weight-proposals/{proposal_id}/approve", response_model=WeightProposalActionResponse)
async def approve_weight_proposal_endpoint(
    proposal_id: str,
    db: Session = Depends(get_db),
):
    """Apply an approved beta weight change to settings."""
    try:
        proposal_uuid = UUID(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_proposal_id") from exc

    try:
        proposal = approve_weight_proposal(db, proposal_uuid)
    except LookupError:
        raise HTTPException(status_code=404, detail="proposal_not_found")
    except ValueError:
        raise HTTPException(status_code=409, detail="proposal_not_pending")

    return WeightProposalActionResponse(
        message="Weight proposal approved",
        proposal=_serialize_proposal(proposal),
    )


@router.post("/learning/weight-proposals/{proposal_id}/reject", response_model=WeightProposalActionResponse)
async def reject_weight_proposal_endpoint(
    proposal_id: str,
    db: Session = Depends(get_db),
):
    """Reject a pending beta weight proposal."""
    try:
        proposal_uuid = UUID(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_proposal_id") from exc

    try:
        proposal = reject_weight_proposal(db, proposal_uuid)
    except LookupError:
        raise HTTPException(status_code=404, detail="proposal_not_found")
    except ValueError:
        raise HTTPException(status_code=409, detail="proposal_not_pending")

    return WeightProposalActionResponse(
        message="Weight proposal rejected",
        proposal=_serialize_proposal(proposal),
    )


@router.get("/learning/insights", response_model=LearningInsightsResponse)
async def get_learning_insights(
    db: Session = Depends(get_db)
):
    """
    Get latest learning insights and analysis.
    
    Returns:
    - Rejection patterns (what got rejected and why)
    - Success patterns (what keywords performed well)
    - Weight adjustments made recently
    - Filter updates based on learning
    """
    agent = LearningAgent(db)
    
    # Analyze rejections (last 30 days)
    rejection_patterns = agent.analyze_rejection_patterns(days=30)
    
    # Analyze successes (last 30 days)
    success_patterns = agent.analyze_success_patterns(days=30, keyword_type="beta")
    
    # Pending beta weight proposals (not yet applied)
    pending = list_weight_proposals(db, status="pending")
    weight_adjustments = [
        WeightAdjustment(
            factor=row.factor,
            old_value=row.old_value,
            new_value=row.new_value,
            reason=row.reason or "Pending operator approval",
            confidence=row.confidence,
        )
        for row in pending
    ]
    
    settings = db.query(SettingsModel).first()
    
    filter_updates = []
    if settings:
        filter_updates = [
            FilterUpdate(
                parameter="min_score_threshold",
                old_value=settings.min_score_threshold,
                new_value=settings.min_score_threshold,
                reason="No change needed"
            )
        ]
    
    # Summary metrics
    total_rejections = db.query(LearningEventModel).filter(
        LearningEventModel.type == 'rejection'
    ).count()
    
    total_reports = db.query(LearningEventModel).filter(
        LearningEventModel.type == 'report'
    ).count()
    
    # Calculate average prediction error
    avg_error = 0.0
    if total_reports > 0:
        reports = db.query(LearningEventModel).filter(
            LearningEventModel.type == 'report',
            LearningEventModel.predicted_score != None,
            LearningEventModel.actual_engagement_rate != None
        ).all()
        
        if reports:
            total_error = sum(
                abs(r.predicted_score - r.actual_engagement_rate)
                for r in reports
            )
            avg_error = total_error / len(reports)
    
    return LearningInsightsResponse(
        timestamp=datetime.utcnow(),
        rejection_patterns=rejection_patterns,
        success_patterns=success_patterns,
        weight_adjustments=weight_adjustments,
        filter_updates=filter_updates,
        new_keywords_generated=0,  # Will be populated by cycle
        summary_metrics={
            "total_rejections": total_rejections,
            "total_reports": total_reports,
            "avg_prediction_error": round(avg_error, 4)
        }
    )


@router.post("/learning/cycle", response_model=LearningCycleResponse)
async def trigger_learning_cycle(
    db: Session = Depends(get_db)
):
    """
    Manually trigger weekly learning cycle.
    
    Runs pattern analysis, creates pending weight proposals, and generates new keywords.
    """
    agent = LearningAgent(db)
    
    # Analyze patterns
    rejection_patterns = agent.analyze_rejection_patterns(days=30)
    success_patterns = agent.analyze_success_patterns(days=30, keyword_type="beta")
    
    # Generate similar keywords from success patterns
    new_keywords = []
    weight_adjustments = []
    
    for pattern in success_patterns[:3]:  # Top 3 success patterns
        try:
            scores = {
                'relevance': 0.7,
                'specificity': pattern['common_characteristics'].get('avg_specificity', 0.5),
                'saturation': pattern['common_characteristics'].get('avg_saturation', 0.5),
                'trend': 0.5,
                'video_performance': 0.7
            }
            variations = agent.generate_similar_keywords(
                pattern['keyword_example'],
                scores
            )
            new_keywords.extend(variations)
        except Exception as e:
            print(f"Error generating keywords from {pattern['keyword_example']}: {e}")
    
    # Save learning report first (proposals may link to it)
    report = LearningReportModel(
        timestamp=datetime.utcnow(),
        rejection_patterns=rejection_patterns,
        success_patterns=success_patterns,
        weight_adjustments=[],
        filter_updates=[],
        new_keywords_generated=len(new_keywords),
        total_rejections=len(rejection_patterns),
        total_reports=len(success_patterns),
        avg_prediction_error=0.0,
    )
    db.add(report)
    db.flush()

    proposals_created = propose_beta_weight_adjustments(
        db,
        agent,
        learning_report_id=report.id,
    )

    pending = list_weight_proposals(db, status="pending")
    weight_adjustments = [
        {
            "factor": row.factor,
            "old_value": row.old_value,
            "new_value": row.new_value,
            "reason": row.reason,
            "confidence": row.confidence,
        }
        for row in pending
    ]
    report.weight_adjustments = weight_adjustments
    db.commit()
    
    return LearningCycleResponse(
        message="Learning cycle complete",
        report_id=str(report.id),
        adjustments_made=proposals_created,
        new_keywords_generated=len(new_keywords),
        proposals_created=proposals_created,
    )
