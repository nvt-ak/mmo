"""Regression tests for cross-track reclassification reroute (US-070)."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from videoscout.core_engine.keyword_classifier import classify_keyword_type
from videoscout.core_engine.keyword_scorer import (
    _finalize_beta_score,
    score_beta_candidates_batch,
)
from videoscout.core_engine.nurture_scorer import (
    score_nurture_candidates_batch,
    score_nurture_heuristic,
)
from videoscout.core_engine.scoring_reroute import (
    is_reroute,
    should_accept_reroute,
    split_finalize_results,
)


def _weights():
    return {
        "relevance": 0.30,
        "specificity": 0.25,
        "saturation": 0.25,
        "trend": 0.10,
        "video_performance": 0.10,
    }


def _llm_payload(high: bool = True):
    if high:
        return {
            "component_scores": {
                "relevance": 0.9,
                "specificity": 0.85,
                "saturation": 0.8,
                "trend": 0.8,
                "video_performance": 0.75,
            },
            "component_reasons": {},
            "rationale": "Strong niche fit.",
            "confidence": 0.9,
            "risk_flags": [],
        }
    return {
        "component_scores": {
            "relevance": 0.2,
            "specificity": 0.3,
            "saturation": 0.3,
            "trend": 0.3,
            "video_performance": 0.3,
        },
        "component_reasons": {},
        "rationale": "Weak saturated match.",
        "confidence": 0.4,
        "risk_flags": [],
    }


def test_should_accept_reroute_respects_filter():
    assert should_accept_reroute("beta", "both")
    assert should_accept_reroute("beta", "beta")
    assert not should_accept_reroute("beta", "nurture")
    assert should_accept_reroute("nurture", "both")
    assert should_accept_reroute("nurture", "nurture")
    assert not should_accept_reroute("nurture", "beta")


def test_provisional_beta_flips_to_nurture_when_saturated():
    keyword = "small business tiktok tips"
    assert classify_keyword_type(keyword, trend_source="youtube_trend") == "beta"

    result = _finalize_beta_score(
        {"keyword": keyword, "discovery_source": "youtube_trend"},
        tiktok_gate={
            "surface": True,
            "score": 0.3,
            "tiktok_stats": {"saturation_tier": "saturated", "video_count_7d": 80},
        },
        llm_payload=_llm_payload(high=False),
        weights=_weights(),
        min_score=0.25,
        keyword_type_filter="both",
        linked_reports=0,
    )
    assert is_reroute(result)
    assert result["to_track"] == "nurture"
    assert result["from_track"] == "beta"


def test_nurture_heuristic_reroutes_to_beta_on_high_score():
    keyword = "niche ai tools"
    assert classify_keyword_type(keyword, trend_source="niche_web") == "nurture"

    candidate = {
        "keyword": keyword,
        "discovery_source": "niche_web",
        "trend_signals": {
            "source_title": "Niche AI Tools Guide for Creators 2026",
            "detected_at": "2026-07-02",
        },
    }
    gate = {
        "surface": True,
        "tiktok_unverified": False,
        "score": 0.85,
        "tiktok_stats": {
            "video_count_7d": 3,
            "avg_views": 120_000.0,
            "avg_likes": 5000.0,
            "avg_comments": 300.0,
            "saturation_tier": "fresh",
        },
    }

    result = score_nurture_heuristic(
        candidate,
        tiktok_gate=gate,
        weights=_weights(),
        keyword_type_filter="both",
    )
    assert is_reroute(result)
    assert result["to_track"] == "beta"
    assert result["keyword"] == keyword


def test_strict_filter_drops_cross_track_without_reroute():
    keyword = "niche ai tools"
    result = score_nurture_heuristic(
        {
            "keyword": keyword,
            "discovery_source": "niche_web",
            "trend_signals": {
                "source_title": "Niche AI Tools Guide for Creators 2026",
                "detected_at": "2026-07-02",
            },
        },
        tiktok_gate={
            "surface": True,
            "score": 0.85,
            "tiktok_stats": {
                "video_count_7d": 3,
                "avg_views": 120_000.0,
                "saturation_tier": "fresh",
            },
        },
        weights=_weights(),
        keyword_type_filter="nurture",
    )
    assert result is None


def test_split_finalize_results_separates_reroutes():
    scored, reroutes = split_finalize_results(
        [
            {"keyword": "keep me", "final_score": 0.8},
            {
                "_scoring_reroute": True,
                "to_track": "beta",
                "from_track": "nurture",
                "keyword": "route me",
                "final_score": 0.7,
                "item": {},
            },
            None,
        ]
    )
    assert len(scored) == 1
    assert scored[0]["keyword"] == "keep me"
    assert len(reroutes) == 1
    assert reroutes[0]["keyword"] == "route me"


@pytest.mark.asyncio
async def test_nurture_batch_reroutes_to_beta_scorer(db_session):
    keyword = "niche ai tools"
    candidate = {
        "keyword": keyword,
        "discovery_source": "niche_web",
        "trend_signals": {
            "source_title": "Niche AI Tools Guide for Creators 2026",
            "detected_at": "2026-07-02",
        },
    }
    item = {
        "candidate": candidate,
        "tiktok_gate": {
            "surface": True,
            "score": 0.85,
            "tiktok_stats": {
                "video_count_7d": 3,
                "avg_views": 120_000.0,
                "saturation_tier": "fresh",
            },
        },
    }

    async def fake_beta_batch(items, **kwargs):
        assert len(items) == 1
        assert items[0]["candidate"]["keyword"] == keyword
        return [{
            "keyword": keyword,
            "keyword_type": "beta",
            "discovery_source": "niche_web",
            "final_score": 0.82,
            "component_scores": _llm_payload()["component_scores"],
            "gate_profile": "full",
            "trend_signals": candidate["trend_signals"],
            "platform_signals": {},
            "tiktok_status": "low",
            "tiktok_count": 3,
            "tiktok_stats": item["tiktok_gate"]["tiktok_stats"],
            "tiktok_unverified": False,
        }]

    with patch(
        "videoscout.core_engine.nurture_scorer._call_llm_json",
        side_effect=Exception("force heuristic"),
    ), patch(
        "videoscout.core_engine.keyword_scorer.score_beta_candidates_batch",
        side_effect=fake_beta_batch,
    ):
        scored = await score_nurture_candidates_batch(
            [item],
            db=db_session,
            keyword_type_filter="both",
        )

    assert len(scored) == 1
    assert scored[0]["keyword_type"] == "beta"
    assert scored[0]["keyword"] == keyword


@pytest.mark.asyncio
async def test_beta_batch_reroutes_to_nurture_scorer(db_session):
    keyword = "small business tiktok tips"
    candidate = {"keyword": keyword, "discovery_source": "youtube_trend"}
    item = {
        "candidate": candidate,
        "tiktok_gate": {
            "surface": True,
            "score": 0.3,
            "tiktok_stats": {
                "video_count_7d": 80,
                "saturation_tier": "saturated",
            },
        },
    }

    llm = MagicMock()
    message = MagicMock()
    message.content = json.dumps({
        "scores": [{
            "keyword": keyword,
            **_llm_payload(high=False),
        }],
    })
    choice = MagicMock()
    choice.message = message
    llm.chat.completions.create.return_value = MagicMock(choices=[choice])

    async def fake_nurture_batch(items, **kwargs):
        assert len(items) == 1
        assert items[0]["candidate"]["keyword"] == keyword
        return [{
            "keyword": keyword,
            "keyword_type": "nurture",
            "discovery_source": "youtube_trend",
            "final_score": 0.71,
            "component_scores": _llm_payload()["component_scores"],
            "gate_profile": "light",
            "trend_signals": {},
            "platform_signals": {},
            "tiktok_status": "saturated",
            "tiktok_count": 80,
            "tiktok_stats": item["tiktok_gate"]["tiktok_stats"],
            "tiktok_unverified": False,
        }]

    with patch(
        "videoscout.core_engine.keyword_scorer.create_llm_client",
        return_value=llm,
    ), patch(
        "videoscout.core_engine.keyword_scorer.get_llm_config",
        return_value={"model": "test-model"},
    ), patch(
        "videoscout.core_engine.keyword_scorer.KeywordContextBuilder.build",
        return_value={},
    ), patch(
        "videoscout.core_engine.nurture_scorer.score_nurture_candidates_batch",
        side_effect=fake_nurture_batch,
    ):
        scored = await score_beta_candidates_batch(
            [item],
            db=db_session,
            keyword_type_filter="both",
            llm_client=llm,
        )

    assert len(scored) == 1
    assert scored[0]["keyword_type"] == "nurture"
    assert scored[0]["keyword"] == keyword
