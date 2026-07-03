"""TrendEvidence v1 — versioned discovery pipeline contract (ADR 0013 / US-062)."""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "1"

SOURCE_MOST_POPULAR = "youtube_most_popular"
CONFIDENCE_POPULARITY = "popularity"


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_published_at(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return None


def compute_velocity_raw(view_count: int, published_at: Optional[str]) -> Optional[float]:
    """log(views) / sqrt(hours) with hours >= 1."""
    if view_count <= 0:
        return None
    published = _parse_published_at(published_at)
    if published is None:
        return None
    now = datetime.now(timezone.utc)
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    hours = max((now - published).total_seconds() / 3600.0, 1.0)
    return round(math.log(view_count) / math.sqrt(hours), 4)


def _percentile_rank(value: float, peers: List[float]) -> float:
    if not peers:
        return 0.5
    if len(peers) == 1:
        return 0.5
    below = sum(1 for peer in peers if peer < value)
    equal = sum(1 for peer in peers if peer == value)
    return round((below + 0.5 * equal) / len(peers), 4)


def compute_velocity_percentiles(
    videos: List[Dict[str, Any]],
    *,
    region: str,
) -> Dict[str, float]:
    """Percentile of raw velocity within (region, category_id) groups in this batch."""
    grouped: Dict[Tuple[str, str], List[Tuple[str, float]]] = defaultdict(list)
    for video in videos:
        video_id = str(video.get("id") or "")
        raw = video.get("velocity_raw")
        if video_id and raw is not None:
            category = str(video.get("category_id") or "unknown")
            grouped[(region, category)].append((video_id, float(raw)))

    percentiles: Dict[str, float] = {}
    for entries in grouped.values():
        values = [value for _, value in entries]
        for video_id, raw in entries:
            percentiles[video_id] = _percentile_rank(raw, values)
    return percentiles


def attach_velocity_to_videos(videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for video in videos:
        item = dict(video)
        item["velocity_raw"] = compute_velocity_raw(
            int(item.get("view_count") or 0),
            item.get("published_at"),
        )
        enriched.append(item)
    return enriched


class EvidenceBuilder:
    """Build TrendEvidence from source video + keyword candidate."""

    def __init__(self, *, pipeline_run_id: str, region: str) -> None:
        self.pipeline_run_id = pipeline_run_id
        self.region = region

    def build(
        self,
        *,
        keyword: str,
        source_video: Dict[str, Any],
        discovery_source: str = "youtube_trend",
        velocity_percentile: Optional[float] = None,
        enrichment_tier: int = 0,
    ) -> Dict[str, Any]:
        velocity_raw = source_video.get("velocity_raw")
        if velocity_raw is None:
            velocity_raw = compute_velocity_raw(
                int(source_video.get("view_count") or 0),
                source_video.get("published_at"),
            )

        derived_velocity: Dict[str, Any] = {}
        if velocity_raw is not None:
            derived_velocity["raw"] = velocity_raw
        if velocity_percentile is not None:
            derived_velocity["percentile_region_category"] = velocity_percentile

        return {
            "schema_version": SCHEMA_VERSION,
            "keyword": keyword,
            "metadata": {
                "created_at": _utc_now_iso(),
                "pipeline_run_id": self.pipeline_run_id,
                "enrichment_tier": enrichment_tier,
            },
            "provenance": {
                "source": SOURCE_MOST_POPULAR,
                "confidence_type": CONFIDENCE_POPULARITY,
                "region": self.region,
                "detected_at": _utc_now_iso(),
            },
            "raw": {
                "youtube": {
                    "source_video_id": source_video.get("id"),
                    "source_title": source_video.get("title"),
                    "channel_id": source_video.get("channel_id"),
                    "published_at": source_video.get("published_at"),
                    "view_count": source_video.get("view_count"),
                    "category_id": source_video.get("category_id"),
                },
                "youtube_search": None,
                "tiktok": None,
                "channel": None,
            },
            "derived": {
                "velocity": derived_velocity or None,
                "supply_pressure": None,
                "history_prior": None,
            },
        }


class LifecycleClassifier:
    """Derive lifecycle stage from evidence — not persisted (ADR 0013)."""

    @staticmethod
    def classify(evidence: Dict[str, Any]) -> str:
        velocity = (evidence.get("derived") or {}).get("velocity") or {}
        percentile = velocity.get("percentile_region_category")
        if percentile is None:
            return "unknown"
        if percentile >= 0.75:
            return "early_accelerating"
        if percentile >= 0.45:
            return "stable"
        if percentile >= 0.25:
            return "late"
        return "noise"


def velocity_percentile_from_evidence(evidence: Optional[Dict[str, Any]]) -> Optional[float]:
    if not evidence:
        return None
    velocity = (evidence.get("derived") or {}).get("velocity") or {}
    raw = velocity.get("percentile_region_category")
    if raw is None:
        return None
    return float(raw)


def trend_signals_from_evidence(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Backward-compatible trend_signals slice for nurture/beta scorers."""
    youtube = (evidence.get("raw") or {}).get("youtube") or {}
    return {
        "source_title": youtube.get("source_title"),
        "video_id": youtube.get("source_video_id"),
        "channel_id": youtube.get("channel_id"),
        "detected_at": (evidence.get("provenance") or {}).get("detected_at"),
    }


def serialize_evidence(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Validate raw/derived/metadata separation before persistence."""
    for key in ("schema_version", "keyword", "metadata", "provenance", "raw", "derived"):
        if key not in evidence:
            raise ValueError(f"TrendEvidence missing required key: {key}")
    if "velocity" in evidence.get("raw", {}):
        raise ValueError("velocity must live under derived, not raw")
    if "lifecycle" in evidence:
        raise ValueError("lifecycle must not be persisted on TrendEvidence")
    return evidence


def replay_evidence(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Load stored TrendEvidence for debug/replay."""
    if not payload:
        return None
    if payload.get("schema_version") != SCHEMA_VERSION:
        return payload
    return dict(payload)
