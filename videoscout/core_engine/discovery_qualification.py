"""Qualification gates before persisting discovery keywords to inbox."""
from __future__ import annotations

from typing import Any, Dict

from videoscout.core_engine.nurture_scorer import NURTURE_MIN_SCORE

BETA_MIN_RELEVANCE = 0.30
DEFAULT_MIN_SCORE_THRESHOLD = 0.55


def qualifies_for_inbox(
    scored: Dict[str, Any],
    *,
    min_score_threshold: float,
    min_specificity: float,
    min_saturation: float = 0.0,
) -> bool:
    """Return True when a ranked row should be saved to the operator inbox."""
    keyword_type = scored.get("keyword_type") or "beta"
    final_score = float(scored.get("final_score") or 0.0)
    components = scored.get("component_scores") or {}

    floor = float(min_score_threshold) if keyword_type == "beta" else NURTURE_MIN_SCORE
    if final_score < floor:
        return False

    if keyword_type != "beta":
        return True

    specificity = float(components.get("specificity") or 0.0)
    saturation = float(components.get("saturation") or 0.0)
    relevance = float(components.get("relevance") or 0.0)

    if specificity < float(min_specificity):
        return False
    if saturation < float(min_saturation):
        return False
    if relevance < BETA_MIN_RELEVANCE:
        return False
    return True
