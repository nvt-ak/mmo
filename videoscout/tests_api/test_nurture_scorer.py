"""Tests for nurture scoring + platform signals (US-060 / US-061)."""
from unittest.mock import MagicMock, patch

import pytest

from videoscout.core_engine.nurture_scorer import (
    _build_nurture_llm_prompt,
    compute_nurture_components,
    compute_title_relevance,
    detect_batch_risk_flags,
    score_nurture_candidates_batch,
    score_nurture_heuristic,
)
from videoscout.core_engine.platform_signals import build_platform_signals
from videoscout.core_engine.scoring_rubric import (
    BATCH_MIN_TOP_BOTTOM_GAP,
    BATCH_MIN_STD,
    batch_score_std,
    default_rubric_text,
    enforce_batch_relevance_tiebreak,
    enforce_batch_spread,
    resolve_scoring_rubric,
)
from videoscout.core_engine.trend_discovery import build_scored_candidate


def _candidate(keyword="viral dance trend", title="Viral Dance Trend Challenge 2026"):
    return {
        "keyword": keyword,
        "discovery_source": "youtube_trend",
        "trend_signals": {
            "source_title": title,
            "detected_at": "2026-07-02",
            "video_id": "vid1",
            "channel_id": "UC1",
        },
    }


def _gate(*, tier="moderate", score=0.7, views=50_000.0, count=12):
    return {
        "surface": True,
        "tiktok_unverified": False,
        "score": score,
        "tiktok_stats": {
            "video_count_7d": count,
            "avg_views": views,
            "avg_likes": 2500.0,
            "avg_comments": 120.0,
            "saturation_tier": tier,
        },
    }


def test_nurture_scores_differ_by_title_overlap():
    high = score_nurture_heuristic(
        _candidate("viral dance trend", "Viral Dance Trend Challenge"),
        tiktok_gate=_gate(),
        weights={
            "relevance": 0.30,
            "specificity": 0.25,
            "saturation": 0.25,
            "trend": 0.10,
            "video_performance": 0.10,
        },
    )
    low = score_nurture_heuristic(
        _candidate("viral dance trend", "Cooking pasta recipe"),
        tiktok_gate=_gate(),
        weights={
            "relevance": 0.30,
            "specificity": 0.25,
            "saturation": 0.25,
            "trend": 0.10,
            "video_performance": 0.10,
        },
    )
    assert high is not None and low is not None
    assert high["final_score"] != low["final_score"]
    assert high["component_scores"]["relevance"] > low["component_scores"]["relevance"]


def test_nurture_scores_differ_by_views():
    strong = score_nurture_heuristic(
        _candidate(),
        tiktok_gate=_gate(views=500_000.0),
        weights={
            "relevance": 0.30,
            "specificity": 0.25,
            "saturation": 0.25,
            "trend": 0.10,
            "video_performance": 0.10,
        },
    )
    weak = score_nurture_heuristic(
        _candidate(),
        tiktok_gate=_gate(views=500.0),
        weights={
            "relevance": 0.30,
            "specificity": 0.25,
            "saturation": 0.25,
            "trend": 0.10,
            "video_performance": 0.10,
        },
    )
    assert strong is not None and weak is not None
    assert strong["final_score"] != weak["final_score"]


def test_platform_signals_includes_agent_reasons():
    scored = score_nurture_heuristic(
        _candidate(),
        tiktok_gate=_gate(),
        weights={
            "relevance": 0.30,
            "specificity": 0.25,
            "saturation": 0.25,
            "trend": 0.10,
            "video_performance": 0.10,
        },
    )
    assert scored is not None
    signals = scored["platform_signals"]
    assert signals["tiktok"]["stats"]["avg_views"] == 50_000.0
    assert signals["youtube"]["video_id"] == "vid1"
    assert signals["agent"]["component_reasons"]["relevance"]
    assert signals["agent"]["rationale"]


def test_build_platform_signals_shape():
    candidate = _candidate()
    gate = _gate()
    components, reasons = compute_nurture_components(candidate, tiktok_gate=gate)
    payload = build_platform_signals(
        candidate=candidate,
        tiktok_gate=gate,
        component_scores=components,
        component_reasons=reasons,
        scored_with="test",
        rationale="test rationale",
        confidence=0.8,
    )
    assert payload["agent"]["scored_with"] == "test"
    assert payload["agent"]["confidence"] == 0.8


def test_build_scored_candidate_delegates_to_nurture_heuristic():
    scored = build_scored_candidate(
        _candidate("small business tips", "Small Business Tips For TikTok"),
        tiktok_gate=_gate(score=0.9, count=8, tier="fresh"),
        keyword_type_filter="nurture",
    )
    assert scored is not None
    assert scored["keyword_type"] == "nurture"
    assert "platform_signals" in scored
    assert scored["final_score"] != 0.75 or scored["component_scores"]["relevance"] != 0.5


