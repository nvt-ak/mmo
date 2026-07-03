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


def apply_final_ranking(scored_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Re-rank after enrichment using derived lifecycle (not persisted on evidence)."""
    ranked: List[Dict[str, Any]] = []
    for row in scored_items:
        updated = copy.deepcopy(row)
        evidence = dict(updated.get("trend_evidence") or {})
        lifecycle = LifecycleClassifier.classify(evidence)
        history = (evidence.get("derived") or {}).get("history_prior") or {}

        base = float(updated.get("final_score") or 0.0)
        adjusted = base
        adjusted += LIFECYCLE_ADJUSTMENTS.get(lifecycle, 0.0)
        adjusted += _history_adjustment(history)
        adjusted += _supply_pressure_adjustment(evidence)
        adjusted = round(max(0.0, min(0.98, adjusted)), 3)

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
                blend=agent.get("blend"),
                lifecycle_stage=lifecycle,
            )
        ranked.append(updated)

    ranked.sort(key=lambda item: item.get("final_score", 0.0), reverse=True)
    return ranked
