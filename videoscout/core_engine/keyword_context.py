"""Assemble keyword evidence context for beta LLM scoring (ADR 0012)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from videoscout.db.models import (
    KeywordPatternModel,
    PerformanceReportModel,
    SettingsModel,
    SuggestionModel,
)

MAX_CONTEXT_CHARS = 2000


def _trait_matches_keyword(trait: str, keyword: str) -> bool:
    trait_l = (trait or "").lower().strip()
    kw_l = (keyword or "").lower().strip()
    if not trait_l or not kw_l:
        return False
    if trait_l in kw_l or kw_l in trait_l:
        return True
    return bool(set(trait_l.split()) & set(kw_l.split()))


def _report_row(report: PerformanceReportModel) -> Dict[str, Any]:
    return {
        "keyword": report.keyword,
        "actual_views": report.actual_views,
        "actual_likes": report.actual_likes,
        "actual_comments": report.actual_comments,
        "followers_gained": report.followers_gained,
        "engagement_rate": report.engagement_rate,
        "outcome": report.outcome,
        "notes": report.notes,
        "reported_at": report.reported_at.isoformat() if report.reported_at else None,
    }


def _pattern_row(pattern: KeywordPatternModel) -> Dict[str, Any]:
    return {
        "pattern_type": pattern.pattern_type,
        "keyword_trait": pattern.keyword_trait,
        "outcome_type": pattern.outcome_type,
        "insight": pattern.insight,
        "confidence": pattern.confidence,
        "occurrence_count": pattern.occurrence_count,
        "suggested_adjustment": pattern.suggested_adjustment,
    }


class KeywordContextBuilder:
    """Build structured knowledge context for a keyword candidate."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def build(
        self,
        keyword: str,
        *,
        keyword_type: str = "beta",
        limit: int = 5,
        tiktok_hint: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clean_keyword = (keyword or "").strip()
        if not clean_keyword:
            return {}

        reports = self._fetch_reports(clean_keyword, keyword_type=keyword_type, limit=limit)
        aggregates = self._aggregate_reports(clean_keyword, keyword_type=keyword_type)
        patterns = self._fetch_patterns(clean_keyword, limit=limit)
        niche = self._fetch_niche()

        context: Dict[str, Any] = {
            "keyword": clean_keyword,
            "keyword_type": keyword_type,
            "similar_reports": [_report_row(r) for r in reports],
            "aggregates": aggregates,
            "patterns": patterns,
            "niche": niche,
        }
        if tiktok_hint:
            context["tiktok_hint"] = tiktok_hint

        return self._apply_char_budget(context)

    def serialize(self, context: Dict[str, Any]) -> str:
        """JSON serialization respecting char budget."""
        if not context:
            return ""
        return json.dumps(context, separators=(",", ":"), ensure_ascii=False)

    def to_text(self, context: Dict[str, Any]) -> str:
        """Human-readable context for legacy prompts."""
        if not context:
            return ""

        keyword = context.get("keyword", "")
        aggregates = context.get("aggregates") or {}
        reports = context.get("similar_reports") or []
        patterns = context.get("patterns") or []
        niche = context.get("niche") or {}

        lines = [
            f"Keyword insight seed: {keyword}",
            (
                f"- Recent reports: {aggregates.get('report_count', len(reports))}"
                f" | Avg views: {aggregates.get('avg_views', 0)}"
                f" | Avg engagement_rate: {aggregates.get('avg_engagement_rate', 0.0)}"
                f" | Outcomes: success={aggregates.get('success_count', 0)},"
                f" failure={aggregates.get('failure_count', 0)}"
            ),
        ]

        if niche.get("topics"):
            lines.append(f"- Niche topics: {', '.join(niche['topics'][:8])}")

        if patterns:
            lines.append("Learned patterns:")
            for idx, pattern in enumerate(patterns[:3], start=1):
                lines.append(
                    f"{idx}. [{pattern.get('outcome_type')}] "
                    f"{pattern.get('keyword_trait')} — {pattern.get('insight')}"
                )

        if reports:
            lines.append("Recent evidence:")
            for idx, report in enumerate(reports, start=1):
                lines.append(
                    (
                        f"{idx}. {report.get('keyword')} | views={report.get('actual_views')} "
                        f"| likes={report.get('actual_likes') or 0} "
                        f"| comments={report.get('actual_comments') or 0} "
                        f"| followers={report.get('followers_gained') or 0} "
                        f"| outcome={report.get('outcome') or 'unknown'} "
                        f"| notes={report.get('notes') or '-'}"
                    )
                )

        return "\n".join(lines)

    def _report_query(self, keyword: str, *, keyword_type: str):
        clean = keyword.strip()
        q = (
            self.db.query(PerformanceReportModel)
            .outerjoin(
                SuggestionModel,
                PerformanceReportModel.suggestion_id == SuggestionModel.id,
            )
            .filter(PerformanceReportModel.keyword.ilike(f"%{clean}%"))
        )
        if keyword_type == "beta":
            q = q.filter(
                or_(
                    SuggestionModel.keyword_type == "beta",
                    PerformanceReportModel.suggestion_id.is_(None),
                )
            )
        elif keyword_type == "nurture":
            q = q.filter(SuggestionModel.keyword_type == "nurture")
        return q

    def _fetch_reports(
        self,
        keyword: str,
        *,
        keyword_type: str,
        limit: int,
    ) -> List[PerformanceReportModel]:
        return (
            self._report_query(keyword, keyword_type=keyword_type)
            .order_by(PerformanceReportModel.reported_at.desc())
            .limit(limit)
            .all()
        )

    def _aggregate_reports(self, keyword: str, *, keyword_type: str) -> Dict[str, Any]:
        base = self._report_query(keyword, keyword_type=keyword_type)
        report_count = base.count()
        if report_count == 0:
            return {
                "report_count": 0,
                "avg_views": 0,
                "avg_engagement_rate": 0.0,
                "success_count": 0,
                "failure_count": 0,
            }

        avg_views, avg_engagement = (
            self.db.query(
                func.avg(PerformanceReportModel.actual_views),
                func.avg(PerformanceReportModel.engagement_rate),
            )
            .select_from(PerformanceReportModel)
            .outerjoin(
                SuggestionModel,
                PerformanceReportModel.suggestion_id == SuggestionModel.id,
            )
            .filter(PerformanceReportModel.keyword.ilike(f"%{keyword.strip()}%"))
            .filter(
                or_(
                    SuggestionModel.keyword_type == keyword_type,
                    PerformanceReportModel.suggestion_id.is_(None),
                )
                if keyword_type == "beta"
                else SuggestionModel.keyword_type == keyword_type
            )
            .one()
        )

        success_count = base.filter(PerformanceReportModel.outcome == "success").count()
        failure_count = base.filter(PerformanceReportModel.outcome == "failure").count()

        return {
            "report_count": report_count,
            "avg_views": int(avg_views or 0),
            "avg_engagement_rate": round(float(avg_engagement or 0.0), 4),
            "success_count": success_count,
            "failure_count": failure_count,
        }

    def _fetch_patterns(self, keyword: str, *, limit: int) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(KeywordPatternModel)
            .order_by(KeywordPatternModel.confidence.desc())
            .limit(max(limit * 4, 20))
            .all()
        )
        matched = [
            _pattern_row(row)
            for row in rows
            if _trait_matches_keyword(row.keyword_trait, keyword)
        ]
        return matched[:limit]

    def _fetch_niche(self) -> Dict[str, Any]:
        settings = self.db.query(SettingsModel).first()
        if not settings:
            return {"topics": [], "preferred_language": "both", "target_audience": None}
        topics = settings.niche_topics or []
        if isinstance(topics, str):
            topics = [topics]
        return {
            "topics": list(topics),
            "preferred_language": settings.niche_preferred_language or "both",
            "target_audience": settings.niche_target_audience,
        }

    def _apply_char_budget(self, context: Dict[str, Any]) -> Dict[str, Any]:
        serialized = self.serialize(context)
        if len(serialized) <= MAX_CONTEXT_CHARS:
            return context

        trimmed = dict(context)
        reports = list(trimmed.get("similar_reports") or [])
        patterns = list(trimmed.get("patterns") or [])

        while len(self.serialize(trimmed)) > MAX_CONTEXT_CHARS and reports:
            reports.pop()
            trimmed["similar_reports"] = reports

        while len(self.serialize(trimmed)) > MAX_CONTEXT_CHARS and patterns:
            patterns.pop()
            trimmed["patterns"] = patterns

        if len(self.serialize(trimmed)) > MAX_CONTEXT_CHARS:
            trimmed["patterns"] = []
            trimmed["similar_reports"] = trimmed.get("similar_reports", [])[:1]

        return trimmed
