"""Server-side reconciliation of LLM component scores with heuristic bands."""
from __future__ import annotations

from typing import Dict

COMPONENT_MAX = 0.98
SATURATION_CAP = 0.3
SPECIFICITY_MAX_DEVIATION = 0.18
SATURATION_MAX_DEVIATION = 0.15
RELEVANCE_MAX_DEVIATION = 0.25


def _clip(score: float) -> float:
    return round(max(0.0, min(COMPONENT_MAX, score)), 3)


def calibration_blend_weights(
    linked_reports: int,
    *,
    threshold: int,
    llm_weight_uncalibrated: float,
) -> tuple[float, float]:
    """Linear ramp from heuristic blend to full LLM between 0 and threshold reports."""
    if linked_reports >= threshold:
        return 1.0, 0.0
    if threshold <= 0:
        return llm_weight_uncalibrated, round(1.0 - llm_weight_uncalibrated, 3)
    ramp = linked_reports / threshold
    llm_weight = llm_weight_uncalibrated + (1.0 - llm_weight_uncalibrated) * ramp
    llm_weight = round(llm_weight, 3)
    return llm_weight, round(1.0 - llm_weight, 3)


def validate_llm_components(
    llm_components: Dict[str, float],
    heuristic_components: Dict[str, float],
    *,
    saturation_tier: str,
) -> tuple[Dict[str, float], Dict[str, bool]]:
    """Reconcile LLM saturation/specificity with server-side heuristic bands."""
    validated = dict(llm_components)
    adjusted: Dict[str, bool] = {
        "saturation": False,
        "specificity": False,
    }

    h_sat = float(heuristic_components.get("saturation", 0.0))
    llm_sat = float(validated.get("saturation", h_sat))
    if saturation_tier == "saturated":
        cap = min(SATURATION_CAP, h_sat + 0.05)
        if llm_sat > cap:
            validated["saturation"] = _clip(cap)
            adjusted["saturation"] = True
    elif abs(llm_sat - h_sat) > SATURATION_MAX_DEVIATION:
        validated["saturation"] = _clip(0.55 * llm_sat + 0.45 * h_sat)
        adjusted["saturation"] = True

    h_spec = float(heuristic_components.get("specificity", 0.0))
    llm_spec = float(validated.get("specificity", h_spec))
    if abs(llm_spec - h_spec) > SPECIFICITY_MAX_DEVIATION:
        validated["specificity"] = _clip(0.6 * llm_spec + 0.4 * h_spec)
        adjusted["specificity"] = True

    return validated, adjusted


def reconcile_heuristic_components_for_blend(
    llm_components: Dict[str, float],
    heuristic_components: Dict[str, float],
) -> Dict[str, float]:
    """Soften over-optimistic heuristic components before beta/nurture blend."""
    reconciled = dict(heuristic_components)
    thresholds = {
        "relevance": RELEVANCE_MAX_DEVIATION,
        "specificity": SPECIFICITY_MAX_DEVIATION,
        "saturation": SATURATION_MAX_DEVIATION,
    }
    for key, max_dev in thresholds.items():
        llm = float(llm_components.get(key, 0.0))
        heur = float(heuristic_components.get(key, 0.0))
        if abs(llm - heur) > max_dev:
            reconciled[key] = _clip(0.35 * heur + 0.65 * llm)
    return reconciled
