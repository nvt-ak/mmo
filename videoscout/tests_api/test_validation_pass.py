"""Tests for validation pass (US-065)."""
import pytest

from videoscout.core_engine.validation_pass import (
    _heuristic_validation,
    apply_validation_result,
    discovery_validation_enabled,
)


def _scored_with_evidence(youtube_stats: dict, rq: dict) -> dict:
    return {
        "keyword": "test keyword phrase",
        "final_score": 0.82,
        "component_scores": {
            "trend": 0.84,
            "relevance": 0.80,
            "specificity": 0.75,
            "saturation": 0.70,
            "video_performance": 0.65,
        },
        "platform_signals": {
            "tiktok": {"unverified": False, "gate_score": 0.7, "stats": {}},
            "agent": {
                "scored_with": "test",
                "confidence": 0.75,
                "component_reasons": {},
                "risk_flags": [],
            },
        },
        "trend_evidence": {
            "schema_version": "2",
            "derived": {
                "search_sample": {"youtube": youtube_stats, "tiktok": {}},
                "representation_quality": rq,
            },
        },
        "tiktok_stats": {},
    }


def test_heuristic_validation_flags_viral_outlier():
    validation = _heuristic_validation(
        _scored_with_evidence(
            {"viral_outlier": True, "top_contribution_pct": 96, "median_views": 7000, "sample_size": 5},
            {"representation_confidence": "high"},
        )
    )
    assert validation["validation_status"] == "weakened"
    assert "single_viral_source" in validation["risk_flags"]


def test_apply_validation_locks_trend_relevance_specificity():
    scored = _scored_with_evidence(
        {"viral_outlier": False, "sample_size": 10, "median_views": 8000},
        {"representation_confidence": "mixed"},
    )
    validation = _heuristic_validation(scored)
    updated = apply_validation_result(scored, validation)
    assert updated["component_scores"]["trend"] == pytest.approx(0.84)
    assert updated["component_scores"]["relevance"] == pytest.approx(0.80)
    assert updated["component_scores"]["specificity"] == pytest.approx(0.75)
    assert updated["platform_signals"]["agent"]["validation"]["validation_status"]


def test_fragmented_pattern_reduces_confidence():
    scored = _scored_with_evidence(
        {"viral_outlier": False, "sample_size": 8, "median_views": 5000},
        {"representation_confidence": "low", "pattern_purity": 0.2},
    )
    validation = _heuristic_validation(scored)
    updated = apply_validation_result(scored, validation)
    assert validation["pattern_assessment"] == "fragmented"
    assert updated["platform_signals"]["agent"]["confidence"] < 0.75


def test_discovery_validation_enabled_default():
    assert discovery_validation_enabled() is True


def test_build_validation_prompt_includes_ambiguous_pairs():
    from videoscout.core_engine.validation_pass import _build_validation_prompt

    prompt = _build_validation_prompt(
        [{"keyword": "alpha beta"}],
        [("alpha beta", "alpha betas", 0.52)],
    )
    assert "ambiguous_pairs" in prompt
    assert "pair_groupings" in prompt
    assert "alpha betas" in prompt
