"""Tests for settings API endpoints."""


def test_get_settings_defaults(client):
    resp = client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["weights"]["relevance"] == 0.30
    assert data["filters"]["min_score_threshold"] == 0.4
    assert data["llm"]["model"] == "gpt-4o"
    assert data["tiktok"]["check_enabled"] is True


def test_update_settings_weights(client, db_session):
    resp = client.put("/api/v1/settings", json={
        "weights": {
            "relevance": 0.40,
            "specificity": 0.20,
            "saturation": 0.20,
            "trend": 0.10,
            "video_performance": 0.10
        }
    })
    assert resp.status_code == 200

    # Verify persisted
    get_resp = client.get("/api/v1/settings")
    assert get_resp.json()["weights"]["relevance"] == 0.40
    assert get_resp.json()["weights"]["specificity"] == 0.20


def test_update_settings_niche(client):
    client.put("/api/v1/settings", json={
        "niche": {
            "topics": ["AI", "marketing", "automation"],
            "preferred_language": "vi",
            "target_audience": "entrepreneurs"
        }
    })
    resp = client.get("/api/v1/settings")
    data = resp.json()
    assert "AI" in data["niche"]["topics"]
    assert data["niche"]["preferred_language"] == "vi"
    assert data["niche"]["target_audience"] == "entrepreneurs"
