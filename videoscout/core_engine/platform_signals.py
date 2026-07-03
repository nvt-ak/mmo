"""Structured per-platform keyword signals + agent scoring metadata."""
from __future__ import annotations

from typing import Any, Dict, Optional


def build_platform_signals(
    *,
    candidate: Dict[str, Any],
    tiktok_gate: Dict[str, Any],
    component_scores: Dict[str, float],
    component_reasons: Dict[str, str],
    scored_with: str,
    rationale: Optional[str] = None,
    confidence: Optional[float] = None,
    risk_flags: Optional[list] = None,
    blend: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    trend_signals = dict(candidate.get("trend_signals") or {})
    tiktok_stats = dict(tiktok_gate.get("tiktok_stats") or {})
    tier_to_status = {"fresh": "low", "moderate": "moderate", "saturated": "saturated"}
    saturation_tier = tiktok_stats.get("saturation_tier", "moderate")

    return {
        "tiktok": {
            "status": tier_to_status.get(saturation_tier, "moderate"),
            "unverified": bool(tiktok_gate.get("tiktok_unverified", False)),
            "gate_score": float(tiktok_gate.get("score", 0.0) or 0.0),
            "stats": tiktok_stats,
        },
        "youtube": {
            "discovery_source": candidate.get("discovery_source"),
            "source_title": trend_signals.get("source_title"),
            "video_id": trend_signals.get("video_id"),
            "channel_id": trend_signals.get("channel_id"),
        },
        "agent": {
            "scored_with": scored_with,
            "rationale": rationale or "",
            "confidence": round(float(confidence or 0.0), 3),
            "risk_flags": list(risk_flags or []),
            "component_scores": component_scores,
            "component_reasons": component_reasons,
            **({"blend": blend} if blend else {}),
        },
    }
