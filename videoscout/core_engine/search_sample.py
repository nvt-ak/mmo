"""Search-sample distribution, population context, and representation quality (ADR 0014)."""
from __future__ import annotations

import math
import os
import re
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from videoscout.core_engine.nurture_scorer import _GENERIC_TOKENS, _contiguous_match, _title_tokens_ordered

RANKING_BIAS_RECENCY = "recency_ranked"


def top_n_validation_limit() -> int:
    raw = os.getenv("TOP_N_VALIDATION", "15").strip()
    try:
        return max(1, min(int(raw), 30))
    except ValueError:
        return 15


def discovery_validation_enabled() -> bool:
    raw = os.getenv("DISCOVERY_VALIDATION_ENABLED", "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _parse_published_at(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return None


def _percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * pct
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return float(ordered[lower])
    weight = rank - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


def _title_proper_noun_phrases(source_title: str) -> List[str]:
    tokens = re.findall(r"\b([A-ZÀ-Ý][a-zA-ZÀ-ÿß]{1,}|[A-ZÀ-Ý]{2,})\b", source_title or "")
    if not tokens:
        return []
    phrases: List[str] = []
    buffer: List[str] = []
    for token in tokens:
        if token[:1].isupper() and token.lower() not in _GENERIC_TOKENS:
            buffer.append(token)
        elif buffer:
            phrases.append(" ".join(buffer))
            buffer = []
    if buffer:
        phrases.append(" ".join(buffer))
    if not phrases and tokens:
        phrases.append(tokens[0])
    return phrases[:3]


def build_search_queries(keyword: str, source_title: str = "") -> List[str]:
    """Literal + de-generic + source-title entity phrases (ADR 0014)."""
    seen: set[str] = set()
    queries: List[str] = []

    def _add(query: str) -> None:
        cleaned = " ".join(query.lower().split())
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            queries.append(cleaned)

    _add(keyword.strip())

    tokens = [
        t
        for t in keyword.lower().split()
        if t not in _GENERIC_TOKENS and len(t) > 1
    ]
    if len(tokens) >= 2:
        _add(" ".join(tokens))

    for phrase in _title_proper_noun_phrases(source_title):
        lowered = phrase.lower()
        if lowered not in seen and len(lowered.split()) <= 5:
            _add(lowered)
            if len(tokens) >= 1:
                _add(f"{lowered} {' '.join(tokens[-2:])}")

    return queries[:4]


def dedupe_videos(
    video_lists: List[List[Dict[str, Any]]],
    *,
    id_key: str = "video_id",
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for videos in video_lists:
        for video in videos:
            vid = str(video.get(id_key) or video.get("id") or "").strip()
            if not vid or vid in seen:
                continue
            seen.add(vid)
            merged.append(dict(video))
    return merged


def compute_distribution_stats(
    videos: List[Dict[str, Any]],
    *,
    creator_key: str = "channel_id",
    window_days: int = 7,
) -> Dict[str, Any]:
    """View/creator distribution for a search sample (not population)."""
    if not videos:
        return {
            "sample_size": 0,
            "median_views": 0.0,
            "p75_views": 0.0,
            "p90_views": 0.0,
            "max_views": 0.0,
            "view_variance": 0.0,
            "top_video_ratio": 0.0,
            "creator_count": 0,
            "creator_diversity": 0.0,
            "uploads_per_day": 0.0,
            "viral_outlier": False,
            "top_contribution_pct": 0.0,
        }

    views = [float(v.get("view_count") or 0) for v in videos]
    total_views = sum(views)
    max_views = max(views) if views else 0.0
    median_views = _percentile(views, 0.5)
    p75_views = _percentile(views, 0.75)
    p90_views = _percentile(views, 0.90)
    view_variance = float(statistics.pvariance(views)) if len(views) > 1 else 0.0
    top_video_ratio = round(max_views / total_views, 4) if total_views > 0 else 0.0
    top_contribution_pct = round(top_video_ratio * 100.0, 2)

    creators = {
        str(v.get(creator_key) or "").strip()
        for v in videos
        if str(v.get(creator_key) or "").strip()
    }
    creator_count = len(creators)
    creator_diversity = round(creator_count / len(videos), 4) if videos else 0.0

    timestamps = [
        dt
        for dt in (_parse_published_at(v.get("published_at")) for v in videos)
        if dt is not None
    ]
    uploads_per_day = 0.0
    if timestamps:
        newest = max(timestamps)
        oldest = min(timestamps)
        span_days = max((newest - oldest).total_seconds() / 86400.0, 1.0)
        uploads_per_day = round(len(timestamps) / span_days, 4)

    viral_outlier = (
        len(views) >= 3
        and max_views > 0
        and median_views > 0
        and max_views >= 10 * median_views
        and top_video_ratio >= 0.45
    )

    return {
        "sample_size": len(videos),
        "median_views": round(median_views, 2),
        "p75_views": round(p75_views, 2),
        "p90_views": round(p90_views, 2),
        "max_views": round(max_views, 2),
        "view_variance": round(view_variance, 2),
        "top_video_ratio": top_video_ratio,
        "creator_count": creator_count,
        "creator_diversity": creator_diversity,
        "uploads_per_day": uploads_per_day,
        "viral_outlier": viral_outlier,
        "top_contribution_pct": top_contribution_pct,
    }


def build_population_context(
    *,
    query_used: str,
    sample_size: int,
    estimated_result_count: Optional[int],
    search_order: str = "date",
    time_window_days: int = 7,
    ranking_bias: str = RANKING_BIAS_RECENCY,
    newest_upload: Optional[str] = None,
    oldest_upload: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "sample_size": sample_size,
        "estimated_result_count": int(estimated_result_count or 0),
        "query_used": query_used,
        "search_order": search_order,
        "time_window_days": time_window_days,
        "ranking_bias": ranking_bias,
        "newest_upload": newest_upload,
        "oldest_upload": oldest_upload,
    }


def _query_coherence(keyword: str) -> float:
    tokens = keyword.lower().split()
    if not tokens:
        return 0.0
    generic = sum(1 for t in tokens if t in _GENERIC_TOKENS)
    return round(max(0.0, 1.0 - generic / len(tokens)), 4)


def compute_representation_quality(
    keyword: str,
    source_title: str,
    sample_titles: List[str],
) -> Dict[str, Any]:
    """Tier-4 metadata — pattern coherence in search sample titles."""
    kw_lower = keyword.lower().strip()
    ordered_source = _title_tokens_ordered(source_title)
    coherence = _query_coherence(keyword)

    if not sample_titles:
        return {
            "query_coherence": coherence,
            "pattern_purity": 0.0,
            "fragmentation": 1.0,
            "alias_density": 0.0,
            "representation_confidence": "low",
        }

    matches = 0
    for title in sample_titles:
        ordered = _title_tokens_ordered(title)
        contiguous, _, _ = _contiguous_match(kw_lower, ordered)
        if contiguous or kw_lower in " ".join(ordered):
            matches += 1

    pattern_purity = round(matches / len(sample_titles), 4)
    fragmentation = round(1.0 - pattern_purity, 4)

    unique_titles = {t.lower().strip() for t in sample_titles if t.strip()}
    alias_density = round(len(unique_titles) / len(sample_titles), 4)

    if pattern_purity >= 0.65 and coherence >= 0.6:
        confidence = "high"
    elif pattern_purity >= 0.35:
        confidence = "mixed"
    else:
        confidence = "low"

    return {
        "query_coherence": coherence,
        "pattern_purity": pattern_purity,
        "fragmentation": fragmentation,
        "alias_density": alias_density,
        "representation_confidence": confidence,
    }


def merge_search_sample_evidence(
    evidence: Dict[str, Any],
    *,
    youtube_videos: List[Dict[str, Any]],
    youtube_population_contexts: List[Dict[str, Any]],
    tiktok_videos: List[Dict[str, Any]],
    tiktok_population_context: Optional[Dict[str, Any]],
    search_queries_used: List[str],
    source_title: str,
    keyword: str,
) -> Dict[str, Any]:
    """Attach Tier 2–4 derived fields and bump schema to v2."""
    yt_stats = compute_distribution_stats(youtube_videos, creator_key="channel_id")
    tt_stats = compute_distribution_stats(tiktok_videos, creator_key="author_id")

    sample_titles = [str(v.get("title") or "") for v in youtube_videos if v.get("title")]
    representation = compute_representation_quality(keyword, source_title, sample_titles)

    derived = dict(evidence.get("derived") or {})
    derived["search_sample"] = {
        "youtube": yt_stats,
        "tiktok": tt_stats,
    }
    derived["population_context"] = {
        "youtube": youtube_population_contexts,
        "tiktok": tiktok_population_context,
    }
    derived["representation_quality"] = representation

    metadata = dict(evidence.get("metadata") or {})
    metadata["search_queries_used"] = search_queries_used
    metadata["enrichment_tier"] = max(int(metadata.get("enrichment_tier") or 0), 2)

    merged = dict(evidence)
    merged["schema_version"] = "2"
    merged["derived"] = derived
    merged["metadata"] = metadata
    return merged
