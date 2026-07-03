"""Dual-source candidate video feeds for discovery (US-064)."""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterator, List, Tuple

from sqlalchemy.orm import Session

from videoscout.core_engine.trend_evidence import attach_velocity_to_videos, compute_velocity_percentiles
from videoscout.db.models import SettingsModel
from videoscout.services.youtube import get_youtube_service

logger = logging.getLogger(__name__)

SourceKind = str  # "most_popular" | "velocity"

DEFAULT_EMERGENCE_QUERIES = ("trending", "viral", "news")


def _emergence_queries(db: Session) -> List[str]:
    settings = db.query(SettingsModel).first()
    topics = list((settings.niche_topics if settings else None) or [])
    cleaned = [str(topic).strip() for topic in topics if str(topic).strip()]
    return cleaned[:3] if cleaned else list(DEFAULT_EMERGENCE_QUERIES)


def fetch_discovery_sources(
    *,
    region_code: str,
    popular_limit: int,
    velocity_limit: int,
    db: Session,
) -> List[Tuple[SourceKind, List[Dict[str, Any]]]]:
    """Return separate source feeds — do not merge before candidate extract."""
    youtube = get_youtube_service()
    popular = youtube.get_trending_videos(
        region_code=region_code,
        max_results=popular_limit,
    )
    velocity = youtube.get_emergence_videos(
        region_code=region_code,
        max_results=velocity_limit,
        search_queries=_emergence_queries(db),
    )
    return [
        ("most_popular", popular),
        ("velocity", velocity),
    ]


def iter_scored_source_videos(
    sources: List[Tuple[SourceKind, List[Dict[str, Any]]]],
    *,
    region_code: str,
) -> Iterator[Tuple[SourceKind, Dict[str, Any], Dict[str, float]]]:
    """Attach velocity + per-source percentiles for each feed independently."""
    for source_kind, videos in sources:
        if not videos:
            continue
        enriched = attach_velocity_to_videos(videos)
        percentiles = compute_velocity_percentiles(enriched, region=region_code)
        for video in enriched:
            yield source_kind, video, percentiles
