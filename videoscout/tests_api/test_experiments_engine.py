"""Unit tests for experiment scoring and pattern engine."""
import pytest
from videoscout.core_engine.experiments import (
    classify_outcome,
    compute_accuracy,
    compute_actual_score,
    extract_patterns,
    suggest_weight_adjustments,
)


def test_compute_actual_score_doc_example():
    # Locked US-001 example in Task 3 brief.
    score = compute_actual_score(views_vs_baseline=2.0, engagement_rate=12.0)
    assert 89.0 <= score <= 90.0


def test_compute_actual_score_accepts_ratio_engagement():
    percent_score = compute_actual_score(views_vs_baseline=1.2, engagement_rate=12.0)
    ratio_score = compute_actual_score(views_vs_baseline=1.2, engagement_rate=0.12)
    assert percent_score == ratio_score


def test_classify_outcome_threshold_60():
    assert classify_outcome(60, "success") == "true_positive"
    assert classify_outcome(59, "success") == "false_negative"
    assert classify_outcome(60, "failed") == "false_positive"
    assert classify_outcome(59, "failed") == "true_negative"


def test_compute_accuracy_formula():
    assert compute_accuracy(72.0, 89.4) == 0.826
    assert compute_accuracy(90.0, 10.0) == pytest.approx(0.2)


def test_extract_patterns_applies_minimums():
    experiments = [
        {
            "id": "e1",
            "keyword": "viral dance move",
            "predicted_score": 85,
            "outcome_type": "false_positive",
            "views_vs_baseline": 0.4,
            "actual_engagement": 4.0,
            "accuracy": 0.82,
        },
        {
            "id": "e2",
            "keyword": "viral shorts challenge",
            "predicted_score": 82,
            "outcome_type": "false_positive",
            "views_vs_baseline": 0.5,
            "actual_engagement": 5.0,
            "accuracy": 0.84,
        },
        {
            "id": "e3",
            "keyword": "viral dance trend",
            "predicted_score": 80,
            "outcome_type": "false_positive",
            "views_vs_baseline": 0.45,
            "actual_engagement": 4.5,
            "accuracy": 0.83,
        },
    ]

    patterns = extract_patterns(experiments)
    assert len(patterns) >= 1
    viral_pattern = next(p for p in patterns if p["trait"] == "contains_viral")
    assert viral_pattern["count"] == 3
    assert viral_pattern["confidence"] >= 0.6


def test_suggest_weight_adjustments_caps_range():
    suggestions = suggest_weight_adjustments(
        [
            {
                "trait": "contains_viral",
                "outcome_type": "false_positive",
                "count": 4,
                "confidence": 0.81,
            }
        ]
    )
    assert len(suggestions) == 1
    first = suggestions[0]
    assert first["factor"] == "search_volume"
    assert 0.5 <= first["new_value"] <= 2.0
