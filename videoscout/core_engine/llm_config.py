"""Resolve LLM config: DB overrides > environment > defaults."""
import os
from typing import Optional

from openai import OpenAI
from sqlalchemy.orm import Session

from videoscout.db.models import SettingsModel

DEFAULT_BASE_URL = "http://localhost:20128/v1"
DEFAULT_API_KEY = "sk-local"
DEFAULT_MODEL = "gpt-4o-mini"


def _env_config() -> dict:
    return {
        "base_url": os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL),
        "api_key": os.getenv("LLM_API_KEY", DEFAULT_API_KEY),
        "model": os.getenv("LLM_MODEL", DEFAULT_MODEL),
    }


def get_llm_config(db: Optional[Session] = None) -> dict:
    """Effective LLM config after applying DB overrides on top of env defaults."""
    config = _env_config()

    settings = None
    if db is not None:
        settings = db.query(SettingsModel).first()
    else:
        try:
            from videoscout.db import get_session

            session = get_session()
            try:
                settings = session.query(SettingsModel).first()
            finally:
                session.close()
        except Exception:
            settings = None

    if settings:
        if settings.llm_base_url:
            config["base_url"] = settings.llm_base_url
        if settings.llm_api_key:
            config["api_key"] = settings.llm_api_key
        if settings.llm_model:
            config["model"] = settings.llm_model

    return config


def llm_api_key_configured(db: Optional[Session] = None) -> bool:
    """True when an API key is set in DB or environment."""
    config = _env_config()
    if db is not None:
        settings = db.query(SettingsModel).first()
        if settings and settings.llm_api_key:
            return True
    else:
        try:
            from videoscout.db import get_session

            session = get_session()
            try:
                settings = session.query(SettingsModel).first()
                if settings and settings.llm_api_key:
                    return True
            finally:
                session.close()
        except Exception:
            pass
    return bool(os.getenv("LLM_API_KEY")) or config["api_key"] != DEFAULT_API_KEY


def _create_client_from_config(config: dict) -> OpenAI:
    try:
        import httpx

        httpx_client = httpx.Client(
            timeout=30.0,
            headers={"User-Agent": "VideoScout/1.0"},
        )
        return OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
            http_client=httpx_client,
        )
    except Exception:
        return OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )


def create_llm_client(db: Optional[Session] = None) -> OpenAI:
    """Create OpenAI client from effective LLM config (DB > env > defaults)."""
    return _create_client_from_config(get_llm_config(db))


def list_llm_models(
    db: Optional[Session] = None,
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> list[str]:
    """Fetch model ids from the configured OpenAI-compatible API."""
    config = get_llm_config(db)
    if base_url and base_url.strip():
        config["base_url"] = base_url.strip()
    if api_key and api_key.strip():
        config["api_key"] = api_key.strip()

    client = _create_client_from_config(config)
    response = client.models.list()
    ids = sorted({m.id for m in response.data if getattr(m, "id", None)})
    return ids
