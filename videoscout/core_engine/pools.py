"""Pool type helpers for typed media pools (R7b)."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from videoscout.db.models import SuggestionModel

VALID_POOL_TYPES = frozenset({"nurture", "beta"})
VALID_POOL_STATUSES = frozenset({
    "pending_review",
    "ready",
    "assigned",
    "posted",
})


def resolve_pool_type(db: Session, suggestion_id: Optional[uuid.UUID]) -> str:
    if not suggestion_id:
        return "beta"
    row = db.query(SuggestionModel).filter(SuggestionModel.id == suggestion_id).first()
    if not row or row.keyword_type not in VALID_POOL_TYPES:
        return "beta"
    return row.keyword_type


def mark_pool_ready(asset, db: Session) -> None:
    """Apply pool fields when operator keeps a video in batch review."""
    asset.pool_type = resolve_pool_type(db, asset.suggestion_id)
    asset.pool_status = "ready"
