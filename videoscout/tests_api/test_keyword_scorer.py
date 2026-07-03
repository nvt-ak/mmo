"""Tests for beta LLM keyword scoring (US-055)."""
import json
from unittest.mock import MagicMock

import pytest

from videoscout.core_engine.keyword_scorer import (
    BLEND_HEURISTIC_WEIGHT,
    BLEND_LLM_WEIGHT,
    clamp_components,
    heuristic_final_score,
    score_beta_candidate,
    score_beta_candidates_batch,
    weighted_final_score,
)
from videoscout.db.models import PerformanceReportModel, SettingsModel, SuggestionModel


def _tiktok_gate(*, tier="moderate", score=0.7, surface=True, unverified=False):
    return {
        "surface": surface,
        "tiktok_unverified": unverified,
        "score": score,
        "tiktok_stats": {
            "video_count_7d": 12,
            "avg_views": 5000.0,
            "avg_likes": 200.0,
            "avg_comments": 20.0,
            "saturation_tier": tier,
        },
    }


def _candidate(keyword="beta long tail keyword phrase"):
    return {
        "keyword": keyword,
        "discovery_source": "youtube_trend",
        "trend_signals": {"source_title": "Example title", "detected_at": "2026-07-02"},
    }


def _llm_response(components=None, confidence=0.85):
    return {
        "component_scores": components or {
            "relevance": 0.8,
            "specificity": 0.75,
            "saturation": 0.65,
            "trend": 0.6,
            "video_performance": 0.55,
        },
        "rationale": "Strong niche fit with moderate competition.",
        "risk_flags": ["moderate_saturation"],
        "confidence": confidence,
    }


def _mock_llm(payload):
    llm = MagicMock()
    message = MagicMock()
    message.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = message
    llm.chat.completions.create.return_value = MagicMock(choices=[choice])
    return llm


def _batch_llm_response(keywords, components=None):
    base = components or {
        "relevance": 0.8,
        "specificity": 0.75,
        "saturation": 0.65,
        "trend": 0.6,
        "video_performance": 0.55,
    }
    return {
        "scores": [
            {
                "keyword": keyword,
                "component_scores": dict(base),
                "rationale": f"Score for {keyword}",
                "risk_flags": ["moderate_saturation"],
                "confidence": 0.85,
            }
            for keyword in keywords
        ]
    }


@pytest.mark.asyncio
async def test_score_beta_candidate_returns_llm_components(db_session):
    keyword = "beta long tail keyword phrase"
    scored = await score_beta_candidate(
        _candidate(keyword=keyword),
        tiktok_gate=_tiktok_gate(),
        db=db_session,
        llm_client=_mock_llm(_batch_llm_response([keyword])),
    )

    assert scored is not None
    assert scored["keyword_type"] == "beta"
    assert scored["component_scores"]["relevance"] == 0.8
    assert scored["trend_signals"]["scoring"]["rationale"]
    assert scored["trend_signals"]["scoring"]["confidence"] == 0.85
    assert scored["final_score"] >= 0.4
    assert scored["trend_signals"]["scoring"]["scored_with"] == "llm_beta_batch"


@pytest.mark.asyncio
async def test_score_beta_blocks_unverified_gate(db_session):
    scored = await score_beta_candidate(
        _candidate(),
        tiktok_gate=_tiktok_gate(surface=False, unverified=True),
        db=db_session,
        llm_client=_mock_llm(_llm_response()),
    )
    assert scored is None


@pytest.mark.asyncio
async def test_score_beta_blocks_short_phrase(db_session):
    scored = await score_beta_candidate(
        _candidate(keyword="two words"),
        tiktok_gate=_tiktok_gate(),
        db=db_session,
        llm_client=_mock_llm(_llm_response()),
    )
    assert scored is None


@pytest.mark.asyncio
async def test_score_beta_caps_saturated_component(db_session):
    keyword = "beta long tail keyword phrase"
    scored = await score_beta_candidate(
        _candidate(keyword=keyword),
        tiktok_gate=_tiktok_gate(tier="saturated", score=0.3),
        db=db_session,
        llm_client=_mock_llm(_batch_llm_response(
            [keyword],
            {"relevance": 0.7, "specificity": 0.7, "saturation": 0.9, "trend": 0.5, "video_performance": 0.5},
        )),
    )
    assert scored is not None
    assert scored["component_scores"]["saturation"] <= 0.3


