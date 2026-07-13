"""Nurture vs beta keyword classification — v1 heuristics + optional v2 calibration."""
from __future__ import annotations

from typing import Literal, Optional, Tuple

from videoscout.core_engine.classifier_calibration import (
    ClassifierCalibration,
    apply_classifier_calibration,
)

KeywordType = Literal["nurture", "beta"]
TrendSource = Literal["youtube_trend", "youtube_velocity", "social", "niche_web", "manual"]
SaturationTier = Literal["fresh", "moderate", "saturated"]

NURTURE_MIN_SCORE = 0.25
BETA_MIN_SCORE = 0.40


def _phrase_word_count(keyword: str) -> int:
    return len(keyword.strip().split())


def score_keyword_type(
    keyword: str,
    *,
    trend_source: str = "youtube_trend",
    saturation_tier: str | None = None,
    agent_score: float | None = None,
) -> Tuple[int, int]:
    """Return nurture and beta heuristic scores (v1 rules)."""
    words = _phrase_word_count(keyword)
    source = trend_source or "youtube_trend"
    sat = saturation_tier or "moderate"

    nurture_score = 0
    beta_score = 0

    if words <= 3:
        nurture_score += 2
    elif words >= 4:
        beta_score += 2
    if words == 4:
        beta_score += 1

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

    if sat in ("moderate", "saturated"):
        nurture_score += 1
    if sat == "saturated" and words <= 3:
        nurture_score += 1
    if sat == "fresh":
        beta_score += 2
    elif sat == "moderate" and words >= 4:
        beta_score += 1

    if agent_score is not None:
        if agent_score >= BETA_MIN_SCORE:
            beta_score += 2
        elif agent_score >= NURTURE_MIN_SCORE:
            nurture_score += 1
        else:
            nurture_score += 1

    return nurture_score, beta_score


def classify_keyword_type(
    keyword: str,
    *,
    trend_source: str = "youtube_trend",
    saturation_tier: str | None = None,
    agent_score: float | None = None,
    calibration: Optional[ClassifierCalibration] = None,
) -> KeywordType:
    """
    Classify keyword as nurture or beta.

    v1: §6.2 heuristics. v2 overlay: optional bucket success rates from
    performance reports when calibration is active.
    """
    nurture_score, beta_score = score_keyword_type(
        keyword,
        trend_source=trend_source,
        saturation_tier=saturation_tier,
        agent_score=agent_score,
    )
    nurture_score, beta_score, _reason = apply_classifier_calibration(
        nurture_score,
        beta_score,
        word_count=_phrase_word_count(keyword),
        trend_source=trend_source,
        saturation_tier=saturation_tier,
        calibration=calibration,
    )
    return "beta" if beta_score > nurture_score else "nurture"