@pytest.mark.asyncio
async def test_nurture_llm_batch_persists_rationale(db_session):
    items = [{"candidate": _candidate(), "tiktok_gate": _gate()}]
    llm_payload = {
        "scores": [
            {
                "keyword": "viral dance trend",
                "component_scores": {
                    "relevance": 0.82,
                    "specificity": 0.6,
                    "saturation": 0.7,
                    "trend": 0.75,
                    "video_performance": 0.68,
                },
                "component_reasons": {
                    "relevance": "Strong title overlap.",
                    "specificity": "3-word phrase.",
                    "saturation": "Moderate TikTok competition.",
                    "trend": "From YouTube trending.",
                    "video_performance": "Solid average views.",
                },
                "rationale": "Good nurture fit with moderate saturation.",
                "confidence": 0.88,
                "risk_flags": [],
            }
        ]
    }

    with patch(
        "videoscout.core_engine.nurture_scorer.create_llm_client",
        return_value=MagicMock(),
    ), patch(
        "videoscout.core_engine.nurture_scorer.get_llm_config",
        return_value={"model": "test-model"},
    ), patch(
        "videoscout.core_engine.nurture_scorer._call_llm_json",
        return_value=llm_payload,
    ):
        scored = await score_nurture_candidates_batch(
            items,
            db=db_session,
            keyword_type_filter="nurture",
        )

    assert len(scored) == 1
    assert scored[0]["platform_signals"]["agent"]["scored_with"] == "llm_nurture_batch"
    assert scored[0]["platform_signals"]["agent"]["rationale"] == (
        "Good nurture fit with moderate saturation."
    )
    blend = scored[0]["platform_signals"]["agent"]["blend"]
    assert blend["llm_weight"] == 0.6
    assert blend["heuristic_weight"] == 0.4
    assert "llm_final" in blend
    assert "heuristic_final" in blend


def test_nurture_rubric_loaded_in_prompt():
    prompt = _build_nurture_llm_prompt(
        [{"keyword": "test keyword", "heuristic_components": {}}],
        {"relevance": 0.30, "specificity": 0.25, "saturation": 0.25, "trend": 0.10, "video_performance": 0.10},
    )
    assert "relative_batch" in prompt
    assert "relative to other keywords" in prompt
    assert default_rubric_text("nurture")
    assert resolve_scoring_rubric("nurture") == default_rubric_text("nurture")


def _clustered_llm_payload(keywords: list[str]) -> dict:
    return {
        "scores": [
            {
                "keyword": kw,
                "component_scores": {
                    "relevance": 0.85,
                    "specificity": 0.60,
                    "saturation": 0.70,
                    "trend": 0.78,
                    "video_performance": 0.68,
                },
                "component_reasons": {
                    "relevance": "High overlap.",
                    "specificity": "3-word phrase.",
                    "saturation": "Moderate.",
                    "trend": "Trending.",
                    "video_performance": "OK views.",
                },
                "rationale": "Clustered LLM score.",
                "confidence": 0.85,
                "risk_flags": [],
            }
            for kw in keywords
        ]
    }


@pytest.mark.asyncio
async def test_nurture_golden_batch_spread_from_clustered_llm(db_session):
    title = "Small Business Tips For TikTok Growth 2026"
    keywords = [
        "small business tips",
        "business tips tiktok",
        "tips tiktok growth",
        "tiktok growth 2026",
    ]
    items = [
        {
            "candidate": _candidate(kw, title),
            "tiktok_gate": _gate(
                score=0.9 - i * 0.1,
                views=500_000 - i * 100_000,
                count=8 + i * 5,
                tier=["fresh", "moderate", "moderate", "saturated"][i],
            ),
        }
        for i, kw in enumerate(keywords)
    ]

    with patch(
        "videoscout.core_engine.nurture_scorer.create_llm_client",
        return_value=MagicMock(),
    ), patch(
        "videoscout.core_engine.nurture_scorer.get_llm_config",
        return_value={"model": "test-model"},
    ), patch(
        "videoscout.core_engine.nurture_scorer._call_llm_json",
        return_value=_clustered_llm_payload(keywords),
    ):
        scored = await score_nurture_candidates_batch(
            items,
            db=db_session,
            keyword_type_filter="nurture",
        )

    assert len(scored) == len(keywords)
    scores = [row["final_score"] for row in scored]
    assert batch_score_std(scored) >= BATCH_MIN_STD
    assert max(scores) - min(scores) >= BATCH_MIN_TOP_BOTTOM_GAP
    assert any(
        row["platform_signals"]["agent"].get("blend", {}).get("spread_enforced")
        for row in scored
    )


def test_enforce_batch_spread_stretches_flat_scores():
    flat_rows = []
    for i, score in enumerate([0.84, 0.85, 0.84, 0.85]):
        flat_rows.append(
            {
                "keyword": f"kw{i}",
                "final_score": score,
                "platform_signals": {
                    "agent": {
                        "blend": {
                            "heuristic_final": 0.50 + i * 0.12,
                        }
                    }
                },
            }
        )

    stretched = enforce_batch_spread(flat_rows)
    assert batch_score_std(stretched) >= BATCH_MIN_STD
    assert stretched[-1]["final_score"] > stretched[0]["final_score"]
    assert stretched[0]["platform_signals"]["agent"]["blend"]["spread_enforced"] is True


