"""Performance-report calibration overlay for nurture/beta classifier (v2)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from videoscout.db.models import PerformanceReportModel, SuggestionModel

CLASSIFIER_CALIBRATION_MIN_REPORTS = 15
MIN_BUCKET_SAMPLES = 3
SUCCESS_DELTA_THRESHOLD = 0.20
CALIBRATION_BOOST = 1


@dataclass
class ClassifierCalibration:
    report_count: int = 0
    buckets: Dict[str, Dict[str, Dict[str, float]]] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.report_count >= CLASSIFIER_CALIBRATION_MIN_REPORTS


def _word_bucket(word_count: int) -> str:
    return "short" if word_count <= 3 else "long"


def _source_bucket(source: str) -> str:
    if source in ("youtube_trend", "social"):
        return "broad"
    return "niche"


def _saturation_bucket(tier: str | None) -> str:
    if tier in ("fresh", "moderate", "saturated"):
        return tier
    return "moderate"


def feature_bucket_key(
    *,
    word_count: int,
    trend_source: str,
    saturation_tier: str | None,
) -> str:
    return "|".join(
        [
            _word_bucket(word_count),
            _source_bucket(trend_source or "youtube_trend"),
            _saturation_bucket(saturation_tier),
        ]
    )


def _outcome_weight(outcome: str | None) -> float:
    if outcome == "success":
        return 1.0
    if outcome == "neutral":
        return 0.5
    if outcome == "failure":
        return 0.0
    return 0.5


def build_classifier_calibration(db: Session) -> ClassifierCalibration:
    rows = (
        db.query(PerformanceReportModel, SuggestionModel)
        .join(
            SuggestionModel,
            PerformanceReportModel.suggestion_id == SuggestionModel.id,
        )
        .filter(PerformanceReportModel.outcome.isnot(None))
        .all()
    )

    buckets: Dict[str, Dict[str, Dict[str, float]]] = {}
    for report, suggestion in rows:
        keyword_type = suggestion.keyword_type or "beta"
        if keyword_type not in ("nurture", "beta"):
            continue

        stats = suggestion.tiktok_stats or {}
        tier = stats.get("saturation_tier") or suggestion.tiktok_status or "moderate"
        if tier == "low":
            tier = "fresh"
        key = feature_bucket_key(
            word_count=len((suggestion.keyword or "").split()),
            trend_source=suggestion.discovery_source or "youtube_trend",
            saturation_tier=tier,
        )
        bucket = buckets.setdefault(
            key,
            {
                "beta": {"weighted_success": 0.0, "count": 0.0},
                "nurture": {"weighted_success": 0.0, "count": 0.0},
            },
        )
        weight = _outcome_weight(report.outcome)
        bucket[keyword_type]["weighted_success"] += weight
        bucket[keyword_type]["count"] += 1.0

    return ClassifierCalibration(report_count=len(rows), buckets=buckets)


def _track_success_rate(bucket: Dict[str, Dict[str, float]], track: str) -> Optional[float]:
    stats = bucket.get(track) or {}
    count = float(stats.get("count", 0.0))
    if count < MIN_BUCKET_SAMPLES:
        return None
    return float(stats.get("weighted_success", 0.0)) / count


def apply_classifier_calibration(
    nurture_score: int,
    beta_score: int,
    *,
    word_count: int,
    trend_source: str,
    saturation_tier: str | None,
    calibration: Optional[ClassifierCalibration],
) -> Tuple[int, int, Optional[str]]:
    """Return adjusted scores and optional calibration reason."""
    if calibration is None or not calibration.is_active:
        return nurture_score, beta_score, None

    key = feature_bucket_key(
        word_count=word_count,
        trend_source=trend_source,
        saturation_tier=saturation_tier,
    )
    bucket = calibration.buckets.get(key)
    if not bucket:
        return nurture_score, beta_score, None

    beta_rate = _track_success_rate(bucket, "beta")
    nurture_rate = _track_success_rate(bucket, "nurture")
    if beta_rate is None or nurture_rate is None:
        return nurture_score, beta_score, None

    delta = beta_rate - nurture_rate
    if delta >= SUCCESS_DELTA_THRESHOLD:
        return nurture_score, beta_score + CALIBRATION_BOOST, (
            f"bucket {key}: beta success {beta_rate:.0%} vs nurture {nurture_rate:.0%}"
        )
    if delta <= -SUCCESS_DELTA_THRESHOLD:
        return nurture_score + CALIBRATION_BOOST, beta_score, (
            f"bucket {key}: nurture success {nurture_rate:.0%} vs beta {beta_rate:.0%}"
        )
    return nurture_score, beta_score, None


def summarize_calibration(calibration: ClassifierCalibration) -> str:
    lines = [
        f"Classifier calibration: {calibration.report_count} linked reports",
        f"Active overlay: {'yes' if calibration.is_active else 'no'} "
        f"(threshold {CLASSIFIER_CALIBRATION_MIN_REPORTS})",
        f"Buckets with data: {len(calibration.buckets)}",
    ]
    for key in sorted(calibration.buckets):
        bucket = calibration.buckets[key]
        beta_rate = _track_success_rate(bucket, "beta")
        nurture_rate = _track_success_rate(bucket, "nurture")
        beta_n = int(bucket.get("beta", {}).get("count", 0))
        nurture_n = int(bucket.get("nurture", {}).get("count", 0))
        lines.append(
            f"  {key}: beta={beta_rate if beta_rate is not None else 'n/a'}"
            f" ({beta_n}), nurture={nurture_rate if nurture_rate is not None else 'n/a'}"
            f" ({nurture_n})"
        )
    return "\n".join(lines)
