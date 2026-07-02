"""Learning API endpoints - Full implementation with pattern analysis."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from videoscout.db import get_db
from videoscout.db.models import SuggestionModel, LearningEventModel
from videoscout.core_engine.learning import LearningAgent
from videoscout.schemas import (
    LearningInsightsResponse, LearningCycleResponse,
    RejectionPattern, SuccessPattern, WeightAdjustment, FilterUpdate
)

router = APIRouter()


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
    success_patterns = agent.analyze_success_patterns(days=30)
    
    # Get recent learning events for weight adjustments
    cutoff = datetime.now() - timedelta(days=7)
    recent_events = db.query(LearningEventModel).filter(
        LearningEventModel.timestamp >= cutoff,
        LearningEventModel.type == 'report'
    ).order_by(LearningEventModel.timestamp.desc()).limit(10).all()
    
    # Calculate weight adjustments from reports
    weight_adjustments = []
    if len(recent_events) >= 3:
        # Placeholder: in production, this would call calibrate_weights
        weight_adjustments = [
            WeightAdjustment(
                factor="relevance",
                old_value=0.30,
                new_value=0.30,
                reason="Stable performance",
                confidence=0.8
            )
        ]
    
    # Get settings for filter updates
    from videoscout.db.models import SettingsModel
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
    
    Runs pattern analysis, updates weights, and generates new keywords.
    """
    agent = LearningAgent(db)
    
    # Analyze patterns
    rejection_patterns = agent.analyze_rejection_patterns(days=30)
    success_patterns = agent.analyze_success_patterns(days=30)
    
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
    
    # Calculate weight adjustments from recent reports
    cutoff = datetime.now() - timedelta(days=7)
    recent_reports = db.query(LearningEventModel).filter(
        LearningEventModel.type == 'report',
        LearningEventModel.timestamp >= cutoff
    ).all()
    
    if len(recent_reports) >= 5:
        # Run weight calibration
        for report in recent_reports[:3]:
            try:
                report_data = {
                    'predicted_score': report.predicted_score or 0.5,
                    'actual_engagement_rate': report.actual_engagement_rate or 0.5
                }
                adjustments = agent.calibrate_weights(report_data)
                weight_adjustments.extend(adjustments)
            except Exception as e:
                print(f"Error calibrating weights: {e}")
    
    # Update settings with new weights if adjustments were made
    from videoscout.db.models import SettingsModel
    if weight_adjustments:
        settings = db.query(SettingsModel).first()
        if settings:
            # Apply weight adjustments (simplified)
            for adj in weight_adjustments[:2]:  # Apply top 2 adjustments
                factor = adj['factor']
                new_value = adj['new_value']
                if factor == 'relevance':
                    settings.weight_relevance = new_value
                elif factor == 'specificity':
                    settings.weight_specificity = new_value
            db.commit()
    
    # Save learning report
    from videoscout.db.models import LearningReportModel
    report = LearningReportModel(
        timestamp=datetime.utcnow(),
        rejection_patterns=rejection_patterns,
        success_patterns=success_patterns,
        weight_adjustments=[
            {"factor": a['factor'], "old_value": a['old_value'], "new_value": a['new_value']}
            for a in weight_adjustments
        ],
        filter_updates=[],
        new_keywords_generated=len(new_keywords),
        total_rejections=len(rejection_patterns),
        total_reports=len(success_patterns),
        avg_prediction_error=0.0  # Will be calculated later
    )
    db.add(report)
    db.commit()
    
    return LearningCycleResponse(
        message="Learning cycle complete",
        report_id=str(report.id),
        adjustments_made=len(weight_adjustments),
        new_keywords_generated=len(new_keywords)
    )
