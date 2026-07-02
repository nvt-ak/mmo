"""Tests for nurture/beta keyword classifier (spec §6.2)."""
import pytest

from videoscout.core_engine.keyword_classifier import classify_keyword_type


@pytest.mark.parametrize(
    "keyword,source,sat,expected",
    [
        ("winter fancam", "youtube_trend", "saturated", "nurture"),
        ("aespa winter fancam", "youtube_trend", "moderate", "nurture"),
        ("kpop idol winter fancam", "niche_web", "fresh", "beta"),
        ("small business tiktok tips", "niche_web", "fresh", "beta"),
        ("viral dance trend", "social", "saturated", "nurture"),
        ("creator rewards long tail", "niche_web", "moderate", "beta"),
    ],
)
def test_classify_keyword_type(keyword, source, sat, expected):
    assert classify_keyword_type(keyword, trend_source=source, saturation_tier=sat) == expected


def test_short_youtube_trending_is_nurture():
    assert classify_keyword_type("new song", trend_source="youtube_trend") == "nurture"


def test_long_niche_is_beta():
    assert classify_keyword_type(
        "german cooking channel tips",
        trend_source="niche_web",
        saturation_tier="fresh",
    ) == "beta"
