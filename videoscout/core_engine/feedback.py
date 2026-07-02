"""Feedback loop helpers — accuracy metrics and pending finals."""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from videoscout.db.models import (
    FinalVideoModel,
    PerformanceReportModel,
    SuggestionModel,
)


def compute_accuracy_metrics(db: Session) -> dict:
    """Aggregate agent prediction quality from linked performance reports."""
    total_reports = db.query(PerformanceReportModel).count()
    if total_reports == 0:
        return {
            "total_reports": 0,
            "linked_suggestions": 0,
            "success_rate": 0.0,
            "avg_views": 0,
            "high_score_success_rate": 0.0,
            "pending_finals": 0,
        }

    success_count = (
        db.query(PerformanceReportModel)
        .filter(PerformanceReportModel.outcome == "success")
        .count()
    )
    avg_views = db.query(func.avg(PerformanceReportModel.actual_views)).scalar() or 0

    linked = (
        db.query(PerformanceReportModel, SuggestionModel)
        .join(SuggestionModel, PerformanceReportModel.suggestion_id == SuggestionModel.id)
        .all()
    )
    linked_count = len(linked)
    high_score_hits = 0
    high_score_total = 0
    for report, suggestion in linked:
        if (suggestion.final_score or 0) >= 0.7:
            high_score_total += 1
            if report.outcome == "success":
                high_score_hits += 1

    reported_final_ids = {
        row[0]
        for row in db.query(PerformanceReportModel.final_video_id)
        .filter(PerformanceReportModel.final_video_id.isnot(None))
        .all()
        if row[0]
    }
    finals_query = db.query(FinalVideoModel)
    if reported_final_ids:
        finals_query = finals_query.filter(~FinalVideoModel.id.in_(reported_final_ids))
    pending_finals = finals_query.count()

    return {
        "total_reports": total_reports,
        "linked_suggestions": linked_count,
        "success_rate": round(success_count / total_reports, 4),
        "avg_views": int(avg_views),
        "high_score_success_rate": round(
            high_score_hits / high_score_total, 4,
        ) if high_score_total else 0.0,
        "pending_finals": pending_finals,
    }


def list_pending_finals(db: Session, limit: int = 20) -> list[FinalVideoModel]:
    """Final videos not yet linked to a performance report."""
    reported_ids = {
        row[0]
        for row in db.query(PerformanceReportModel.final_video_id)
        .filter(PerformanceReportModel.final_video_id.isnot(None))
        .all()
        if row[0]
    }
    query = db.query(FinalVideoModel).order_by(FinalVideoModel.created_at.desc())
    if reported_ids:
        query = query.filter(~FinalVideoModel.id.in_(reported_ids))
    return query.limit(limit).all()
