"""Knowledge base utilities backed by performance reports."""
from __future__ import annotations

from sqlalchemy.orm import Session

from videoscout.core_engine.keyword_context import KeywordContextBuilder


class KnowledgeBase:
    """Read-only helper that builds LLM-friendly context from report history."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self._builder = KeywordContextBuilder(db_session)

    def build_context(
        self,
        keyword: str,
        *,
        keyword_type: str = "beta",
        limit: int = 5,
        tiktok_hint: dict | None = None,
    ) -> dict:
        """Structured context for beta LLM scoring."""
        return self._builder.build(
            keyword,
            keyword_type=keyword_type,
            limit=limit,
            tiktok_hint=tiktok_hint,
        )

    def get_context(self, keyword: str, limit: int = 5) -> str:
        """
        Return formatted context for a keyword from recent performance reports.

        Delegates to KeywordContextBuilder; preserves legacy text format for scan path.
        """
        context = self._builder.build(keyword, keyword_type="beta", limit=limit)
        return self._builder.to_text(context)
