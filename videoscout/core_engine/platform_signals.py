"""Structured per-platform keyword signals + agent scoring metadata."""
from __future__ import annotations

from typing import Any, Dict, Optional

from videoscout.core_engine.trend_evidence import velocity_percentile_from_evidence


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
    trend_evidence = dict(candidate.get("trend_evidence") or {})
    youtube_raw = (trend_evidence.get("raw") or {}).get("youtube") or {}
    tiktok_stats = dict(tiktok_gate.get("tiktok_stats") or {})
    tier_to_status = {"fresh": "low", "moderate": "moderate", "saturated": "saturated"}
    saturation_tier = tiktok_stats.get("saturation_tier", "moderate")
    velocity_percentile = velocity_percentile_from_evidence(trend_evidence or None)

    youtube_block: Dict[str, Any] = {
        "discovery_source": candidate.get("discovery_source"),
        "source_title": youtube_raw.get("source_title") or trend_signals.get("source_title"),
        "video_id": youtube_raw.get("source_video_id") or trend_signals.get("video_id"),
        "channel_id": youtube_raw.get("channel_id") or trend_signals.get("channel_id"),
    }
    if velocity_percentile is not None:
        youtube_block["velocity_percentile"] = velocity_percentile
    if trend_evidence.get("schema_version"):
        youtube_block["evidence_schema_version"] = trend_evidence["schema_version"]

    return {
        "tiktok": {
            "status": tier_to_status.get(saturation_tier, "moderate"),
            "unverified": bool(tiktok_gate.get("tiktok_unverified", False)),
            "gate_score": float(tiktok_gate.get("score", 0.0) or 0.0),
            "stats": tiktok_stats,
        },
        "youtube": youtube_block,
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
