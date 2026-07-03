"""Top-N TrendEvidence enrichment — Tier-1 channel + round-trip validation (US-063)."""
from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from videoscout.core_engine.engine import SuggestionEngine
from videoscout.core_engine.trend_evidence import serialize_evidence
from videoscout.db.models import ChannelModel
from videoscout.services.youtube import get_youtube_service

logger = logging.getLogger(__name__)

TOP_N_ENRICHMENT = 10
YOUTUBE_SEARCH_MAX_RESULTS = 25
TIKTOK_DEEP_LIMIT = 50


def load_tier1_channel(db: Session, channel_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Tier-1 enrichment from channels already in DB (0 YouTube quota)."""
    if not channel_id:
        return None
    row = (
        db.query(ChannelModel)
        .filter(ChannelModel.channel_id == channel_id)
        .first()
    )
    if row is None:
        return None
    return {
        "tier": 1,
        "source": "db",
        "channel_id": row.channel_id,
        "name": row.name,
        "subscriber_count": row.subscriber_count,
        "last_video_count": row.last_video_count,
        "scan_enabled": bool(row.scan_enabled),
    }


def _creator_diversity(items: List[Dict[str, Any]], creator_key: str) -> Dict[str, Any]:
    total = len(items)
    creators = {
        str(item.get(creator_key) or "").strip()
        for item in items
        if str(item.get(creator_key) or "").strip()
    }
    unique = len(creators)
    diversity = round(unique / total, 4) if total else 0.0
    return {
        "video_count": total,
        "unique_creators": unique,
        "creator_diversity": diversity,
    }


def compute_supply_pressure(
    *,
    youtube_videos: List[Dict[str, Any]],
    tiktok_result: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Derived supply/demand pressure from cross-platform search."""
    yt = _creator_diversity(youtube_videos, "channel_id")
    tt_videos = list((tiktok_result or {}).get("videos") or [])
    tt = _creator_diversity(tt_videos, "author_id")

    yt_count = yt["video_count"]
    tt_count = int((tiktok_result or {}).get("total_count") or tt["video_count"] or 0)
    combined_creators = yt["unique_creators"] + tt["unique_creators"]
    combined_videos = yt_count + tt_count

    # Higher pressure when many videos but few distinct creators (one-off viral pattern).
    if combined_videos == 0:
        pressure_score = 0.0
    else:
        avg_diversity = (yt["creator_diversity"] + tt["creator_diversity"]) / 2.0
        volume_factor = min(1.0, combined_videos / 40.0)
        pressure_score = round(volume_factor * (1.0 - avg_diversity * 0.7), 4)

    return {
        "youtube": yt,
        "tiktok": {
            "video_count": tt_count,
            "unique_creators": tt["unique_creators"],
            "creator_diversity": tt["creator_diversity"],
            "avg_engagement_rate": float((tiktok_result or {}).get("avg_engagement_rate") or 0.0),
        },
        "combined_unique_creators": combined_creators,
        "pressure_score": pressure_score,
    }


def merge_enrichment_into_evidence(
    evidence: Dict[str, Any],
    *,
    channel_raw: Optional[Dict[str, Any]],
    youtube_search_raw: Optional[Dict[str, Any]],
    tiktok_raw: Optional[Dict[str, Any]],
    supply_pressure: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    merged = copy.deepcopy(evidence)
    raw = dict(merged.get("raw") or {})
    derived = dict(merged.get("derived") or {})
    metadata = dict(merged.get("metadata") or {})

    if channel_raw is not None:
        raw["channel"] = channel_raw
    if youtube_search_raw is not None:
        raw["youtube_search"] = youtube_search_raw
    if tiktok_raw is not None:
        raw["tiktok"] = tiktok_raw
    if supply_pressure is not None:
        derived["supply_pressure"] = supply_pressure

    enrichment_tier = 0
    if channel_raw:
        enrichment_tier = max(enrichment_tier, 1)
    if youtube_search_raw or tiktok_raw:
        enrichment_tier = max(enrichment_tier, 2)
    metadata["enrichment_tier"] = enrichment_tier

    merged["raw"] = raw
    merged["derived"] = derived
    merged["metadata"] = metadata
    return serialize_evidence(merged)


async def enrich_scored_candidate(
    scored: Dict[str, Any],
    *,
    db: Session,
    engine: SuggestionEngine,
) -> Dict[str, Any]:
    """Tier-1 + tier-2 enrichment for one scored keyword."""
    evidence = scored.get("trend_evidence")
    if not evidence:
        return scored

    youtube_block = (evidence.get("raw") or {}).get("youtube") or {}
    channel_id = youtube_block.get("channel_id")
    keyword = scored["keyword"]

    channel_raw = load_tier1_channel(db, channel_id)

    youtube_videos: List[Dict[str, Any]] = []
    try:
        youtube_videos = get_youtube_service().search_videos_by_keyword(
            keyword,
            max_results=YOUTUBE_SEARCH_MAX_RESULTS,
        )
    except Exception as exc:
        logger.warning("YouTube enrichment failed for %r: %s", keyword, exc)

    youtube_search_raw = {
        "keyword": keyword,
        "days": 7,
        "videos": youtube_videos,
    }

    tiktok_raw: Optional[Dict[str, Any]] = None
    try:
        tiktok_result = await engine.tiktok.search_videos_async(
            keyword,
            period="7d",
            limit=TIKTOK_DEEP_LIMIT,
        )
        if isinstance(tiktok_result, dict) and not tiktok_result.get("error"):
            tiktok_raw = {
                "keyword": keyword,
                "period": "7d",
                "total_count": tiktok_result.get("total_count", 0),
                "avg_views": tiktok_result.get("avg_views", 0.0),
                "avg_likes": tiktok_result.get("avg_likes", 0.0),
                "avg_comments": tiktok_result.get("avg_comments", 0.0),
                "avg_engagement_rate": tiktok_result.get("avg_engagement_rate", 0.0),
                "videos": tiktok_result.get("videos") or [],
            }
    except Exception as exc:
        logger.warning("TikTok deep enrichment failed for %r: %s", keyword, exc)

    supply_pressure = compute_supply_pressure(
        youtube_videos=youtube_videos,
        tiktok_result=tiktok_raw,
    )

    enriched_evidence = merge_enrichment_into_evidence(
        evidence,
        channel_raw=channel_raw,
        youtube_search_raw=youtube_search_raw,
        tiktok_raw=tiktok_raw,
        supply_pressure=supply_pressure,
    )

    updated = dict(scored)
    updated["trend_evidence"] = enriched_evidence
    if updated.get("platform_signals"):
        from videoscout.core_engine.platform_signals import build_platform_signals

        candidate = {
            "keyword": keyword,
            "discovery_source": scored.get("discovery_source"),
            "trend_signals": scored.get("trend_signals"),
            "trend_evidence": enriched_evidence,
        }
        tiktok_gate = {
            "tiktok_unverified": scored.get("tiktok_unverified", False),
            "score": (updated["platform_signals"].get("tiktok") or {}).get("gate_score", 0.0),
            "tiktok_stats": scored.get("tiktok_stats") or {},
        }
        agent = updated["platform_signals"].get("agent") or {}
        updated["platform_signals"] = build_platform_signals(
            candidate=candidate,
            tiktok_gate=tiktok_gate,
            component_scores=scored.get("component_scores") or {},
            component_reasons=(agent.get("component_reasons") or {}),
            scored_with=agent.get("scored_with", "enriched"),
            rationale=agent.get("rationale"),
            confidence=agent.get("confidence"),
            risk_flags=agent.get("risk_flags"),
            blend=agent.get("blend"),
        )
    return updated


async def enrich_top_scored(
    scored_items: List[Dict[str, Any]],
    *,
    db: Session,
    engine: SuggestionEngine,
    top_n: int = TOP_N_ENRICHMENT,
) -> List[Dict[str, Any]]:
    """Enrich top-N by final_score; pass through the rest unchanged."""
    if not scored_items:
        return []

    ranked = sorted(scored_items, key=lambda row: row.get("final_score", 0.0), reverse=True)
    top_keys = {row["keyword"].lower() for row in ranked[:top_n]}

    enriched: List[Dict[str, Any]] = []
    for row in ranked:
        if row["keyword"].lower() in top_keys:
            enriched.append(
                await enrich_scored_candidate(row, db=db, engine=engine)
            )
        else:
            enriched.append(row)
    return enriched
