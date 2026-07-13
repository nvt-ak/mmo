"""Tests for settings API endpoints."""
from unittest.mock import patch


def test_get_settings_defaults(client):
    resp = client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["weights"]["relevance"] == 0.30
    assert data["filters"]["min_score_threshold"] == 0.55
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


def test_update_settings_llm(client, db_session):
    resp = client.put("/api/v1/settings", json={
        "llm": {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "api_key": "sk-test-override",
        }
    })
    assert resp.status_code == 200

    get_resp = client.get("/api/v1/settings")
    data = get_resp.json()
    assert data["llm"]["base_url"] == "https://api.openai.com/v1"
    assert data["llm"]["model"] == "gpt-4o-mini"
    assert data["llm"]["api_key_set"] is True

    from videoscout.db.models import SettingsModel
    settings = db_session.query(SettingsModel).first()
    assert settings.llm_base_url == "https://api.openai.com/v1"
    assert settings.llm_model == "gpt-4o-mini"
    assert settings.llm_api_key == "sk-test-override"


def test_list_llm_models(client):
    with patch("videoscout.api.settings.list_llm_models", return_value=["gpt-4o-mini", "gpt-4o"]):
        resp = client.post("/api/v1/settings/llm/models", json={})

    assert resp.status_code == 200
    assert resp.json()["models"] == ["gpt-4o-mini", "gpt-4o"]


def test_list_llm_models_with_overrides(client):
    with patch("videoscout.api.settings.list_llm_models", return_value=["gemini/flash"]) as mock_list:
        resp = client.post(
            "/api/v1/settings/llm/models",
            json={"base_url": "http://localhost:20128/v1", "api_key": "sk-test"},
        )

    assert resp.status_code == 200
    assert resp.json()["models"] == ["gemini/flash"]
    mock_list.assert_called_once()
    assert mock_list.call_args.kwargs["base_url"] == "http://localhost:20128/v1"
    assert mock_list.call_args.kwargs["api_key"] == "sk-test"


def test_list_llm_models_upstream_error(client):
    with patch("videoscout.api.settings.list_llm_models", side_effect=RuntimeError("connection refused")):
        resp = client.post("/api/v1/settings/llm/models", json={})

    assert resp.status_code == 502


def test_update_settings_llm_api_key_unchanged_when_omitted(client, db_session):
    from videoscout.db.models import SettingsModel

    settings = SettingsModel(llm_api_key="sk-existing")
    db_session.add(settings)
    db_session.commit()

    client.put("/api/v1/settings", json={"llm": {"base_url": "http://localhost:20128/v1"}})

    db_session.refresh(settings)
    assert settings.llm_api_key == "sk-existing"


def test_get_settings_includes_scoring_rubrics(client):
    resp = client.get("/api/v1/settings")
    assert resp.status_code == 200
    rubrics = resp.json()["scoring_rubrics"]
    assert rubrics["nurture"]["text"]
    assert rubrics["nurture"]["default_text"]
    assert rubrics["nurture"]["is_custom"] is False
    assert rubrics["beta"]["text"]
    assert rubrics["beta"]["is_custom"] is False


def test_update_settings_scoring_rubric_override(client, db_session):
    from videoscout.core_engine.scoring_rubric import default_rubric_text
    from videoscout.db.models import SettingsModel

    custom = "Custom nurture rubric for testing.\n\nScore relatively."
    client.put("/api/v1/settings", json={"scoring_rubrics": {"nurture": custom}})
    resp = client.get("/api/v1/settings")
    data = resp.json()
    assert data["scoring_rubrics"]["nurture"]["is_custom"] is True
    assert data["scoring_rubrics"]["nurture"]["text"] == custom

    settings = db_session.query(SettingsModel).first()
    assert settings.nurture_scoring_rubric == custom


def test_update_settings_scoring_rubric_reset_to_default(client, db_session):
    from videoscout.core_engine.scoring_rubric import default_rubric_text
    from videoscout.db.models import SettingsModel

    default = default_rubric_text("nurture")
    settings = SettingsModel(nurture_scoring_rubric="Temporary override")
    db_session.add(settings)
    db_session.commit()

    client.put("/api/v1/settings", json={"scoring_rubrics": {"nurture": default}})
    db_session.refresh(settings)
    assert settings.nurture_scoring_rubric is None

    resp = client.get("/api/v1/settings")
    assert resp.json()["scoring_rubrics"]["nurture"]["is_custom"] is False
