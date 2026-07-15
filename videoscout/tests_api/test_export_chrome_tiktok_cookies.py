"""Unit tests for Chrome/Comet → Cookie-Editor export helpers."""
from types import SimpleNamespace
from unittest.mock import patch

from scripts.export_chrome_tiktok_cookies import (
    _score_rows,
    cookie_to_editor_dict,
    list_comet_profiles,
)
from videoscout.services.tiktok import parse_tiktok_cookies_payload


def test_cookie_to_editor_dict_and_parse_roundtrip():
    jar_cookie = SimpleNamespace(
        name="msToken",
        value="abc123longtoken",
        domain=".tiktok.com",
        path="/",
        secure=True,
        expires=1800000000,
        _rest={"HttpOnly": None, "SameSite": "None"},
    )
    row = cookie_to_editor_dict(jar_cookie)
    assert row["name"] == "msToken"
    assert row["value"] == "abc123longtoken"
    assert row["domain"] == ".tiktok.com"
    assert row["sameSite"] == "no_restriction"
    assert row["httpOnly"] is True

    profiles = parse_tiktok_cookies_payload([row])
    assert profiles == [{"msToken": "abc123longtoken"}]


def test_score_rows_prefers_mstoken_and_session():
    weak = [{"name": "ttwid", "value": "x"}]
    strong = [
        {"name": "msToken", "value": "tok"},
        {"name": "sessionid", "value": "sid"},
    ]
    assert _score_rows(strong) > _score_rows(weak)


def test_list_comet_profiles_filters_system(tmp_path):
    (tmp_path / "Default").mkdir()
    (tmp_path / "Default" / "Cookies").write_bytes(b"x")
    (tmp_path / "System Profile").mkdir()
    (tmp_path / "System Profile" / "Cookies").write_bytes(b"x")
    (tmp_path / "Profile 4").mkdir()
    (tmp_path / "Profile 4" / "Cookies").write_bytes(b"x")
    with patch("scripts.export_chrome_tiktok_cookies.COMET_SUPPORT_DIR", tmp_path):
        assert list_comet_profiles() == ["Default", "Profile 4"]
