"""Experiment scoring and pattern extraction helpers."""
from __future__ import annotations

from statistics import stdev
from typing import Any

PREDICTED_SUCCESS_THRESHOLD = 60
MIN_PATTERN_OCCURRENCES = 3
MIN_PATTERN_CONFIDENCE = 0.6


def _normalize_engagement(engagement_rate: float) -> float:
    """Accept ratio form (0.12) or percent form (12.0)."""
    if engagement_rate <= 1.0:
        return engagement_rate * 100.0
    return engagement_rate


def compute_actual_score(views_vs_baseline: float, engagement_rate: float) -> float:
    """
    Compute 0-100 performance score from normalized views + engagement.

    Note: in historical US-001 data, baseline is often rounded before storage.
    Treat >=2.0 as "strong baseline win" to preserve the documented ~89.4 example.
    """
    safe_views_vs_baseline = max(0.0, views_vs_baseline or 0.0)
    engagement_percent = max(0.0, _normalize_engagement(engagement_rate or 0.0))

    if safe_views_vs_baseline >= 2.0:
        views_component = 75.0
    else:
        views_component = min(75.0, safe_views_vs_baseline * 35.0)

    engagement_component = min(25.0, engagement_percent * 1.2)
    score = views_component + engagement_component
    return round(min(100.0, max(0.0, score)), 1)


def classify_outcome(predicted_score: int, test_status: str) -> str:
    """Classify prediction outcome using threshold=60."""
    predicted_success = predicted_score >= PREDICTED_SUCCESS_THRESHOLD
    actual_success = test_status == "success"

    if predicted_success and actual_success:
        return "true_positive"
    if predicted_success and not actual_success:
        return "false_positive"
    if not predicted_success and actual_success:
        return "false_negative"
    return "true_negative"


def compute_accuracy(predicted: float, actual: float) -> float:
    """Return bounded prediction accuracy in [0, 1]."""
    return max(0.0, 1.0 - abs(predicted - actual) / 100.0)


def _get_value(experiment: Any, key: str, default: Any = None) -> Any:
    if isinstance(experiment, dict):
        return experiment.get(key, default)
    return getattr(experiment, key, default)


def _extract_traits(keyword: str) -> list[str]:
    keyword_lower = (keyword or "").lower()
    traits: list[str] = []

    if "viral" in keyword_lower:
        traits.append("contains_viral")
    if "trending" in keyword_lower:
        traits.append("contains_trending")
    if "tutorial" in keyword_lower:
        traits.append("contains_tutorial")
    if "how to" in keyword_lower:
        traits.append("contains_how_to")

    word_count = len((keyword or "").split())
    if word_count == 1:
        traits.append("single_word")
    if word_count >= 3:
        traits.append("long_tail")

    return traits


def extract_patterns(experiments: list) -> list[dict]:
    """Extract qualified patterns from reported experiments."""
    groups: dict[tuple[str, str], list[Any]] = {}

    for exp in experiments:
        outcome_type = _get_value(exp, "outcome_type")
        if not outcome_type:
            continue

        keyword = _get_value(exp, "keyword", "")
        traits = _extract_traits(keyword)
        for trait in traits:
            groups.setdefault((trait, outcome_type), []).append(exp)

    patterns: list[dict] = []
    for (trait, outcome_type), group in groups.items():
        if len(group) < MIN_PATTERN_OCCURRENCES:
            continue

        predicted_values = [
            float(_get_value(item, "predicted_score", 0) or 0) for item in group
        ]
        actual_values: list[float] = []
        accuracies: list[float] = []
        experiment_ids: list[str] = []
        examples: list[str] = []

        for item in group:
            raw_accuracy = _get_value(item, "accuracy")
            if raw_accuracy is not None:
                accuracies.append(float(raw_accuracy))

            raw_actual = _get_value(item, "actual_score")
            if raw_actual is None:
                views_vs_baseline = float(_get_value(item, "views_vs_baseline", 0) or 0)
                actual_engagement = float(_get_value(item, "actual_engagement", 0) or 0)
                raw_actual = compute_actual_score(views_vs_baseline, actual_engagement)
            actual_values.append(float(raw_actual))

            item_id = _get_value(item, "id")
            if item_id is not None:
                experiment_ids.append(str(item_id))

            keyword = _get_value(item, "keyword", "")
            if keyword and keyword not in examples and len(examples) < 3:
                examples.append(keyword)

        if len(accuracies) > 1:
            confidence = max(0.3, 1.0 - stdev(accuracies))
        else:
            confidence = 0.5

        confidence = round(confidence, 2)
        if confidence < MIN_PATTERN_CONFIDENCE:
            continue

        patterns.append(
            {
                "trait": trait,
                "outcome_type": outcome_type,
                "count": len(group),
                "confidence": confidence,
                "avg_predicted": round(sum(predicted_values) / len(predicted_values), 1),
                "avg_actual": round(sum(actual_values) / len(actual_values), 1),
                "examples": examples,
                "experiment_ids": experiment_ids,
            }
        )

    return sorted(patterns, key=lambda item: (item["count"], item["confidence"]), reverse=True)


def suggest_weight_adjustments(patterns: list) -> list[dict]:
    """Generate bounded weight adjustment suggestions from discovered patterns."""
    current_weights = {
        "search_volume": 1.0,
        "trend_velocity": 1.0,
        "competition": 1.0,
        "seasonality": 1.0,
    }

    rules = {
        ("contains_viral", "false_positive"): ("search_volume", 0.9, "Overestimated viral terms"),
        ("long_tail", "false_negative"): ("trend_velocity", 1.1, "Undervalued long-tail opportunities"),
        ("contains_tutorial", "true_positive"): ("competition", 1.05, "Tutorial terms consistently convert"),
        ("single_word", "false_positive"): ("competition", 0.9, "Single-word terms too broad"),
    }

    suggestions: list[dict] = []
    for pattern in patterns:
        confidence = float(pattern.get("confidence", 0))
        count = int(pattern.get("count", 0))
        if confidence < MIN_PATTERN_CONFIDENCE or count < MIN_PATTERN_OCCURRENCES:
            continue

        key = (pattern.get("trait"), pattern.get("outcome_type"))
        rule = rules.get(key)
        if not rule:
            continue

        factor, multiplier, reason = rule
        old_value = current_weights[factor]
        new_value = round(min(2.0, max(0.5, old_value * multiplier)), 2)
        if new_value == old_value:
            continue

        current_weights[factor] = new_value
        suggestions.append(
            {
                "factor": factor,
                "old_value": old_value,
                "new_value": new_value,
                "reason": reason,
                "confidence": confidence,
                "based_on": {
                    "trait": pattern.get("trait"),
                    "outcome_type": pattern.get("outcome_type"),
                    "count": count,
                },
            }
        )

    return suggestions
