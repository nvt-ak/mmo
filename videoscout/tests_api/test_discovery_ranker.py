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
