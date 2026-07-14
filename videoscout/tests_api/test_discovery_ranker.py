"""Tests for discovery final ranker (US-064)."""
from videoscout.core_engine.discovery_ranker import apply_final_ranking


def _scored(keyword: str, score: float, evidence: dict) -> dict:
    return {
        "keyword": keyword,
        "final_score": score,
        "component_scores": {"trend": 0.5},
        "platform_signals": {
            "tiktok": {"unverified": False, "gate_score": 0.5, "stats": {}},
            "agent": {"scored_with": "test", "component_reasons": {}},
        },
        "trend_evidence": evidence,
        "tiktok_stats": {},
    }


def test_apply_final_ranking_prefers_early_accelerating():
    early = _scored(
        "early keyword phrase",
        0.70,
        {
            "provenance": {"confidence_type": "emergence"},
            "derived": {
                "velocity": {"percentile_region_category": 0.9},
                "history_prior": {"prior_score": 0.6, "rejected_count": 0, "approved_count": 1},
            },
        },
    )
    noise = _scored(
        "noise keyword phrase",
        0.72,
        {
            "provenance": {"confidence_type": "popularity"},
            "derived": {
                "velocity": {"percentile_region_category": 0.1},
                "history_prior": {"prior_score": 0.5, "rejected_count": 0, "approved_count": 0},
            },
        },
    )
    ranked = apply_final_ranking([noise, early])
    assert ranked[0]["keyword"] == early["keyword"]
    assert ranked[0]["lifecycle_stage"] == "early_accelerating"
    assert "lifecycle_stage" in ranked[0]["platform_signals"]["agent"]
    ranking = ranked[0]["platform_signals"]["agent"]["ranking_adjustments"]
    assert ranking["pre_ranking_score"] == 0.70
    assert ranking["lifecycle_delta"] == 0.04
    assert ranking["post_ranking_score"] == ranked[0]["final_score"]


def test_apply_final_ranking_penalizes_high_supply_pressure():
    low_pressure = _scored(
        "low pressure keyword",
        0.65,
        {
            "derived": {
                "velocity": {"percentile_region_category": 0.6},
                "supply_pressure": {"pressure_score": 0.2},
            },
        },
    )
    high_pressure = _scored(
        "high pressure keyword",
        0.65,
        {
            "derived": {
                "velocity": {"percentile_region_category": 0.6},
                "supply_pressure": {"pressure_score": 0.9},
            },
        },
    )
    ranked = apply_final_ranking([high_pressure, low_pressure])
    assert ranked[0]["keyword"] == low_pressure["keyword"]
    assert ranked[1]["lifecycle_stage"] == "late"


def test_apply_final_ranking_boosts_google_trends_breakout():
    trends_row = _scored(
        "trends breakout keyword",
        0.60,
        {
            "raw": {
                "google_trends": {
                    "interest_index": 85,
                    "growth_pct": "breakout",
                    "gprop": "youtube",
                },
            },
            "derived": {},
        },
    )
    plain = _scored(
        "plain keyword phrase",
        0.62,
        {
            "derived": {
                "velocity": {"percentile_region_category": 0.5},
            },
        },
    )
    ranked = apply_final_ranking([plain, trends_row])
    assert ranked[0]["keyword"] == trends_row["keyword"]
    ranking = ranked[0]["platform_signals"]["agent"]["ranking_adjustments"]
    assert ranking["trends_delta"] > 0
