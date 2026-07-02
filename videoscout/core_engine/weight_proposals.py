"""Beta weight proposal helpers (US-056)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from videoscout.core_engine.learning import LearningAgent
from videoscout.db.models import (
    LearningEventModel,
    SettingsModel,
    SuggestionModel,
    WeightProposalModel,
)

ALLOWED_FACTORS = frozenset({"relevance", "specificity", "saturation"})
MIN_BETA_REPORTS = 5


def _weight_column(factor: str) -> str:
    return f"weight_{factor}"


def get_beta_report_events(db: Session, *, days: int = 7) -> List[LearningEventModel]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(LearningEventModel)
        .join(SuggestionModel, LearningEventModel.suggestion_id == SuggestionModel.id)
        .filter(
            LearningEventModel.type == "report",
            LearningEventModel.timestamp >= cutoff,
            SuggestionModel.keyword_type == "beta",
        )
        .all()
    )


def _current_weight(settings: Optional[SettingsModel], factor: str) -> float:
    defaults = {"relevance": 0.30, "specificity": 0.25, "saturation": 0.25}
    if not settings:
        return defaults[factor]
    return float(getattr(settings, _weight_column(factor)))


def propose_beta_weight_adjustments(
    db: Session,
    agent: LearningAgent,
    *,
    learning_report_id: Optional[UUID] = None,
) -> int:
    """Create pending weight proposals from beta report events. Returns count created."""
    events = get_beta_report_events(db)
    if len(events) < MIN_BETA_REPORTS:
        return 0

    predicted_scores = [float(e.predicted_score or 0.0) for e in events]
    actual_rates = [float(e.actual_engagement_rate or 0.0) for e in events]
    avg_predicted = sum(predicted_scores) / len(predicted_scores)
    avg_actual = sum(actual_rates) / len(actual_rates)

    adjustments = agent.calibrate_weights(
        {
            "predicted_score": avg_predicted,
            "actual_engagement_rate": avg_actual,
        }
    )

    settings = db.query(SettingsModel).first()
    created = 0

    for adjustment in adjustments:
        factor = adjustment.get("factor")
        if factor not in ALLOWED_FACTORS:
            continue

        existing = (
            db.query(WeightProposalModel)
            .filter(
                WeightProposalModel.factor == factor,
                WeightProposalModel.status == "pending",
            )
            .first()
        )
        if existing:
            continue

        old_value = _current_weight(settings, factor)
        new_value = round(float(adjustment["new_value"]), 4)
        if abs(new_value - old_value) < 0.001:
            continue

        db.add(
            WeightProposalModel(
                factor=factor,
                old_value=old_value,
                new_value=new_value,
                reason=str(adjustment.get("reason") or "Beta learning cycle proposal"),
                confidence=float(adjustment.get("confidence") or 0.7),
                status="pending",
                keyword_type="beta",
                learning_report_id=learning_report_id,
            )
        )
        created += 1

    if created:
        db.commit()
    return created


def list_weight_proposals(
    db: Session,
    *,
    status: str = "pending",
) -> List[WeightProposalModel]:
    query = db.query(WeightProposalModel).order_by(WeightProposalModel.created_at.desc())
    if status:
        query = query.filter(WeightProposalModel.status == status)
    return query.all()


def approve_weight_proposal(db: Session, proposal_id: UUID) -> WeightProposalModel:
    proposal = db.query(WeightProposalModel).filter(WeightProposalModel.id == proposal_id).first()
    if not proposal:
        raise LookupError("proposal_not_found")
    if proposal.status != "pending":
        raise ValueError("proposal_not_pending")

    settings = db.query(SettingsModel).first()
    if not settings:
        settings = SettingsModel()
        db.add(settings)
        db.flush()

    setattr(settings, _weight_column(proposal.factor), proposal.new_value)
    proposal.status = "approved"
    proposal.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(proposal)
    return proposal


def reject_weight_proposal(db: Session, proposal_id: UUID) -> WeightProposalModel:
    proposal = db.query(WeightProposalModel).filter(WeightProposalModel.id == proposal_id).first()
    if not proposal:
        raise LookupError("proposal_not_found")
    if proposal.status != "pending":
        raise ValueError("proposal_not_pending")

    proposal.status = "rejected"
    proposal.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(proposal)
    return proposal
