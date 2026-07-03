"""Trend-first keyword discovery — extract, classify, gate."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from videoscout.core_engine.keyword_classifier import classify_keyword_type
from videoscout.core_engine.keyword_scorer import get_scoring_weights
from videoscout.core_engine.nurture_scorer import score_nurture_heuristic

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
    max_word_width: int = 5,
) -> List[Dict[str, Any]]:
    """Extract 2–5 word keyword phrases from a trending title."""
    cleaned = re.sub(r"[^\w\s-]", " ", title.lower())
    tokens = [t for t in cleaned.split() if t and t not in STOPWORDS and len(t) > 1]
    if len(tokens) < 2:
        return []

    widths = [w for w in (4, 5, 3, 2) if 2 <= w <= max_word_width]
    if not widths:
        widths = [2]

    phrases: List[str] = []
    for width in widths:
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
    """Score nurture candidate with multi-signal heuristic (LLM batch in worker)."""
    return score_nurture_heuristic(
        candidate,
        tiktok_gate=tiktok_gate,
        weights=get_scoring_weights(None),
        keyword_type_filter=keyword_type_filter,
    )
