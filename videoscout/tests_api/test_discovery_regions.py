"""Unit tests for discovery region allowlist (US-079)."""
import pytest

from videoscout.core_engine.discovery_regions import (
    DEFAULT_DISCOVERY_REGION_CODES,
    DiscoveryRegionError,
    normalize_discovery_region_codes,
    resolve_discovery_region_codes,
)


def test_normalize_default_when_none():
    assert normalize_discovery_region_codes(None) == list(DEFAULT_DISCOVERY_REGION_CODES)


def test_normalize_empty_falls_back_to_default():
    assert normalize_discovery_region_codes([]) == ["US"]


def test_normalize_uppercases_and_dedupes():
    assert normalize_discovery_region_codes(["us", "DE", "us", "jp"]) == [
        "US",
        "DE",
        "JP",
    ]


def test_normalize_rejects_unknown():
    with pytest.raises(DiscoveryRegionError, match="allowlist"):
        normalize_discovery_region_codes(["US", "VN"])


def test_resolve_prefers_region_codes_over_settings():
    assert resolve_discovery_region_codes(
        settings_codes=["DE"],
        region_codes=["JP", "KR"],
        region_code="US",
    ) == ["JP", "KR"]


def test_resolve_legacy_region_code():
    assert resolve_discovery_region_codes(
        settings_codes=["DE", "FR"],
        region_code="gb",
    ) == ["GB"]


def test_resolve_settings_when_no_override():
    assert resolve_discovery_region_codes(settings_codes=["MX", "ES"]) == ["MX", "ES"]
