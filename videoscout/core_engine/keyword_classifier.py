"""Nurture vs beta keyword classification — spec §6.2 heuristics (v1, tunable)."""
from __future__ import annotations

from typing import Literal

KeywordType = Literal["nurture", "beta"]
TrendSource = Literal["youtube_trend", "youtube_velocity", "social", "niche_web", "manual"]
SaturationTier = Literal["fresh", "moderate", "saturated"]

NURTURE_MIN_SCORE = 0.25
BETA_MIN_SCORE = 0.40


def _phrase_word_count(keyword: str) -> int:
    return len(keyword.strip().split())


def classify_keyword_type(
    keyword: str,
    *,
    trend_source: str = "youtube_trend",
    saturation_tier: str | None = None,
    agent_score: float | None = None,
) -> KeywordType:
    """
    Classify keyword as nurture or beta using v1 heuristics.

    Nurture: 2–3 words, broad trend sources, moderate–saturated OK.
    Beta: 3–5 words, niche/low competition, prefer fresh–moderate saturation.
    """
    words = _phrase_word_count(keyword)
    source = trend_source or "youtube_trend"
    sat = saturation_tier or "moderate"

    nurture_score = 0
    beta_score = 0

    # Phrase length
    if words <= 3:
        nurture_score += 2
    elif words >= 4:
        beta_score += 2
    if words == 4:
        beta_score += 1  # sweet spot for long-tail

    # Trend source
    if source in ("youtube_trend", "social"):
        nurture_score += 2
    elif source == "youtube_velocity":
        beta_score += 1
        nurture_score += 1
    elif source == "niche_web":
        beta_score += 2
    elif source == "manual":
        nurture_score += 1
        beta_score += 1

    # Saturation
    if sat in ("moderate", "saturated"):
        nurture_score += 1
    if sat == "saturated" and words <= 3:
        nurture_score += 1
    if sat == "fresh":
        beta_score += 2
    elif sat == "moderate" and words >= 4:
        beta_score += 1

    # Agent score thresholds (when available)
    if agent_score is not None:
        if agent_score >= BETA_MIN_SCORE:
            beta_score += 2
        elif agent_score >= NURTURE_MIN_SCORE:
            nurture_score += 1
        else:
            nurture_score += 1  # low score broad terms → nurture bias

    return "beta" if beta_score > nurture_score else "nurture"
