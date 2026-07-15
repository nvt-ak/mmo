"""Experiments API endpoints."""
from datetime import datetime
from typing import Any, Dict, Optional
import copy
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from videoscout.db import get_db
from videoscout.db.models import KeywordExperimentModel, SuggestionModel
from videoscout.schemas import (
    ExperimentCreate,
    ExperimentReportRequest,
    Experiment,
    ExperimentListResponse,
)
from videoscout.core_engine.experiments import (
    classify_outcome,
    compute_accuracy,
    compute_actual_score,
    extract_patterns,
    suggest_weight_adjustments,
)

router = APIRouter()


def build_prediction_signals(suggestion: SuggestionModel) -> Dict[str, Any]:
    """Freeze prediction-time risk/validation from suggestion.platform_signals.agent."""
    agent = ((suggestion.platform_signals or {}).get("agent") or {})
    risk_flags = list(agent.get("risk_flags") or [])
    validation = agent.get("validation")
    return {
        "risk_flags": risk_flags,
        "validation": copy.deepcopy(validation) if validation is not None else None,
    }


def _to_experiment_schema(item: KeywordExperimentModel) -> Experiment:
    return Experiment(
        id=str(item.id),
        keyword=item.keyword,
        channel_id=item.channel_id,
        channel_subscribers=item.channel_subscribers,
        creator_avg_views=item.creator_avg_views,
        views_vs_baseline=item.views_vs_baseline,
        suggestion_source=item.suggestion_source,
        agent_suggested_score=item.agent_suggested_score,
        predicted_score=item.predicted_score,
        prediction_reasoning=item.prediction_reasoning,
        suggestion_id=str(item.suggestion_id) if item.suggestion_id else None,
        prediction_signals=item.prediction_signals,
        actual_views=item.actual_views,
        actual_engagement=item.actual_engagement,
        actual_retention=item.actual_retention,
        test_status=item.test_status,
        user_rating=item.user_rating,
        user_comments=item.user_comments,
        accuracy=item.accuracy,
        outcome_type=item.outcome_type,
        reported_at=item.reported_at,
        created_at=item.created_at,
    )


@router.post("/experiments", response_model=Experiment, status_code=201)
async def create_experiment(payload: ExperimentCreate, db: Session = Depends(get_db)):
    suggestion_uuid = None
    prediction_signals = None
    if payload.suggestion_id:
        try:
            suggestion_uuid = uuid.UUID(payload.suggestion_id)
        except ValueError as exc:
            raise HTTPException(400, "Invalid suggestion_id") from exc
        suggestion = (
            db.query(SuggestionModel)
            .filter(SuggestionModel.id == suggestion_uuid)
            .first()
        )
        if suggestion is None:
            raise HTTPException(400, "suggestion_id not found")
        prediction_signals = build_prediction_signals(suggestion)

    experiment = KeywordExperimentModel(
        keyword=payload.keyword,
        channel_id=payload.channel_id,
        channel_subscribers=payload.channel_subscribers,
        creator_avg_views=payload.creator_avg_views,
        suggestion_source=payload.suggestion_source,
        agent_suggested_score=payload.agent_suggested_score,
        predicted_score=payload.predicted_score,
        prediction_reasoning=payload.prediction_reasoning,
        suggestion_id=suggestion_uuid,
        prediction_signals=prediction_signals,
        test_status="in_progress",
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return _to_experiment_schema(experiment)


@router.get("/experiments", response_model=ExperimentListResponse)
async def list_experiments(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(KeywordExperimentModel)
    if status:
        query = query.filter(KeywordExperimentModel.test_status == status)

    items = query.order_by(KeywordExperimentModel.created_at.desc()).all()
    return ExperimentListResponse(
        items=[_to_experiment_schema(item) for item in items],
        total=len(items),
    )


@router.post("/experiments/{experiment_id}/report", response_model=Experiment)
async def report_experiment(
    experiment_id: str,
    payload: ExperimentReportRequest,
    db: Session = Depends(get_db),
):
    try:
        experiment_uuid = uuid.UUID(experiment_id)
    except ValueError as exc:
        raise HTTPException(400, "Invalid experiment id") from exc

    experiment = db.query(KeywordExperimentModel).filter(
        KeywordExperimentModel.id == experiment_uuid
    ).first()

    if not experiment:
        raise HTTPException(404, "Experiment not found")

    if payload.actual_views is not None:
        experiment.actual_views = payload.actual_views
    if payload.actual_engagement is not None:
        experiment.actual_engagement = payload.actual_engagement
    if payload.actual_retention is not None:
        experiment.actual_retention = payload.actual_retention
    if payload.user_rating is not None:
        experiment.user_rating = payload.user_rating
    if payload.user_comments is not None:
        experiment.user_comments = payload.user_comments
    if payload.outcome_type is not None:
        experiment.outcome_type = payload.outcome_type
    if payload.accuracy is not None:
        experiment.accuracy = payload.accuracy
    if payload.test_status is not None:
        experiment.test_status = payload.test_status

    if experiment.actual_views is not None and experiment.creator_avg_views:
        experiment.views_vs_baseline = experiment.actual_views / experiment.creator_avg_views

    # Task 3: compute outcome metrics at report time.
    if (
        experiment.views_vs_baseline is not None
        and experiment.actual_engagement is not None
    ):
        actual_score = compute_actual_score(
            views_vs_baseline=experiment.views_vs_baseline,
            engagement_rate=experiment.actual_engagement,
        )
        experiment.accuracy = compute_accuracy(
            predicted=float(experiment.predicted_score),
            actual=actual_score,
        )

    if experiment.test_status in {"success", "failed", "partial"}:
        experiment.outcome_type = classify_outcome(
            predicted_score=experiment.predicted_score,
            test_status=experiment.test_status,
        )

    experiment.reported_at = payload.reported_at or datetime.utcnow()

    db.commit()
    db.refresh(experiment)
    return _to_experiment_schema(experiment)


@router.post("/experiments/analyze")
async def analyze_experiments(db: Session = Depends(get_db)):
    experiments = (
        db.query(KeywordExperimentModel)
        .filter(KeywordExperimentModel.reported_at.isnot(None))
        .all()
    )
    patterns = extract_patterns(experiments)
    suggestions = suggest_weight_adjustments(patterns)
    return {
        "total_experiments": len(experiments),
        "patterns": patterns,
        "weight_suggestions": suggestions,
    }
