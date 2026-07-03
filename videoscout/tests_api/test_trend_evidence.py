"""Tests for TrendEvidence v1 (US-062)."""
from datetime import datetime, timedelta, timezone

import pytest

from videoscout.core_engine.trend_evidence import (
    SCHEMA_VERSION,
    EvidenceBuilder,
    LifecycleClassifier,
    attach_velocity_to_videos,
    compute_velocity_percentiles,
    compute_velocity_raw,
    replay_evidence,
    serialize_evidence,
    trend_signals_from_evidence,
    velocity_percentile_from_evidence,
)


def _published_hours_ago(hours: float) -> str:
    when = datetime.now(timezone.utc) - timedelta(hours=hours)
    return when.isoformat().replace("+00:00", "Z")


def test_compute_velocity_raw_uses_log_views_over_sqrt_hours():
    published = _published_hours_ago(4)
    raw = compute_velocity_raw(10_000, published)
    assert raw is not None
    assert raw > 0


def test_compute_velocity_raw_requires_positive_views():
    assert compute_velocity_raw(0, _published_hours_ago(1)) is None


def test_velocity_percentile_within_region_category_batch():
    videos = [
        {
            "id": "a",
            "category_id": "20",
            "velocity_raw": 1.0,
        },
        {
            "id": "b",
            "category_id": "20",
            "velocity_raw": 3.0,
        },
        {
            "id": "c",
            "category_id": "10",
            "velocity_raw": 5.0,
        },
    ]
    percentiles = compute_velocity_percentiles(videos, region="DE")
    assert percentiles["b"] > percentiles["a"]
    assert percentiles["c"] == 0.5


def test_attach_velocity_to_videos():
    videos = attach_velocity_to_videos([
        {
            "id": "v1",
            "title": "Example",
            "channel_id": "UC1",
            "published_at": _published_hours_ago(2),
            "view_count": 50_000,
            "category_id": "22",
        }
    ])
    assert videos[0]["velocity_raw"] is not None


def test_evidence_builder_raw_derived_metadata_separation():
    builder = EvidenceBuilder(pipeline_run_id="job-1", region="DE")
    evidence = builder.build(
        keyword="small business tips",
        source_video={
            "id": "vid",
            "title": "Small Business Tips",
            "channel_id": "UC1",
            "published_at": _published_hours_ago(6),
            "view_count": 120_000,
            "category_id": "22",
            "velocity_raw": 2.5,
        },
        velocity_percentile=0.82,
    )
    assert evidence["schema_version"] == SCHEMA_VERSION
    assert evidence["raw"]["youtube"]["view_count"] == 120_000
    assert evidence["derived"]["velocity"]["raw"] == 2.5
    assert evidence["derived"]["velocity"]["percentile_region_category"] == 0.82
    assert evidence["metadata"]["pipeline_run_id"] == "job-1"
    assert "lifecycle" not in evidence


def test_serialize_evidence_rejects_velocity_in_raw():
    builder = EvidenceBuilder(pipeline_run_id="job-1", region="DE")
    evidence = builder.build(
        keyword="kw",
        source_video={"id": "v", "title": "T", "channel_id": "c"},
    )
    evidence["raw"]["velocity"] = 1.0
    with pytest.raises(ValueError, match="derived"):
        serialize_evidence(evidence)


def test_serialize_evidence_rejects_persisted_lifecycle():
    builder = EvidenceBuilder(pipeline_run_id="job-1", region="DE")
    evidence = builder.build(
        keyword="kw",
        source_video={"id": "v", "title": "T", "channel_id": "c"},
    )
    evidence["lifecycle"] = "early_accelerating"
    with pytest.raises(ValueError, match="lifecycle"):
        serialize_evidence(evidence)


def test_lifecycle_classifier_derived_not_persisted():
    builder = EvidenceBuilder(pipeline_run_id="job-1", region="DE")
    evidence = builder.build(
        keyword="kw",
        source_video={"id": "v", "title": "T", "channel_id": "c"},
        velocity_percentile=0.9,
    )
    assert LifecycleClassifier.classify(evidence) == "early_accelerating"


def test_trend_signals_from_evidence_backward_compat():
    builder = EvidenceBuilder(pipeline_run_id="job-1", region="DE")
    evidence = builder.build(
        keyword="kw",
        source_video={
            "id": "vid",
            "title": "Title Here",
            "channel_id": "UC9",
            "published_at": _published_hours_ago(1),
            "view_count": 1_000,
            "category_id": "20",
        },
    )
    signals = trend_signals_from_evidence(evidence)
    assert signals["source_title"] == "Title Here"
    assert signals["video_id"] == "vid"


def test_velocity_percentile_from_evidence_helper():
    payload = {
        "derived": {"velocity": {"percentile_region_category": 0.66}},
    }
    assert velocity_percentile_from_evidence(payload) == 0.66


def test_replay_evidence_round_trip():
    builder = EvidenceBuilder(pipeline_run_id="job-1", region="DE")
    evidence = serialize_evidence(
        builder.build(
            keyword="kw",
            source_video={"id": "v", "title": "T", "channel_id": "c"},
        )
    )
    replayed = replay_evidence(evidence)
    assert replayed is not None
    assert replayed["schema_version"] == SCHEMA_VERSION


def test_nurture_trend_uses_velocity_percentile():
    from videoscout.core_engine.nurture_scorer import compute_trend_signal

    score, reason = compute_trend_signal(
        "business tips",
        "youtube_trend",
        "Some Title",
        trend_evidence={
            "derived": {"velocity": {"percentile_region_category": 0.88}},
        },
    )
    assert score == pytest.approx(0.88, abs=0.01)
    assert "percentile" in reason.lower()
