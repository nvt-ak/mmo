"""Tests for discovery inbox qualification gates (US-073)."""
from videoscout.core_engine.discovery_qualification import qualifies_for_inbox


def _beta_row(**overrides):
    base = {
        "keyword": "beta keyword phrase example",
        "keyword_type": "beta",
        "final_score": 0.62,
        "component_scores": {
            "relevance": 0.55,
            "specificity": 0.7,
            "saturation": 0.65,
            "trend": 0.5,
            "video_performance": 0.5,
        },
    }
    base.update(overrides)
    return base


def test_qualifies_beta_at_threshold():
    assert qualifies_for_inbox(
        _beta_row(final_score=0.55),
        min_score_threshold=0.55,
        min_specificity=0.4,
    )


def test_rejects_beta_below_min_score():
    assert not qualifies_for_inbox(
        _beta_row(final_score=0.54),
        min_score_threshold=0.55,
        min_specificity=0.4,
    )


def test_rejects_beta_with_zero_relevance():
    components = _beta_row()["component_scores"].copy()
    components["relevance"] = 0.0
    assert not qualifies_for_inbox(
        _beta_row(component_scores=components),
        min_score_threshold=0.55,
        min_specificity=0.4,
    )


def test_rejects_beta_low_specificity():
    components = _beta_row()["component_scores"].copy()
    components["specificity"] = 0.35
    assert not qualifies_for_inbox(
        _beta_row(component_scores=components),
        min_score_threshold=0.55,
        min_specificity=0.4,
    )


def test_nurture_uses_lower_floor():
    row = {
        "keyword": "viral trend",
        "keyword_type": "nurture",
        "final_score": 0.28,
        "component_scores": {},
    }
    assert qualifies_for_inbox(
        row,
        min_score_threshold=0.55,
        min_specificity=0.4,
    )
