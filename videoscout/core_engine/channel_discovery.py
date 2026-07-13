"""Keyword-based YouTube channel discovery and scoring."""
from dataclasses import dataclass
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from videoscout.core_engine.nurture_scorer import (
    _GENERIC_TOKENS,
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

# Decision-tree thresholds for ``evaluate_channel_relevance`` (US-076).
# ``MIN_PER_VIDEO_OVERLAP`` doubles as the per-video bar for a "match".
METADATA_PASS_THRESHOLD = 0.5
METADATA_ZERO_MATCH_THRESHOLD = 0.25
MIN_PER_VIDEO_OVERLAP = 0.5
CATALOG_PATTERN_MIN_SHARE = 0.6
CATALOG_MIN_NON_MATCHING = 3


def _channel_content_tokens(text: str) -> set[str]:
    """Normalize and tokenize channel content text, stripping generic terms."""
    cleaned = re.sub(r"[^\w\s-]", " ", (text or "").lower())
    return {
        t
        for t in cleaned.split()
        if len(t) > 1 and t not in _GENERIC_TOKENS
    }


def _distinctive_keyword_tokens(keyword: str) -> set[str]:
    """Return keyword tokens that are not generic stopwords."""
    return _channel_content_tokens((keyword or "").lower().strip())


def _per_video_overlaps(
    kw_tokens: set[str],
    videos: List[Dict[str, Any]],
) -> List[float]:
    """Return token-overlap score for each video against distinctive kw tokens."""
    if not kw_tokens:
        return [0.0] * len(videos)
    overlaps: List[float] = []
    for video in videos:
        title = str(video.get("title") or "")
        description = str(video.get("description") or "")
        text_tokens = _channel_content_tokens(f"{title} {description}".strip())
        if not text_tokens:
            overlaps.append(0.0)
            continue
        overlap = len(kw_tokens & text_tokens) / len(kw_tokens)
        overlaps.append(round(overlap, 3))
    return overlaps


def _metadata_score(
    kw_tokens: set[str],
    channel_name: str,
    channel_description: str,
) -> float:
    """Raw token overlap between distinctive keyword tokens and channel metadata."""
    if not kw_tokens:
        return 0.0
    metadata_tokens = _channel_content_tokens(
        f"{channel_name} {channel_description}".strip()
    )
    if not metadata_tokens:
        return 0.0
    return round(len(kw_tokens & metadata_tokens) / len(kw_tokens), 3)


def _contains_ngram(tokens: List[str], ngram: Tuple[str, ...]) -> bool:
    n = len(ngram)
    if n == 0 or len(tokens) < n:
        return False
    for i in range(len(tokens) - n + 1):
        if tuple(tokens[i : i + n]) == ngram:
            return True
    return False


def _extract_absent_dominant_pattern(
    non_matching_titles: List[str],
    matching_title: str,
    min_share: float,
    min_non_matching: int,
) -> Optional[str]:
    """
    Find a catalog pattern shared by ``min_share`` of non-matching videos that
    the matching video lacks. Returns the pattern as a space-joined string, or
    ``None`` if no such pattern exists (the matching video fits the catalog).
    """
    if len(non_matching_titles) < min_non_matching:
        return None

    counts: Dict[Tuple[str, ...], int] = {}
    for title in non_matching_titles:
        tokens = _title_tokens_ordered(title)
        seen: set[Tuple[str, ...]] = set()
        for n in (3, 2):
            for i in range(len(tokens) - n + 1):
                ngram = tuple(tokens[i : i + n])
                if ngram not in seen:
                    counts[ngram] = counts.get(ngram, 0) + 1
                    seen.add(ngram)

    if not counts:
        return None

    threshold = max(1, math.ceil(min_share * len(non_matching_titles)))
    candidates = [(ngram, count) for ngram, count in counts.items() if count >= threshold]
    if not candidates:
        return None

    # Deterministic tie-breaking: frequency, then length, then lexical order.
    candidates.sort(key=lambda item: (-item[1], -len(item[0]), item[0]))
    matching_tokens = _title_tokens_ordered(matching_title)
    for ngram, _count in candidates:
        if not _contains_ngram(matching_tokens, ngram):
            return " ".join(ngram)
    return None


def evaluate_channel_relevance(
    keyword: str,
    *,
    channel_name: str,
    channel_description: str,
    videos: List[Dict[str, Any]],
) -> Tuple[bool, float, str, Dict[str, Any]]:
    """
    Decide whether a channel should be subscribed for a keyword.

    Returns ``(pass, score, reason, signals)``. ``reason`` is one of the
    explicit branch labels required by US-076:
    ``metadata_pass``, ``multi_video``, ``catalog_coherent_single``,
    ``catalog_outlier_single``, ``rejected``.
    """
    kw_tokens = _distinctive_keyword_tokens(keyword)
    if not kw_tokens:
        signals = {
            "video_best": 0.0,
            "match_count": 0,
            "match_rate": 0.0,
            "metadata_score": 0.0,
            "catalog_dominant_pattern": None,
            "decision_branch": "rejected",
        }
        return False, 0.0, "rejected", signals

    overlaps = _per_video_overlaps(kw_tokens, videos)
    match_count = sum(1 for o in overlaps if o >= MIN_PER_VIDEO_OVERLAP)
    video_best = max(overlaps) if overlaps else 0.0
    match_rate = round(match_count / len(videos), 3) if videos else 0.0
    metadata_score = _metadata_score(kw_tokens, channel_name, channel_description)

    # 1. Metadata pass — catches official/artist channels whose recent uploads
    #    omit the trend tokens. A lower bar is used when no recent video is a
    #    strong match, which is exactly the Cargo - Topic failure mode.
    metadata_threshold = (
        METADATA_ZERO_MATCH_THRESHOLD
        if videos and match_count == 0
        else METADATA_PASS_THRESHOLD
    )
    if metadata_score >= metadata_threshold:
        signals = {
            "video_best": video_best,
            "match_count": match_count,
            "match_rate": match_rate,
            "metadata_score": metadata_score,
            "catalog_dominant_pattern": None,
            "decision_branch": "metadata_pass",
        }
        return True, max(video_best, metadata_score), "metadata_pass", signals

    if not videos:
        signals = {
            "video_best": 0.0,
            "match_count": 0,
            "match_rate": 0.0,
            "metadata_score": metadata_score,
            "catalog_dominant_pattern": None,
            "decision_branch": "rejected",
        }
        return False, 0.0, "rejected", signals

    # 2. Multiple strong video matches.
    if match_count >= 2:
        signals = {
            "video_best": video_best,
            "match_count": match_count,
            "match_rate": match_rate,
            "metadata_score": metadata_score,
            "catalog_dominant_pattern": None,
            "decision_branch": "multi_video",
        }
        return True, video_best, "multi_video", signals

    # 3. Single strong video match — use catalog coherence to separate a true
    #    themed channel (Mikado singt) from a one-off outlier (Hans Schmitz).
    if match_count == 1:
        match_index = next(
            i for i, o in enumerate(overlaps) if o >= MIN_PER_VIDEO_OVERLAP
        )
        matching_video = videos[match_index]
        matching_title = str(matching_video.get("title") or "")
        non_matching = [
            v for i, v in enumerate(videos) if i != match_index
        ]
        non_matching_titles = [
            str(v.get("title") or "") for v in non_matching
        ]

        absent_pattern = _extract_absent_dominant_pattern(
            non_matching_titles,
            matching_title,
            CATALOG_PATTERN_MIN_SHARE,
            CATALOG_MIN_NON_MATCHING,
        )

        if absent_pattern is None:
            branch = "catalog_coherent_single"
            passed = True
        else:
            # Metadata can rescue a single match if it supports the keyword and
            # the dominant catalog pattern is keyword-related.
            pattern_tokens = set(absent_pattern.split())
            metadata_rescue = (
                metadata_score >= METADATA_PASS_THRESHOLD
                and bool(pattern_tokens & kw_tokens)
            )
            if metadata_rescue:
                branch = "catalog_coherent_single"
                passed = True
            else:
                branch = "catalog_outlier_single"
                passed = False

        signals = {
            "video_best": video_best,
            "match_count": match_count,
            "match_rate": match_rate,
            "metadata_score": metadata_score,
            "catalog_dominant_pattern": absent_pattern,
            "decision_branch": branch,
        }
        return passed, video_best, branch, signals

    # 4. No strong video match and metadata did not rescue.
    signals = {
        "video_best": video_best,
        "match_count": match_count,
        "match_rate": match_rate,
        "metadata_score": metadata_score,
        "catalog_dominant_pattern": None,
        "decision_branch": "rejected",
    }
    return False, video_best, "rejected", signals


def compute_channel_keyword_relevance(
    keyword: str,
    videos: List[Dict[str, Any]],
) -> Tuple[float, str]:
    """
    Backwards-compatible wrapper for US-075 callers.

    Uses ``evaluate_channel_relevance`` with empty metadata, so channels that
    would only pass via metadata are scored on video evidence alone.
    """
    passed, score, reason, _signals = evaluate_channel_relevance(
        keyword,
        channel_name="",
        channel_description="",
        videos=videos,
    )
    # Preserve the old ``(score, reason)`` shape for any legacy callers.
    return score, reason


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