@pytest.mark.asyncio
async def test_score_beta_blend_when_few_reports(db_session):
    keyword = "beta long tail keyword phrase"
    gate = _tiktok_gate()
    llm = _mock_llm(_batch_llm_response([keyword]))

    llm_final = weighted_final_score(_llm_response()["component_scores"], {
        "relevance": 0.30,
        "specificity": 0.25,
        "saturation": 0.25,
        "trend": 0.10,
        "video_performance": 0.10,
    })
    heuristic_final = heuristic_final_score(keyword, gate)
    expected = round(BLEND_LLM_WEIGHT * llm_final + BLEND_HEURISTIC_WEIGHT * heuristic_final, 3)

    scored = await score_beta_candidate(
        _candidate(keyword=keyword),
        tiktok_gate=gate,
        db=db_session,
        llm_client=llm,
    )

    assert scored is not None
    assert scored["final_score"] == expected
    assert scored["trend_signals"]["scoring"]["blend"]["linked_beta_reports"] == 0


@pytest.mark.asyncio
async def test_score_beta_no_blend_after_calibration_threshold(db_session):
    suggestion = SuggestionModel(
        keyword="existing beta keyword",
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

    for idx in range(20):
        db_session.add(
            PerformanceReportModel(
                keyword=f"report {idx}",
                suggestion_id=suggestion.id,
                actual_views=1000 + idx,
                outcome="success",
            )
        )
    db_session.commit()

    components = _llm_response()["component_scores"]
    keyword = "beta long tail keyword phrase"
    llm_final = weighted_final_score(components, {
        "relevance": 0.30,
        "specificity": 0.25,
        "saturation": 0.25,
        "trend": 0.10,
        "video_performance": 0.10,
    })

    scored = await score_beta_candidate(
        _candidate(keyword=keyword),
        tiktok_gate=_tiktok_gate(),
        db=db_session,
        llm_client=_mock_llm(_batch_llm_response([keyword], components)),
    )

    assert scored is not None
    assert scored["final_score"] == llm_final
    assert scored["trend_signals"]["scoring"]["blend"] is None


@pytest.mark.asyncio
async def test_score_beta_llm_failure_returns_none(db_session):
    llm = MagicMock()
    llm.chat.completions.create.side_effect = RuntimeError("llm down")

    scored = await score_beta_candidate(
        _candidate(),
        tiktok_gate=_tiktok_gate(),
        db=db_session,
        llm_client=llm,
    )
    assert scored is None


def test_weighted_final_score_recomputes_server_side():
    components = {
        "relevance": 0.8,
        "specificity": 0.7,
        "saturation": 0.6,
        "trend": 0.5,
        "video_performance": 0.4,
    }
    weights = {
        "relevance": 0.30,
        "specificity": 0.25,
        "saturation": 0.25,
        "trend": 0.10,
        "video_performance": 0.10,
    }
    assert weighted_final_score(components, weights) == pytest.approx(0.655)


def test_clamp_components():
    assert clamp_components({"relevance": 1.4, "specificity": -0.2, "saturation": 0.5, "trend": 0.5, "video_performance": 0.5}) == {
        "relevance": 1.0,
        "specificity": 0.0,
        "saturation": 0.5,
        "trend": 0.5,
        "video_performance": 0.5,
    }


@pytest.mark.asyncio
async def test_score_beta_candidates_batch_single_llm_call(db_session):
    keywords = [
        "beta long tail keyword phrase",
        "another beta keyword phrase here",
    ]
    llm = _mock_llm(_batch_llm_response(keywords))
    items = [
        {"candidate": _candidate(keyword=k), "tiktok_gate": _tiktok_gate()}
        for k in keywords
    ]

    scored = await score_beta_candidates_batch(
        items,
        db=db_session,
        llm_client=llm,
    )

    assert len(scored) == 2
    assert llm.chat.completions.create.call_count == 1
    assert {row["keyword"] for row in scored} == set(keywords)


@pytest.mark.asyncio
async def test_score_beta_candidates_batch_skips_failed_chunk(db_session):
    llm = MagicMock()
    llm.chat.completions.create.side_effect = RuntimeError("llm down")
    items = [{"candidate": _candidate(), "tiktok_gate": _tiktok_gate()}]

    scored = await score_beta_candidates_batch(items, db=db_session, llm_client=llm)
    assert scored == []


@pytest.mark.asyncio
async def test_score_beta_candidates_batch_splits_on_timeout(db_session):
    keywords = [
        "beta long tail keyword phrase",
        "another beta keyword phrase here",
        "third beta keyword phrase now",
        "fourth beta keyword phrase test",
    ]
    items = [
        {"candidate": _candidate(keyword=k), "tiktok_gate": _tiktok_gate()}
        for k in keywords
    ]

    def side_effect(*args, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        matched = [k for k in keywords if k in prompt]
        if len(matched) > 2:
            raise RuntimeError("Request timed out.")
        return _mock_llm(_batch_llm_response(matched)).chat.completions.create.return_value

    llm = MagicMock()
    llm.chat.completions.create.side_effect = side_effect

    scored = await score_beta_candidates_batch(
        items,
        db=db_session,
        llm_client=llm,
    )

    assert len(scored) == 4
    assert llm.chat.completions.create.call_count == 3
