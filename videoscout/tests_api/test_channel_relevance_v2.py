"""Unit tests for US-076 channel relevance v2 decision tree."""
import json
from pathlib import Path

import pytest

from videoscout.core_engine.channel_discovery import (
    CATALOG_MIN_NON_MATCHING,
    CATALOG_PATTERN_MIN_SHARE,
    MIN_PER_VIDEO_OVERLAP,
    _extract_absent_dominant_pattern,
    evaluate_channel_relevance,
)


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "jetzt_kommt_rolf_channels.json"


@pytest.fixture(scope="module")
def fixture():
    with FIXTURE_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


class TestEvaluateChannelRelevance:
    """Golden regression cases for the German trend keyword ``jetzt kommt rolf``."""

    def test_cargo_topic_passes_via_metadata(self, fixture):
        case = next(c for c in fixture["cases"] if c["channel_name"] == "Cargo - Topic")
        passed, score, reason, signals = evaluate_channel_relevance(
            fixture["keyword"],
            channel_name=case["channel_name"],
            channel_description=case["channel_description"],
            videos=case["videos"],
        )
        assert passed is True
        assert reason == "metadata_pass"
        assert signals["decision_branch"] == "metadata_pass"
        assert signals["match_count"] == 0
        assert signals["match_rate"] == 0.0
        assert signals["metadata_score"] > 0
        assert signals["catalog_dominant_pattern"] is None

    def test_rolfs_vater_is_rejected(self, fixture):
        case = next(c for c in fixture["cases"] if c["channel_name"] == "Rolfs Vater")
        passed, score, reason, signals = evaluate_channel_relevance(
            fixture["keyword"],
            channel_name=case["channel_name"],
            channel_description=case["channel_description"],
            videos=case["videos"],
        )
        assert passed is False
        assert reason == "rejected"
        assert signals["decision_branch"] == "rejected"
        assert signals["metadata_score"] == 0.0

    def test_simonsagtvevo_is_rejected(self, fixture):
        case = next(c for c in fixture["cases"] if c["channel_name"] == "SimonsagtVEVO")
        passed, score, reason, signals = evaluate_channel_relevance(
            fixture["keyword"],
            channel_name=case["channel_name"],
            channel_description=case["channel_description"],
            videos=case["videos"],
        )
        assert passed is False
        assert reason == "rejected"
        assert signals["decision_branch"] == "rejected"

    def test_hans_schmitz_is_catalog_outlier(self, fixture):
        case = next(c for c in fixture["cases"] if c["channel_name"] == "Hans Schmitz")
        passed, score, reason, signals = evaluate_channel_relevance(
            fixture["keyword"],
            channel_name=case["channel_name"],
            channel_description=case["channel_description"],
            videos=case["videos"],
        )
        assert passed is False
        assert reason == "catalog_outlier_single"
        assert signals["decision_branch"] == "catalog_outlier_single"
        assert signals["match_count"] == 1
        assert signals["match_rate"] == 0.1
        assert signals["catalog_dominant_pattern"] is not None
        assert "retter" in signals["catalog_dominant_pattern"]

    def test_mikado_singt_is_catalog_coherent(self, fixture):
        case = next(c for c in fixture["cases"] if c["channel_name"] == "Mikado singt")
        passed, score, reason, signals = evaluate_channel_relevance(
            fixture["keyword"],
            channel_name=case["channel_name"],
            channel_description=case["channel_description"],
            videos=case["videos"],
        )
        assert passed is True
        assert reason == "catalog_coherent_single"
        assert signals["decision_branch"] == "catalog_coherent_single"
        assert signals["match_count"] == 1
        assert signals["match_rate"] == 0.1
        assert signals["catalog_dominant_pattern"] is None

    def test_match_rate_alone_cannot_separate_hans_and_mikado(self, fixture):
        """Anti-trap: identical match_rate must not determine the outcome."""
        hans = next(c for c in fixture["cases"] if c["channel_name"] == "Hans Schmitz")
        mikado = next(c for c in fixture["cases"] if c["channel_name"] == "Mikado singt")

        _, _, _, hans_signals = evaluate_channel_relevance(
            fixture["keyword"],
            channel_name=hans["channel_name"],
            channel_description=hans["channel_description"],
            videos=hans["videos"],
        )
        _, _, _, mikado_signals = evaluate_channel_relevance(
            fixture["keyword"],
            channel_name=mikado["channel_name"],
            channel_description=mikado["channel_description"],
            videos=mikado["videos"],
        )

        assert hans_signals["match_rate"] == mikado_signals["match_rate"]
        assert hans_signals["match_count"] == mikado_signals["match_count"]
        assert hans_signals["decision_branch"] == "catalog_outlier_single"
        assert mikado_signals["decision_branch"] == "catalog_coherent_single"


