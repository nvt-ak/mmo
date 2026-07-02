"""Trend-first keyword discovery — extract, classify, gate."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from videoscout.core_engine.keyword_classifier import classify_keyword_type

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "must", "shall", "can", "need", "dare", "ought", "used",
    "i", "you", "he", "she", "it", "we", "they", "what", "which", "who",
    "when", "where", "why", "how", "all", "each", "every", "both", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "don", "now", "new", "official",
    "video", "full", "hd", "4k", "ft", "feat", "vs", "ep", "part", "trailer",
    "reaction", "live", "stream", "shorts",
}


def extract_keyword_candidates(
    title: str,
    *,
    discovery_source: str = "youtube_trend",
    max_phrases: int = 3,
) -> List[Dict[str, Any]]:
    """Extract 2–5 word keyword phrases from a trending title."""
    cleaned = re.sub(r"[^\w\s-]", " ", title.lower())
    tokens = [t for t in cleaned.split() if t and t not in STOPWORDS and len(t) > 1]
    if len(tokens) < 2:
        return []

    phrases: List[str] = []
    for width in (4, 5, 3, 2):
        for i in range(len(tokens) - width + 1):
            phrase = " ".join(tokens[i : i + width])
            if phrase not in phrases:
                phrases.append(phrase)
            if len(phrases) >= max_phrases:
                break
        if len(phrases) >= max_phrases:
            break

    return [
        {
            "keyword": phrase,
            "discovery_source": discovery_source,
            "trend_signals": {
                "source_title": title[:120],
                "detected_at": datetime.utcnow().isoformat(),
            },
        }
        for phrase in phrases[:max_phrases]
    ]


def build_scored_candidate(
    candidate: Dict[str, Any],
    *,
    tiktok_gate: Dict[str, Any],
    keyword_type_filter: str = "both",
) -> Optional[Dict[str, Any]]:
    """Score, classify, and apply gate profile. Returns None if blocked."""
    keyword = candidate["keyword"]
    discovery_source = candidate.get("discovery_source", "youtube_trend")
    tiktok_stats = tiktok_gate.get("tiktok_stats") or {}
    saturation_tier = tiktok_stats.get("saturation_tier", "moderate")

    specificity = min(1.0, len(keyword.split()) / 5.0)
    saturation_score = tiktok_gate.get("score", 0.5)
    final_score = round(0.5 * specificity + 0.5 * saturation_score, 3)

    keyword_type = classify_keyword_type(
        keyword,
        trend_source=discovery_source,
        saturation_tier=saturation_tier,
        agent_score=final_score,
    )

    if keyword_type_filter in ("nurture", "beta") and keyword_type != keyword_type_filter:
        return None

    gate_profile = "light" if keyword_type == "nurture" else "full"
    if not tiktok_gate.get("surface", True):
        return None

    min_score = 0.25 if keyword_type == "nurture" else 0.40
    if final_score < min_score:
        return None

    tier_to_status = {"fresh": "low", "moderate": "moderate", "saturated": "saturated"}
    return {
        "keyword": keyword,
        "keyword_type": keyword_type,
        "discovery_source": discovery_source,
        "trend_signals": candidate.get("trend_signals"),
        "gate_profile": gate_profile,
        "final_score": final_score,
        "component_scores": {
            "relevance": 0.5,
            "specificity": round(specificity, 3),
            "saturation": round(saturation_score, 3),
            "trend": 0.7,
            "video_performance": 0.5,
        },
        "tiktok_status": tier_to_status.get(saturation_tier, "moderate"),
        "tiktok_count": tiktok_stats.get("video_count_7d", 0),
        "tiktok_stats": tiktok_stats,
        "tiktok_unverified": bool(tiktok_gate.get("tiktok_unverified", False)),
    }
