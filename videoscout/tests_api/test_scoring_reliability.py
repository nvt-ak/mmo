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
    reconcile_heuristic_components_for_blend,
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
    assert scored["platform_signals"]["agent"]["blend"]["llm_final"] == blend["llm_final"]


def test_reconcile_heuristic_pulls_overoptimistic_relevance():
    llm = {
        "relevance": 0.59,
        "specificity": 0.654,
        "saturation": 0.78,
        "trend": 0.68,
        "video_performance": 0.53,
    }
    heuristic = {
        "relevance": 0.98,
        "specificity": 0.855,
        "saturation": 0.902,
        "trend": 0.5,
        "video_performance": 0.775,
    }
    reconciled = reconcile_heuristic_components_for_blend(llm, heuristic)
    assert reconciled["relevance"] < heuristic["relevance"]
    assert reconciled["relevance"] > llm["relevance"]

    weights = _weights()
    raw_final = weighted_final_score(heuristic, weights)
    blend_final = weighted_final_score(reconciled, weights)
    assert blend_final < raw_final


def test_yara_style_scores_stay_below_spread_ladder():
    """Regression: flat beta batch must not jump to 0.92 via nurture spread ladder."""
    llm = {
        "relevance": 0.59,
        "specificity": 0.654,
        "saturation": 0.78,
        "trend": 0.68,
        "video_performance": 0.53,
    }
    heuristic_raw = {
        "relevance": 0.98,
        "specificity": 0.855,
        "saturation": 0.902,
        "trend": 0.5,
        "video_performance": 0.775,
    }
    weights = _weights()
    llm_final = weighted_final_score(llm, weights)
    heur = reconcile_heuristic_components_for_blend(llm, heuristic_raw)
    heur_final = weighted_final_score(heur, weights)
    blended = round(BLEND_LLM_WEIGHT * llm_final + BLEND_HEURISTIC_WEIGHT * heur_final, 3)
    assert blended < 0.80
    assert blended != 0.92
