"""Tests for keyword history prior (US-064)."""
from videoscout.core_engine.history_prior import build_history_prior
from videoscout.db.models import SuggestionModel


def test_history_prior_boosts_when_similar_approved(db_session):
    db_session.add_all([
        SuggestionModel(
            keyword="business marketing tips",
            final_score=0.7,
            component_scores={
                "relevance": 0.7, "specificity": 0.7,
                "saturation": 0.7, "trend": 0.7, "video_performance": 0.7,
            },
            suggested_by=[{"source": "manual", "score": 0.7, "timestamp": "2026-07-01"}],
            status="approved",
            keyword_type="nurture",
        ),
        SuggestionModel(
            keyword="business growth hacks",
            final_score=0.4,
            component_scores={
                "relevance": 0.4, "specificity": 0.4,
                "saturation": 0.4, "trend": 0.4, "video_performance": 0.4,
            },
            suggested_by=[{"source": "manual", "score": 0.4, "timestamp": "2026-07-01"}],
            status="rejected",
            keyword_type="nurture",
        ),
    ])
    db_session.commit()

    prior = build_history_prior(db_session, "business startup tips")
    assert prior["similar_seen"] >= 1
    assert prior["prior_score"] >= 0.0
    assert prior["prior_score"] <= 1.0


def test_history_prior_neutral_when_no_matches(db_session):
    prior = build_history_prior(db_session, "unique keyword phrase")
    assert prior["similar_seen"] == 0
    assert prior["prior_score"] == 0.5
