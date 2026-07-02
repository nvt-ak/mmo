"""Tests for KeywordContextBuilder (US-054)."""
from datetime import datetime

from videoscout.core_engine.keyword_context import (
    MAX_CONTEXT_CHARS,
    KeywordContextBuilder,
)
from videoscout.core_engine.knowledge_base import KnowledgeBase
from videoscout.db.models import (
    KeywordPatternModel,
    PerformanceReportModel,
    SettingsModel,
    SuggestionModel,
)


def _add_beta_report(db_session, *, keyword, suggestion_id=None, outcome="success", views=5000):
    report = PerformanceReportModel(
        keyword=keyword,
        suggestion_id=suggestion_id,
        actual_views=views,
        actual_likes=400,
        actual_comments=30,
        engagement_rate=0.08,
        outcome=outcome,
        reported_at=datetime.utcnow(),
        notes="test note",
    )
    db_session.add(report)
    db_session.commit()
    return report


def test_build_empty_keyword_returns_empty(db_session):
    builder = KeywordContextBuilder(db_session)
    assert builder.build("") == {}
    assert builder.build("   ") == {}


def test_build_includes_reports_aggregates_and_niche(db_session):
    suggestion = SuggestionModel(
        keyword="ai marketing tips",
        final_score=0.75,
        component_scores={
            "relevance": 0.8,
            "specificity": 0.7,
            "saturation": 0.6,
            "trend": 0.5,
            "video_performance": 0.5,
        },
        suggested_by=[],
        keyword_type="beta",
    )
    db_session.add(suggestion)
    db_session.add(
        SettingsModel(
            niche_topics=["AI", "marketing"],
            niche_preferred_language="en",
            niche_target_audience="creators",
        )
    )
    db_session.commit()

    _add_beta_report(
        db_session,
        keyword="ai marketing tips",
        suggestion_id=suggestion.id,
        views=8000,
    )

    ctx = KeywordContextBuilder(db_session).build("ai marketing tips", keyword_type="beta")

    assert ctx["keyword"] == "ai marketing tips"
    assert len(ctx["similar_reports"]) == 1
    assert ctx["aggregates"]["report_count"] == 1
    assert ctx["aggregates"]["avg_views"] == 8000
    assert ctx["aggregates"]["success_count"] == 1
    assert ctx["niche"]["topics"] == ["AI", "marketing"]
    assert ctx["niche"]["target_audience"] == "creators"


def test_beta_filter_excludes_nurture_linked_reports(db_session):
    beta = SuggestionModel(
        keyword="beta keyword phrase",
        final_score=0.7,
        component_scores={
            "relevance": 0.7,
            "specificity": 0.7,
            "saturation": 0.7,
            "trend": 0.5,
            "video_performance": 0.5,
        },
        suggested_by=[],
        keyword_type="beta",
    )
    nurture = SuggestionModel(
        keyword="nurture keyword phrase",
        final_score=0.5,
        component_scores={
            "relevance": 0.5,
            "specificity": 0.5,
            "saturation": 0.5,
            "trend": 0.5,
            "video_performance": 0.5,
        },
        suggested_by=[],
        keyword_type="nurture",
    )
    db_session.add_all([beta, nurture])
    db_session.commit()

    _add_beta_report(db_session, keyword="beta keyword phrase", suggestion_id=beta.id)
    _add_beta_report(db_session, keyword="nurture keyword phrase", suggestion_id=nurture.id)

    ctx = KeywordContextBuilder(db_session).build("keyword phrase", keyword_type="beta")

    keywords = {row["keyword"] for row in ctx["similar_reports"]}
    assert "beta keyword phrase" in keywords
    assert "nurture keyword phrase" not in keywords


def test_patterns_matched_by_trait_overlap(db_session):
    db_session.add(
        KeywordPatternModel(
            pattern_type="overestimate",
            keyword_trait="tiktok tips saturated",
            outcome_type="false_positive",
            insight="Broad saturated terms underperform",
            confidence=0.85,
            occurrence_count=4,
            suggested_adjustment={"specificity": -0.05},
        )
    )
    db_session.commit()

    ctx = KeywordContextBuilder(db_session).build(
        "small business tiktok tips",
        keyword_type="beta",
    )

    assert len(ctx["patterns"]) == 1
    assert ctx["patterns"][0]["keyword_trait"] == "tiktok tips saturated"


def test_char_budget_trims_large_context(db_session):
    suggestion = SuggestionModel(
        keyword="long tail keyword example",
        final_score=0.7,
        component_scores={
            "relevance": 0.7,
            "specificity": 0.7,
            "saturation": 0.7,
            "trend": 0.5,
            "video_performance": 0.5,
        },
        suggested_by=[],
        keyword_type="beta",
    )
    db_session.add(suggestion)
    db_session.commit()

    for idx in range(12):
        _add_beta_report(
            db_session,
            keyword=f"long tail keyword example {idx}",
            suggestion_id=suggestion.id,
            views=1000 + idx,
            outcome="failure" if idx % 2 else "success",
        )

    for idx in range(8):
        db_session.add(
            KeywordPatternModel(
                pattern_type="correlation",
                keyword_trait=f"long tail pattern trait {idx}",
                outcome_type="false_positive",
                insight=f"Insight number {idx} with extra detail to inflate payload size",
                confidence=0.9 - idx * 0.01,
                occurrence_count=idx + 1,
            )
        )
    db_session.commit()

    ctx = KeywordContextBuilder(db_session).build("long tail keyword", keyword_type="beta", limit=10)
    assert len(KeywordContextBuilder(db_session).serialize(ctx)) <= MAX_CONTEXT_CHARS


def test_knowledge_base_get_context_text_format(db_session):
    suggestion = SuggestionModel(
        keyword="ai marketing tips",
        final_score=0.75,
        component_scores={
            "relevance": 0.8,
            "specificity": 0.7,
            "saturation": 0.6,
            "trend": 0.5,
            "video_performance": 0.5,
        },
        suggested_by=[],
        keyword_type="beta",
    )
    db_session.add(suggestion)
    db_session.commit()
    _add_beta_report(
        db_session,
        keyword="ai marketing tips",
        suggestion_id=suggestion.id,
    )

    text = KnowledgeBase(db_session).get_context("ai marketing tips")

    assert "Keyword insight seed: ai marketing tips" in text
    assert "Recent evidence:" in text
    assert "views=8000" in text or "views=5000" in text