def test_schradin_golden_heuristic_components():
    """Golden-set from US-061 review — no component should hit 1.0."""
    title = "🤣😱MONTE & SCHRADIN sind BLIND?! - 15.000 PUNKTE in Meccha Chameleon! |"
    candidate = _candidate("schradin sind blind", title)
    gate = _gate(
        tier="fresh",
        score=1.0,
        views=5_650_000.0,
        count=2,
    )
    gate["tiktok_stats"]["avg_likes"] = 170_500.0
    gate["tiktok_stats"]["avg_comments"] = 4_342.0

    components, reasons = compute_nurture_components(candidate, tiktok_gate=gate)

    assert all(v <= 0.98 for v in components.values())
    assert components["relevance"] >= 0.90
    assert 0.65 <= components["specificity"] <= 0.75
    assert 0.88 <= components["saturation"] <= 0.96
    assert components["trend"] >= 0.80
    assert 0.90 <= components["video_performance"] <= 0.98
    assert "published in the last 7 days" in reasons["saturation"]
    assert "avg views" not in reasons["saturation"].lower()
    assert "5,650,000" in reasons["video_performance"]


def test_xhoni_golden_primary_hook_and_specificity():
    """Short title where keyword is the core hook — not secondary."""
    title = "DON XHONI - 100%"
    candidate = _candidate("xhoni 100", title)
    gate = _gate(tier="moderate", score=0.7, views=34_126.0, count=11)

    components, reasons = compute_nurture_components(candidate, tiktok_gate=gate)

    assert components["trend"] >= 0.82
    assert "Primary hook" in reasons["trend"]
    assert 0.58 <= components["specificity"] <= 0.65
    assert "named entity" in reasons["specificity"]
    assert "numeric identifier" in reasons["specificity"]
    assert "avg views" not in reasons["saturation"].lower()
    assert "11 videos" in reasons["saturation"]
    assert 0.72 <= components["video_performance"] <= 0.78


def test_trend_differs_by_hook_strength():
    title = "MONTE & SCHRADIN sind BLIND?! - 15.000 PUNKTE"
    main_components, _ = compute_nurture_components(
        _candidate("schradin sind blind", title),
        tiktok_gate=_gate(tier="fresh", count=2),
    )
    filler_components, _ = compute_nurture_components(
        _candidate("blind", title),
        tiktok_gate=_gate(tier="fresh", count=2),
    )
    assert main_components["trend"] > filler_components["trend"]


def test_confidence_reflects_data_coverage():
    scored = score_nurture_heuristic(
        _candidate("schradin sind blind", "MONTE & SCHRADIN sind BLIND?!"),
        tiktok_gate=_gate(tier="fresh", count=2, views=5_650_000.0),
        weights={
            "relevance": 0.30,
            "specificity": 0.25,
            "saturation": 0.25,
            "trend": 0.10,
            "video_performance": 0.10,
        },
    )
    assert scored is not None
    confidence = scored["platform_signals"]["agent"]["confidence"]
    assert 0.50 <= confidence <= 0.70


def test_detect_batch_duplicate_risk_flags():
    flags = detect_batch_risk_flags([
        "schradin sind blind",
        "blind schradin sind",
        "unrelated topic",
    ])
    assert "duplicate_of_batch_peer" in flags["schradin sind blind"]
    assert "duplicate_of_batch_peer" in flags["blind schradin sind"]
    assert "duplicate_of_batch_peer" not in flags["unrelated topic"]


def test_relevance_tiers():
    primary, reason = compute_title_relevance("xhoni 100", "DON XHONI - 100%")
    assert primary == 0.98
    assert "primary subject" in reason

    reordered, reason2 = compute_title_relevance(
        "schradin monte", "MONTE & SCHRADIN sind BLIND?!"
    )
    assert reordered == 0.95
    assert "minor normalization" in reason2


def test_relevance_tiebreak_spreads_clustered_batch():
    title = "DON XHONI - 100%"
    rows = []
    for kw in ("xhoni", "xhoni 100", "don xhoni"):
        scored = score_nurture_heuristic(
            _candidate(kw, title),
            tiktok_gate=_gate(tier="moderate", count=11, views=34_126.0),
            weights={
                "relevance": 0.30,
                "specificity": 0.25,
                "saturation": 0.25,
                "trend": 0.10,
                "video_performance": 0.10,
            },
        )
        assert scored is not None
        rows.append(scored)

    broken = enforce_batch_relevance_tiebreak(rows)
    relevances = [r["component_scores"]["relevance"] for r in broken]
    assert len(set(relevances)) == len(relevances)
    assert max(relevances) - min(relevances) >= 0.01

