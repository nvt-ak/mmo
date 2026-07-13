"""Keyword-based YouTube channel discovery and scoring."""
from dataclasses import dataclass
import logging
import re
from typing import Any, Dict, List, Tuple

from videoscout.core_engine.nurture_scorer import (
    _GENERIC_TOKENS,
    _contiguous_match,
    _title_tokens_ordered,
)
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

# Minimum keyword-to-channel-content relevance required before subscribing a
# channel. Computed from recent video titles/descriptions. 0.5 means at least
# half the keyword tokens (or an exact phrase) appear in recent content.
MIN_CHANNEL_RELEVANCE_THRESHOLD = 0.5


def _channel_content_tokens(text: str) -> set[str]:
    """Normalize and tokenize channel content text, stripping generic terms."""
    cleaned = re.sub(r"[^\w\s-]", " ", (text or "").lower())
    return {
        t
        for t in cleaned.split()
        if len(t) > 1 and t not in _GENERIC_TOKENS
    }


def compute_channel_keyword_relevance(
    keyword: str,
    videos: List[Dict[str, Any]],
) -> Tuple[float, str]:
    """
    Score how well a keyword matches a channel's recent video content.

    Returns (score, reason) where score is 0.0-1.0.
    """
    kw_lower = (keyword or "").lower().strip()
    kw_tokens = _channel_content_tokens(kw_lower)
    if not kw_tokens:
        return 0.0, "Keyword contains only generic tokens."

    if not videos:
        return 0.0, "No recent videos to evaluate relevance."

    best_score = 0.0
    best_reason = "No meaningful overlap with recent videos."

    for video in videos:
        title = str(video.get("title") or "")
        description = str(video.get("description") or "")
        content_text = f"{title} {description}".strip()
        ordered = _title_tokens_ordered(content_text)

        contiguous, _, _ = _contiguous_match(kw_lower, ordered)
        if contiguous:
            return 1.0, "Exact keyword phrase found in recent video title/description."

        text_tokens = _channel_content_tokens(content_text)
        if text_tokens:
            overlap = len(kw_tokens & text_tokens) / len(kw_tokens)
            if overlap > best_score:
                best_score = overlap
                matched = ", ".join(sorted(kw_tokens & text_tokens))
                best_reason = f"Token overlap {overlap:.0%} ({matched}) with recent video."

    return round(best_score, 3), best_reason


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
