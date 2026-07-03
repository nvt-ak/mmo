"""Keyword history prior from suggestion lifecycle (US-064)."""
from __future__ import annotations

from typing import Any, Dict, List, Set

from sqlalchemy import or_
from sqlalchemy.orm import Session

from videoscout.db.models import SuggestionModel


def _keyword_tokens(keyword: str) -> List[str]:
    return [token for token in keyword.lower().split() if len(token) > 2]


def build_history_prior(db: Session, keyword: str) -> Dict[str, Any]:
    """Summarize prior operator decisions on similar keywords."""
    tokens = _keyword_tokens(keyword)
    if not tokens:
        return {
            "similar_seen": 0,
            "approved_count": 0,
            "rejected_count": 0,
            "reported_count": 0,
            "prior_score": 0.5,
        }

    filters = [SuggestionModel.keyword.ilike(f"%{token}%") for token in tokens[:4]]
    rows: List[SuggestionModel] = (
        db.query(SuggestionModel)
        .filter(or_(*filters))
        .limit(40)
        .all()
    )

    keyword_lower = keyword.lower().strip()
    similar: List[SuggestionModel] = []
    seen: Set[str] = set()
    for row in rows:
        if row.keyword.lower() == keyword_lower:
            continue
        row_tokens = set(_keyword_tokens(row.keyword))
        if not row_tokens:
            continue
        overlap = len(row_tokens & set(tokens)) / max(len(tokens), 1)
        if overlap < 0.34:
            continue
        if row.keyword.lower() in seen:
            continue
        seen.add(row.keyword.lower())
        similar.append(row)

    approved = sum(1 for row in similar if row.status == "approved")
    rejected = sum(1 for row in similar if row.status == "rejected")
    reported = sum(1 for row in similar if row.status == "reported")

    total = approved + rejected + reported
    if total == 0:
        prior_score = 0.5
    else:
        prior_score = round((approved + reported * 0.5) / total, 4)
        if rejected > approved:
            prior_score = round(max(0.1, prior_score - 0.15), 4)

    return {
        "similar_seen": len(similar),
        "approved_count": approved,
        "rejected_count": rejected,
        "reported_count": reported,
        "prior_score": prior_score,
    }
