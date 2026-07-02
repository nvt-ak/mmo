"""Tests for LLM config wiring into SuggestionEngine."""
from unittest.mock import MagicMock, patch

from videoscout.db.models import SettingsModel


def test_suggestion_engine_uses_db_llm_config(db_session):
    db_session.add(
        SettingsModel(
            llm_api_key="sk-test-override",
            llm_base_url="https://api.example.com/v1",
            llm_model="gpt-test-model",
        )
    )
    db_session.commit()

    with patch("videoscout.core_engine.engine.create_llm_client") as mock_create:
        mock_create.return_value = MagicMock()
        from videoscout.core_engine.engine import SuggestionEngine

        engine = SuggestionEngine(db_session=db_session)

    mock_create.assert_called_once_with(db_session)
    assert engine.llm_model == "gpt-test-model"
