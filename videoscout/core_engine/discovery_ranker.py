"""Final discovery ranking — lifecycle + history + supply pressure (US-064)."""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from videoscout.core_engine.platform_signals import build_platform_signals
from videoscout.core_engine.trend_evidence import LifecycleClassifier

LIFECYCLE_ADJUSTMENTS = {
    "early_accelerating": 0.04,
    "stable": 0.01,
    "late": -0.03,
    "noise": -0.06,
    "unknown": 0.0,
}


def _history_adjustment(history_prior: Optional[Dict[str, Any]]) -> float:
    if not history_prior:
        return 0.0
    prior = float(history_prior.get("prior_score") or 0.5)
    rejected = int(history_prior.get("rejected_count") or 0)
    approved = int(history_prior.get("approved_count") or 0)
    delta = (prior - 0.5) * 0.08
    if rejected > approved:
        delta -= 0.02
    return delta


def _supply_pressure_adjustment(evidence: Dict[str, Any]) -> float:
    supply = (evidence.get("derived") or {}).get("supply_pressure") or {}
    pressure = float(supply.get("pressure_score") or 0.0)
    if pressure >= 0.75:
        return -0.04
    if pressure >= 0.5:
        return -0.02
    return 0.0


def _trends_adjustment(evidence: Dict[str, Any]) -> float:
    trends = (evidence.get("raw") or {}).get("google_trends") or {}
    if not trends:
        return 0.0
    delta = 0.0
    interest = trends.get("interest_index")
    if interest is not None:
        interest_val = float(interest)
        if interest_val >= 80:
            delta += 0.03
        elif interest_val >= 50:
            delta += 0.01
    growth = trends.get("growth_pct")
    if growth == "breakout":
        delta += 0.03
    elif isinstance(growth, (int, float)) and float(growth) >= 200:
        delta += 0.02
    return delta


def _agent_blend(row: Dict[str, Any]) -> Dict[str, Any]:
    """Merge calibration blend from trend_signals when agent.blend only has spread meta."""
    agent = (row.get("platform_signals") or {}).get("agent") or {}
    blend = dict(agent.get("blend") or {})
    scoring_blend = ((row.get("trend_signals") or {}).get("scoring") or {}).get("blend") or {}
    if scoring_blend and not blend.get("llm_final"):
        blend = {**scoring_blend, **blend}
    return blend


def apply_final_ranking(scored_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Re-rank after enrichment using derived lifecycle (not persisted on evidence)."""
    ranked: List[Dict[str, Any]] = []
    for row in scored_items:
        updated = copy.deepcopy(row)
        evidence = dict(updated.get("trend_evidence") or {})
        lifecycle = LifecycleClassifier.classify(evidence)
        history = (evidence.get("derived") or {}).get("history_prior") or {}

        base = float(updated.get("final_score") or 0.0)
        lifecycle_delta = LIFECYCLE_ADJUSTMENTS.get(lifecycle, 0.0)
        history_delta = _history_adjustment(history)
        supply_delta = _supply_pressure_adjustment(evidence)
        trends_delta = _trends_adjustment(evidence)
        adjusted = base + lifecycle_delta + history_delta + supply_delta + trends_delta
        adjusted = round(max(0.0, min(0.98, adjusted)), 3)
        ranking_adjustments = {
            "pre_ranking_score": round(base, 3),
            "lifecycle_stage": lifecycle,
            "lifecycle_delta": lifecycle_delta,
            "history_delta": history_delta,
            "supply_pressure_delta": supply_delta,
            "trends_delta": trends_delta,
            "post_ranking_score": adjusted,
        }

        updated["final_score"] = adjusted
        updated["lifecycle_stage"] = lifecycle

        if updated.get("platform_signals"):
            candidate = {
                "keyword": updated["keyword"],
                "discovery_source": updated.get("discovery_source"),
                "trend_signals": updated.get("trend_signals"),
                "trend_evidence": evidence,
            }
            agent = dict(updated["platform_signals"].get("agent") or {})
            blend = _agent_blend(updated)
            tiktok_block = updated["platform_signals"].get("tiktok") or {}
            tiktok_gate = {
                "tiktok_unverified": tiktok_block.get("unverified", False),
                "score": tiktok_block.get("gate_score", 0.0),
                "tiktok_stats": tiktok_block.get("stats") or updated.get("tiktok_stats") or {},
            }
            updated["platform_signals"] = build_platform_signals(
                candidate=candidate,
                tiktok_gate=tiktok_gate,
                component_scores=updated.get("component_scores") or {},
                component_reasons=agent.get("component_reasons") or {},
                scored_with=agent.get("scored_with", "ranked"),
                rationale=agent.get("rationale"),
                confidence=agent.get("confidence"),
                risk_flags=list(agent.get("risk_flags") or []),
                blend=blend,
                lifecycle_stage=lifecycle,
                ranking_adjustments=ranking_adjustments,
            )
        ranked.append(updated)

    ranked.sort(key=lambda item: item.get("final_score", 0.0), reverse=True)
    return ranked
