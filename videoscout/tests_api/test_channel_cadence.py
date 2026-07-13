"""Unit tests for US-076b short-upload cadence bonus (M2 cascade)."""
import json
from pathlib import Path

import pytest

from videoscout.core_engine.channel_discovery import (
    CADENCE_BONUS_MAX,
    CADENCE_MIN_AVG_VIEWS,
    SHORT_MAX_DURATION_SEC,
    compute_short_upload_cadence,
    evaluate_channel_relevance,
)


def _video(title, published_at, duration_sec, description=""):
    return {
        "title": title,
        "description": description,
        "published_at": published_at,
        "duration_sec": duration_sec,
        "view_count": 0,
    }


class TestComputeShortUploadCadence:
    def test_zero_shorts_returns_zero_cadence(self):
        cadence = compute_short_upload_cadence([])
        assert cadence["shorts_count"] == 0
        assert cadence["shorts_per_day"] == 0.0
        assert cadence["window_span_days"] == 0.0
        assert cadence["cadence_confidence"] == "low"

    def test_long_videos_are_excluded_from_shorts(self):
        videos = [
            _video("short", "2026-07-07T00:00:00Z", SHORT_MAX_DURATION_SEC),
            _video("long", "2026-07-07T00:00:00Z", SHORT_MAX_DURATION_SEC + 1),
        ]
        cadence = compute_short_upload_cadence(videos)
        assert cadence["shorts_count"] == 1
        assert cadence["shorts_per_day"] == 1.0

    def test_missing_duration_skips_video(self):
        videos = [
            {"title": "no duration", "published_at": "2026-07-07T00:00:00Z"},
        ]
        cadence = compute_short_upload_cadence(videos)
        assert cadence["shorts_count"] == 0

    def test_seven_shorts_over_seven_days(self):
        videos = [
            _video(f"day {i+1}", f"2026-07-{i+1:02d}T12:00:00Z", 60)
            for i in range(7)
        ]
        cadence = compute_short_upload_cadence(videos)
        assert cadence["shorts_count"] == 7
        assert cadence["shorts_per_day"] == pytest.approx(7 / 6, abs=0.01)
        assert cadence["cadence_confidence"] == "high"

    def test_same_calendar_day_shorts_use_day_resolution(self):
        videos = [
            _video("morning", "2026-07-07T08:00:00Z", 60),
            _video("noon", "2026-07-07T12:00:00Z", 60),
            _video("evening", "2026-07-07T20:00:00Z", 60),
        ]
        cadence = compute_short_upload_cadence(videos)
        assert cadence["shorts_count"] == 3
        assert cadence["shorts_per_day"] == 3.0
        assert cadence["window_span_days"] == 1.0


class TestCadenceBonusInEvaluate:
    def test_bonus_applies_when_cadence_and_views_meet_threshold(self):
        videos = [
            _video(
                f"ai marketing niche tip {i+1}",
                f"2026-07-{i+1:02d}T12:00:00Z",
                60,
            )
            for i in range(7)
        ]
        passed, score, branch, signals = evaluate_channel_relevance(
            "ai marketing niche",
            channel_name="",
            channel_description="",
            videos=videos,
            channel_avg_views=CADENCE_MIN_AVG_VIEWS,
        )
        assert passed is True
        assert branch == "multi_video"
        assert signals["shorts_per_day"] > 0.0
        assert signals["cadence_bonus"] == CADENCE_BONUS_MAX
        assert signals["cadence_skipped"] is False
        assert signals["source_quality_score"] == pytest.approx(
            score, abs=0.001
        )

    def test_no_bonus_when_avg_views_too_low(self):
        videos = [
            _video(
                f"ai marketing niche tip {i+1}",
                f"2026-07-{i+1:02d}T12:00:00Z",
                60,
            )
            for i in range(7)
        ]
        passed, score, branch, signals = evaluate_channel_relevance(
            "ai marketing niche",
            channel_name="",
            channel_description="",
            videos=videos,
            channel_avg_views=CADENCE_MIN_AVG_VIEWS - 1,
        )
        assert signals["cadence_bonus"] == 0.0
        assert signals["cadence_skipped"] is False

    def test_metadata_pass_skips_cadence_bonus(self):
        # Cargo-style: metadata matches, no video overlap.
        passed, score, branch, signals = evaluate_channel_relevance(
            "rolf zuckowski",
            channel_name="Cargo - Topic",
            channel_description="Official channel for Rolf Zuckowski",
            videos=[_video("unrelated", "2026-07-07T00:00:00Z", 60)],
            channel_avg_views=CADENCE_MIN_AVG_VIEWS,
        )
        assert branch == "metadata_pass"
        assert signals["cadence_skipped"] is True
        assert signals["cadence_bonus"] == 0.0
        assert signals["shorts_per_day"] == 0.0


class TestCadenceRegression:
    """US-076 golden fixture must not change subscribe decisions."""

    FIXTURE_PATH = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "jetzt_kommt_rolf_channels.json"
    )

    @pytest.fixture(scope="class")
    def fixture(self):
        with self.FIXTURE_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def test_all_golden_cases_expect_subscribe_unchanged(self, fixture):
        for case in fixture["cases"]:
            passed, _score, branch, signals = evaluate_channel_relevance(
                fixture["keyword"],
                channel_name=case["channel_name"],
                channel_description=case["channel_description"],
                videos=case["videos"],
                channel_avg_views=100_000,
            )
            assert passed == case["expect_subscribe"], (
                f"{case['channel_name']}: expected subscribe={case['expect_subscribe']}, "
                f"got passed={passed}, branch={branch}"
            )
            # Cadence fields are present even when fixture lacks durations.
            assert "shorts_per_day" in signals
            assert "cadence_bonus" in signals
            assert "cadence_skipped" in signals

    def test_match_rate_anti_trap_still_holds(self, fixture):
        hans = next(c for c in fixture["cases"] if c["channel_name"] == "Hans Schmitz")
        mikado = next(
            c for c in fixture["cases"] if c["channel_name"] == "Mikado singt"
        )

        _, _, _, hans_signals = evaluate_channel_relevance(
            fixture["keyword"],
            channel_name=hans["channel_name"],
            channel_description=hans["channel_description"],
            videos=hans["videos"],
            channel_avg_views=100_000,
        )
        _, _, _, mikado_signals = evaluate_channel_relevance(
            fixture["keyword"],
            channel_name=mikado["channel_name"],
            channel_description=mikado["channel_description"],
            videos=mikado["videos"],
            channel_avg_views=100_000,
        )

        assert hans_signals["match_rate"] == mikado_signals["match_rate"]
        assert hans_signals["decision_branch"] == "catalog_outlier_single"
        assert mikado_signals["decision_branch"] == "catalog_coherent_single"
