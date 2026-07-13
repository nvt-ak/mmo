"""Keyword-based YouTube channel discovery and scoring."""
from dataclasses import dataclass
from typing import List
import logging

from videoscout.services.youtube import get_youtube_service

logger = logging.getLogger(__name__)


@dataclass
class ChannelCandidate:
    youtube_channel_id: str
    name: str
    description: str
    thumbnail_url: str
    subscriber_count: int
    video_count: int
    avg_views: int
    discovery_score: float


# Minimum channel discovery score required before a channel is considered
# qualified for keyword-cascade subscription. Tune based on observed channel
# quality; 40/100 catches obviously weak channels while preserving the legacy
# scoring range.
MIN_DISCOVERY_SCORE = 40.0


def _score_channel(subs: int, avg_views: int, video_count: int) -> float:
    """Ported channel scoring logic from legacy discovery service."""
    if 150_000 <= avg_views <= 200_000:
        view_score = 30
    elif 100_000 <= avg_views < 150_000:
        view_score = 20
    elif 200_000 < avg_views <= 300_000:
        view_score = 15
    elif 50_000 <= avg_views < 100_000:
        view_score = 10
    else:
        view_score = 0

    if subs <= 5_000:
        sub_score = 30
    elif subs <= 15_000:
        sub_score = 24
    elif subs <= 30_000:
        sub_score = 16
    elif subs <= 50_000:
        sub_score = 8
    else:
        sub_score = 0

    if video_count >= 100:
        upload_score = 20
    elif video_count >= 50:
        upload_score = 14
    elif video_count >= 20:
        upload_score = 8
    else:
        upload_score = 2

    ratio = avg_views / subs if subs > 0 else 0
    if ratio >= 5:
        ratio_score = 20
    elif ratio >= 2:
        ratio_score = 14
    elif ratio >= 1:
        ratio_score = 8
    else:
        ratio_score = 2

    return float(view_score + sub_score + upload_score + ratio_score)


def discover_channels(keyword: str, max_results: int = 10) -> List[ChannelCandidate]:
    """Discover and score channels by keyword with YouTube Data API."""
    keyword = (keyword or "").strip()
    if not keyword:
        return []

    youtube = get_youtube_service().client
    search_resp = youtube.search().list(
        part="snippet",
        q=keyword,
        type="channel",
        maxResults=max_results,
        relevanceLanguage="en",
    ).execute()

    channel_ids = []
    for item in search_resp.get("items", []):
        snippet = item.get("snippet", {})
        channel_id = snippet.get("channelId")
        if channel_id and channel_id not in channel_ids:
            channel_ids.append(channel_id)

    if not channel_ids:
        return []

    details_resp = youtube.channels().list(
        part="snippet,statistics",
        id=",".join(channel_ids),
    ).execute()

    candidates: List[ChannelCandidate] = []
    for item in details_resp.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        subscriber_count = int(stats.get("subscriberCount", 0) or 0)
        video_count = int(stats.get("videoCount", 0) or 0)
        view_count = int(stats.get("viewCount", 0) or 0)
        avg_views = int(view_count / video_count) if video_count > 0 else 0
        discovery_score = _score_channel(subscriber_count, avg_views, video_count)

        candidates.append(
            ChannelCandidate(
                youtube_channel_id=item.get("id", ""),
                name=snippet.get("title", ""),
                description=(snippet.get("description", "") or "")[:500],
                thumbnail_url=(
                    snippet.get("thumbnails", {}).get("medium", {}).get("url", "")
                ),
                subscriber_count=subscriber_count,
                video_count=video_count,
                avg_views=avg_views,
                discovery_score=discovery_score,
            )
        )

    candidates.sort(key=lambda x: x.discovery_score, reverse=True)
    logger.info(
        "Discovered %d channels for keyword '%s'",
        len(candidates),
        keyword,
    )
    return candidates