class TestCatalogCoherenceHelpers:
    def test_detects_absent_trigram_in_coherent_catalog(self):
        non_matching = [
            "Der Retter Film 1 - Ostern",
            "Der Retter Film 2 - Passion",
            "Der Retter Film 3 - Auferstehung",
            "Der Retter Film 4 - Glaube",
            "Der Retter Film 5 - Hoffnung",
            "Der Retter Film 6 - Liebe",
            "Der Retter Film 7 - Frieden",
            "Der Retter Film 8 - Gnade",
            "Der Retter Film 9 - Erlösung",
        ]
        matching = "Rolf Zuckowski Jetzt kommt die Osterzeit Film Der Retter"
        pattern = _extract_absent_dominant_pattern(
            non_matching,
            matching,
            CATALOG_PATTERN_MIN_SHARE,
            CATALOG_MIN_NON_MATCHING,
        )
        assert pattern is not None
        assert "retter" in pattern

    def test_no_absent_pattern_when_matching_video_fits(self):
        non_matching = [
            "Mikado singt - Kinderlied Mix",
            "Mikado singt - Frühlingslieder",
            "Mikado singt - Osterlieder für Kinder",
            "Mikado singt - Rolf Zuckowski Medley",
            "Mikado singt - Sing mit uns",
            "Mikado singt - Live Session",
            "Mikado singt - Acapella Cover",
            "Mikado singt - Neue Covers",
            "Mikado singt - Backstage",
        ]
        matching = "Mikado singt - Jetzt kommt Rolf Zuckowski Osterlied Cover"
        pattern = _extract_absent_dominant_pattern(
            non_matching,
            matching,
            CATALOG_PATTERN_MIN_SHARE,
            CATALOG_MIN_NON_MATCHING,
        )
        assert pattern is None

    def test_insufficient_non_matching_videos_returns_none(self):
        pattern = _extract_absent_dominant_pattern(
            ["One title", "Another title"],
            "Matching title",
            CATALOG_PATTERN_MIN_SHARE,
            CATALOG_MIN_NON_MATCHING,
        )
        assert pattern is None


class TestPerVideoOverlap:
    def test_exact_token_overlap_counts_as_match(self):
        videos = [{"title": "ai marketing niche tutorial", "description": ""}]
        passed, score, reason, signals = evaluate_channel_relevance(
            "ai marketing niche",
            channel_name="",
            channel_description="",
            videos=videos,
        )
        assert passed is True
        assert signals["match_count"] == 1
        assert signals["video_best"] == 1.0

    def test_partial_token_overlap_below_threshold_is_rejected(self):
        videos = [{"title": "rolf prank compilation", "description": ""}]
        passed, score, reason, signals = evaluate_channel_relevance(
            "jetzt kommt rolf",
            channel_name="",
            channel_description="",
            videos=videos,
        )
        assert passed is False
        assert signals["match_count"] == 0
        assert signals["video_best"] == pytest.approx(1 / 3, abs=0.01)
        assert signals["video_best"] < MIN_PER_VIDEO_OVERLAP

    def test_multi_video_match_passes(self):
        videos = [
            {"title": "ai marketing niche part 1", "description": ""},
            {"title": "ai marketing niche part 2", "description": ""},
            {"title": "unrelated video", "description": ""},
        ]
        passed, score, reason, signals = evaluate_channel_relevance(
            "ai marketing niche",
            channel_name="",
            channel_description="",
            videos=videos,
        )
        assert passed is True
        assert reason == "multi_video"
        assert signals["match_count"] == 2
