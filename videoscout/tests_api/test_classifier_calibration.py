"""Tests for classifier v2 performance calibration (US-072)."""
import uuid
from datetime import datetime

import pytest

from videoscout.core_engine.classifier_calibration import (
    CLASSIFIER_CALIBRATION_MIN_REPORTS,
    ClassifierCalibration,
    apply_classifier_calibration,
    build_classifier_calibration,
    feature_bucket_key,
)
from videoscout.core_engine.keyword_classifier import classify_keyword_type, score_keyword_type
from videoscout.db.models import PerformanceReportModel, SuggestionModel


def _suggestion(
    *,
    keyword: str,
    keyword_type: str,
    discovery_source: str = "youtube_trend",
    saturation_tier: str = "moderate",
):
    return SuggestionModel(
        keyword=keyword,
        final_score=0.7,
        component_scores={
            "relevance": 0.7,
            "specificity": 0.7,
            "saturation": 0.7,
            "trend": 0.5,
            "video_performance": 0.5,
        },
        suggested_by=[],
        status="reported",
        keyword_type=keyword_type,
        discovery_source=discovery_source,
        tiktok_stats={"saturation_tier": saturation_tier},
        tiktok_status="moderate",
    )


def _report(suggestion: SuggestionModel, outcome: str):
    return PerformanceReportModel(
        keyword=suggestion.keyword,
        suggestion_id=suggestion.id,
        actual_views=10_000,
        outcome=outcome,
        reported_at=datetime.utcnow(),
    )


def _seed_bucket_reports(db_session, *, keyword_type: str, outcome: str, count: int):
    for idx in range(count):
        suggestion = _suggestion(
            keyword=f"short broad moderate {keyword_type} {idx} {uuid.uuid4().hex[:4]}",
            keyword_type=keyword_type,
            discovery_source="youtube_trend",
            saturation_tier="moderate",
        )
        db_session.add(suggestion)
        db_session.flush()
        db_session.add(_report(suggestion, outcome))
    db_session.commit()


def test_feature_bucket_key_groups_features():
    assert feature_bucket_key(
        word_count=3,
        trend_source="youtube_trend",
        saturation_tier="moderate",
    ) == "short|broad|moderate"


def test_v1_unchanged_without_calibration():
    assert classify_keyword_type("new song", trend_source="youtube_trend") == "nurture"


def test_calibration_inactive_below_threshold(db_session):
    _seed_bucket_reports(db_session, keyword_type="beta", outcome="success", count=5)
    calibration = build_classifier_calibration(db_session)
    assert not calibration.is_active
    assert (
        classify_keyword_type(
            "short broad moderate",
            trend_source="youtube_trend",
            saturation_tier="moderate",
            calibration=calibration,
        )
        == classify_keyword_type(
            "short broad moderate",
            trend_source="youtube_trend",
            saturation_tier="moderate",
        )
    )


def test_calibration_boosts_track_with_higher_bucket_success(db_session):
    key = feature_bucket_key(
        word_count=3,
        trend_source="youtube_trend",
        saturation_tier="moderate",
    )
    for idx in range(5):
        suggestion = _suggestion(
            keyword=f"beta win {idx}",
            keyword_type="beta",
        )
        db_session.add(suggestion)
        db_session.flush()
        db_session.add(_report(suggestion, "success"))
    for idx in range(5):
        suggestion = _suggestion(
            keyword=f"nurture lose {idx}",
            keyword_type="nurture",
        )
        db_session.add(suggestion)
        db_session.flush()
        db_session.add(_report(suggestion, "failure"))
    for idx in range(CLASSIFIER_CALIBRATION_MIN_REPORTS - 10):
        filler = _suggestion(
            keyword=f"filler report {idx} {uuid.uuid4().hex[:4]}",
            keyword_type="beta",
            discovery_source="niche_web",
            saturation_tier="fresh",
        )
        db_session.add(filler)
        db_session.flush()
        db_session.add(_report(filler, "neutral"))
    db_session.commit()

    calibration = build_classifier_calibration(db_session)
    assert calibration.is_active
    assert key in calibration.buckets

    nurture_score, beta_score = score_keyword_type(
        "beta win test",
        trend_source="youtube_trend",
        saturation_tier="moderate",
    )
    adjusted_nurture, adjusted_beta, reason = apply_classifier_calibration(
        nurture_score,
        beta_score,
        word_count=3,
        trend_source="youtube_trend",
        saturation_tier="moderate",
        calibration=calibration,
    )
    assert adjusted_beta > beta_score
    assert reason is not None


def test_calibration_flips_tied_v1_scores():
    calibration = ClassifierCalibration(
        report_count=CLASSIFIER_CALIBRATION_MIN_REPORTS,
        buckets={
            "short|broad|moderate": {
                "beta": {"weighted_success": 5.0, "count": 5.0},
                "nurture": {"weighted_success": 0.0, "count": 5.0},
            }
        },
    )
    nurture_score, beta_score = 3, 3
    adjusted_nurture, adjusted_beta, reason = apply_classifier_calibration(
        nurture_score,
        beta_score,
        word_count=3,
        trend_source="youtube_trend",
        saturation_tier="moderate",
        calibration=calibration,
    )
    assert adjusted_beta == beta_score + 1
    assert adjusted_beta > adjusted_nurture
    assert reason is not None
    assert (
        "beta"
        if adjusted_beta > adjusted_nurture
        else "nurture"
    ) == "beta"


def test_apply_calibration_noop_when_bucket_sparse():
    calibration = ClassifierCalibration(
        report_count=CLASSIFIER_CALIBRATION_MIN_REPORTS,
        buckets={
            "short|broad|moderate": {
                "beta": {"weighted_success": 3.0, "count": 3.0},
                "nurture": {"weighted_success": 0.0, "count": 1.0},
            }
        },
    )
    nurture_score, beta_score = 4, 2
    adjusted = apply_classifier_calibration(
        nurture_score,
        beta_score,
        word_count=3,
        trend_source="youtube_trend",
        saturation_tier="moderate",
        calibration=calibration,
    )
    assert adjusted[:2] == (nurture_score, beta_score)
