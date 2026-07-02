"""Tests for sources (channel management) API endpoints."""
from unittest.mock import patch, MagicMock


def test_list_channels_empty(client):
    resp = client.get("/api/v1/sources/channels")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@patch("videoscout.api.sources.get_youtube_service")
def test_add_channel_success(mock_yt, client, db_session):
    mock_svc = MagicMock()
    mock_svc.extract_channel_id.return_value = "UCxxxxxxxxxxxxxxxxxxxxxxxx"
    mock_svc.get_channel_info.return_value = {
        "name": "Test Channel",
        "description": "Tech content",
        "thumbnail_url": "http://example.com/thumb.jpg",
        "subscribers": 10000
    }
    mock_yt.return_value = mock_svc

    resp = client.post("/api/v1/sources/channels", json={
        "channel_id": "@testchannel"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel_id"] == "UCxxxxxxxxxxxxxxxxxxxxxxxx"
    assert data["name"] == "Test Channel"
    assert data["subscriber_count"] == 10000

    from videoscout.db.models import ChannelModel
    assert db_session.query(ChannelModel).count() == 1


@patch("videoscout.api.sources.get_youtube_service")
def test_add_channel_duplicate(mock_yt, client, db_session):
    mock_svc = MagicMock()
    mock_svc.extract_channel_id.return_value = "UC_dup12345678901234567890"
    mock_svc.get_channel_info.return_value = {"name": "Dup", "description": "", "thumbnail_url": "", "subscribers": 0}
    mock_yt.return_value = mock_svc

    client.post("/api/v1/sources/channels", json={"channel_id": "@dup"})
    resp = client.post("/api/v1/sources/channels", json={"channel_id": "@dup"})
    assert resp.status_code == 409


@patch("videoscout.api.sources.get_youtube_service")
def test_add_channel_unresolvable(mock_yt, client):
    mock_svc = MagicMock()
    mock_svc.extract_channel_id.return_value = None
    mock_yt.return_value = mock_svc

    resp = client.post("/api/v1/sources/channels", json={"channel_id": "garbage"})
    assert resp.status_code == 400


@patch("videoscout.api.sources.get_youtube_service")
def test_update_channel_scan_enabled(mock_yt, client, db_session):
    mock_svc = MagicMock()
    mock_svc.extract_channel_id.return_value = "UC_toggle_123456789012345672"
    mock_svc.get_channel_info.return_value = {"name": "Toggle", "description": "", "thumbnail_url": "", "subscribers": 0}
    mock_yt.return_value = mock_svc

    add_resp = client.post("/api/v1/sources/channels", json={"channel_id": "@toggle"})
    channel_id = add_resp.json()["channel_id"]

    update_resp = client.put(f"/api/v1/sources/channels/{channel_id}?scan_enabled=false")
    assert update_resp.status_code == 200

    from videoscout.db.models import ChannelModel
    ch = db_session.query(ChannelModel).first()
    assert ch.scan_enabled is False
