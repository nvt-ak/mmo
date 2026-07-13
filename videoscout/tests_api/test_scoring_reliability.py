"""Tests for beta heuristic reliability and LLM validation (US-071)."""
import json
from unittest.mock import MagicMock

import pytest

from videoscout.core_engine.keyword_scorer import (
    BLEND_HEURISTIC_WEIGHT,
    BLEND_LLM_WEIGHT,
    _heuristic_components,
    heuristic_final_score,
    score_beta_candidate,
    weighted_final_score,
)
from videoscout.core_engine.scoring_rubric import enforce_batch_spread
from videoscout.core_engine.scoring_validation import (
    calibration_blend_weights,
    validate_llm_components,
)


def _weights():
    return {
        "relevance": 0.30,
        "specificity": 0.25,
        "saturation": 0.25,
        "trend": 0.10,
        "video_performance": 0.10,
    }


def _gate(*, tier="moderate", count=12, views=50_000.0):
    return {
        "surface": True,
        "tiktok_unverified": False,
        "score": 0.7,
        "tiktok_stats": {
            "video_count_7d": count,
            "avg_views": views,
            "avg_likes": 2500.0,
            "avg_comments": 120.0,
            "saturation_tier": tier,
        },
    }


def test_beta_heuristic_uses_title_signals_not_constants():
    high = _heuristic_components(
        "viral dance trend",
        _gate(),
        candidate={
            "discovery_source": "youtube_trend",
            "trend_signals": {"source_title": "Viral Dance Trend Challenge 2026"},
        },
    )
    low = _heuristic_components(
        "viral dance trend",
        _gate(),
        candidate={
            "discovery_source": "youtube_trend",
            "trend_signals": {"source_title": "Cooking pasta recipe"},
        },
    )

    assert high["relevance"] != 0.5
    assert high["trend"] != 0.7
    assert high["relevance"] > low["relevance"]
    assert high["trend"] >= low["trend"]


def test_heuristic_final_score_uses_all_component_weights():
    keyword = "beta long tail keyword phrase"
    gate = _gate(tier="fresh", count=3, views=120_000.0)
    candidate = {
        "keyword": keyword,
        "discovery_source": "youtube_trend",
        "trend_signals": {"source_title": "Beta Long Tail Keyword Phrase Guide"},
    }
    weights = _weights()
    components = _heuristic_components(keyword, gate, candidate=candidate)
    expected = weighted_final_score(components, weights)
    assert heuristic_final_score(keyword, gate, candidate=candidate, weights=weights) == expected


def test_validate_llm_components_pulls_saturated_saturation():
    heuristic = {
        "relevance": 0.7,
        "specificity": 0.7,
        "saturation": 0.22,
        "trend": 0.6,
        "video_performance": 0.5,
    }
    llm = dict(heuristic)
    llm["saturation"] = 0.85

    validated, adjusted = validate_llm_components(
        llm,
        heuristic,
        saturation_tier="saturated",
    )
    assert validated["saturation"] <= 0.3
    assert adjusted["saturation"] is True


def test_validate_llm_components_blends_outlier_specificity():
    heuristic = {
        "relevance": 0.7,
        "specificity": 0.62,
        "saturation": 0.7,
        "trend": 0.6,
        "video_performance": 0.5,
    }
    llm = dict(heuristic)
    llm["specificity"] = 0.95

    validated, adjusted = validate_llm_components(
        llm,
        heuristic,
        saturation_tier="moderate",
    )
    assert validated["specificity"] < llm["specificity"]
    assert adjusted["specificity"] is True


def test_calibration_blend_ramps_before_threshold():
    llm_w, heur_w = calibration_blend_weights(
        10,
        threshold=20,
        llm_weight_uncalibrated=BLEND_LLM_WEIGHT,
    )
    assert llm_w > BLEND_LLM_WEIGHT
    assert llm_w < 1.0
    assert round(llm_w + heur_w, 3) == 1.0

    full_llm, no_heur = calibration_blend_weights(
        20,
        threshold=20,
        llm_weight_uncalibrated=BLEND_LLM_WEIGHT,
    )
    assert full_llm == 1.0
    assert no_heur == 0.0


@pytest.mark.asyncio
async def test_score_beta_records_validation_and_ramp(db_session):
    keyword = "beta long tail keyword phrase"
    gate = _gate()
    candidate = {
        "keyword": keyword,
        "discovery_source": "youtube_trend",
        "trend_signals": {"source_title": "Beta Long Tail Keyword Phrase Tips"},
    }
    llm = MagicMock()
    message = MagicMock()
    message.content = json.dumps({
        "scores": [{
            "keyword": keyword,
            "component_scores": {
                "relevance": 0.8,
                "specificity": 0.95,
                "saturation": 0.9,
                "trend": 0.6,
                "video_performance": 0.55,
            },
            "component_reasons": {},
            "rationale": "Test",
            "confidence": 0.8,
            "risk_flags": [],
        }],
    })
    choice = MagicMock()
    choice.message = message
    llm.chat.completions.create.return_value = MagicMock(choices=[choice])

    scored = await score_beta_candidate(
        candidate,
        tiktok_gate=gate,
        db=db_session,
        llm_client=llm,
    )
    assert scored is not None
    blend = scored["trend_signals"]["scoring"]["blend"]
    assert blend["llm_weight"] == BLEND_LLM_WEIGHT
    assert blend["heuristic_weight"] == BLEND_HEURISTIC_WEIGHT
    assert "heuristic_components" in blend
    assert blend["heuristic_components"]["relevance"] != 0.5
    assert scored["component_scores"]["saturation"] < 0.9
