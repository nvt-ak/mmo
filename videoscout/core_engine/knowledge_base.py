"""Knowledge base utilities backed by performance reports."""
from __future__ import annotations

from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from videoscout.db.models import PerformanceReportModel


class KnowledgeBase:
    """Read-only helper that builds LLM-friendly context from report history."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_context(self, keyword: str, limit: int = 5) -> str:
        """
        Return formatted context for a keyword from recent performance reports.

        Includes recent reports plus basic aggregates so prompts can reuse
        evidence from past outcomes.
        """
        clean_keyword = (keyword or "").strip()
        if not clean_keyword:
            return ""

        reports: List[PerformanceReportModel] = (
            self.db.query(PerformanceReportModel)
            .filter(PerformanceReportModel.keyword.ilike(f"%{clean_keyword}%"))
            .order_by(PerformanceReportModel.reported_at.desc())
            .limit(limit)
            .all()
        )
        if not reports:
            return ""

        avg_views, avg_engagement = (
            self.db.query(
                func.avg(PerformanceReportModel.actual_views),
                func.avg(PerformanceReportModel.engagement_rate),
            )
            .filter(PerformanceReportModel.keyword.ilike(f"%{clean_keyword}%"))
            .one()
        )

        success_count = (
            self.db.query(PerformanceReportModel)
            .filter(PerformanceReportModel.keyword.ilike(f"%{clean_keyword}%"))
            .filter(PerformanceReportModel.outcome == "success")
            .count()
        )
        failure_count = (
            self.db.query(PerformanceReportModel)
            .filter(PerformanceReportModel.keyword.ilike(f"%{clean_keyword}%"))
            .filter(PerformanceReportModel.outcome == "failure")
            .count()
        )

        lines = [
            f"Keyword insight seed: {clean_keyword}",
            f"- Recent reports: {len(reports)}",
            f"- Avg views: {int(avg_views or 0)}",
            f"- Avg engagement_rate: {round(float(avg_engagement or 0.0), 4)}",
            f"- Outcomes: success={success_count}, failure={failure_count}",
            "Recent evidence:",
        ]

        for idx, report in enumerate(reports, start=1):
            lines.append(
                (
                    f"{idx}. {report.keyword} | views={report.actual_views} "
                    f"| likes={report.actual_likes or 0} "
                    f"| comments={report.actual_comments or 0} "
                    f"| followers={report.followers_gained or 0} "
                    f"| outcome={report.outcome or 'unknown'} "
                    f"| notes={report.notes or '-'}"
                )
            )

        return "\n".join(lines)
