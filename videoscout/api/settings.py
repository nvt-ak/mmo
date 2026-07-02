"""Settings API endpoints - Full implementation with DB persistence."""
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from videoscout.db import get_db
from videoscout.db.models import SettingsModel
from videoscout.schemas import (
    SettingsResponse, UpdateSettingsRequest,
    ScoringWeights, NicheDefinition, LLMConfig, TikTokConfig,
    LLMModelsRequest, LLMModelsResponse,
)
from videoscout.core_engine.llm_config import (
    get_llm_config, llm_api_key_configured, list_llm_models,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_or_create_settings(db: Session) -> SettingsModel:
    """Get the single settings row, or create with defaults."""
    settings = db.query(SettingsModel).first()
    if not settings:
        settings = SettingsModel()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    """Get current settings from database."""
    s = _get_or_create_settings(db)
    effective_llm = get_llm_config(db)
    
    return SettingsResponse(
        weights=ScoringWeights(
            relevance=s.weight_relevance,
            specificity=s.weight_specificity,
            saturation=s.weight_saturation,
            trend=s.weight_trend,
            video_performance=s.weight_video_performance
        ),
        filters={
            "min_score_threshold": s.min_score_threshold,
            "min_specificity": s.min_specificity,
            "min_saturation": s.min_saturation,
            "max_suggestions_per_video": s.max_suggestions_per_video
        },
        niche=NicheDefinition(
            topics=s.niche_topics or [],
            preferred_language=s.niche_preferred_language,
            target_audience=s.niche_target_audience
        ),
        llm=LLMConfig(
            model=s.llm_model,
            temperature=s.llm_temperature,
            base_url=effective_llm["base_url"],
            api_key_set=llm_api_key_configured(db),
        ),
        tiktok=TikTokConfig(
            api_key_set=bool(s.tiktok_api_key or os.getenv("TIKTOK_MS_TOKEN", "").strip()),
            check_enabled=s.tiktok_check_enabled
        )
    )


@router.post("/settings/llm/models", response_model=LLMModelsResponse)
async def fetch_llm_models(
    payload: LLMModelsRequest,
    db: Session = Depends(get_db),
):
    """List models from the configured OpenAI-compatible endpoint."""
    try:
        models = list_llm_models(
            db,
            base_url=payload.base_url,
            api_key=payload.api_key,
        )
    except Exception as exc:
        logger.warning("Failed to list LLM models: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch models: {exc}",
        ) from exc

    return LLMModelsResponse(models=models)


@router.put("/settings")
async def update_settings(
    payload: UpdateSettingsRequest,
    db: Session = Depends(get_db)
):
    """Update settings in database."""
    s = _get_or_create_settings(db)
    
    if payload.weights:
        s.weight_relevance = payload.weights.relevance
        s.weight_specificity = payload.weights.specificity
        s.weight_saturation = payload.weights.saturation
        s.weight_trend = payload.weights.trend
        s.weight_video_performance = payload.weights.video_performance
    
    if payload.filters:
        if 'min_score_threshold' in payload.filters:
            s.min_score_threshold = payload.filters['min_score_threshold']
        if 'min_specificity' in payload.filters:
            s.min_specificity = payload.filters['min_specificity']
        if 'min_saturation' in payload.filters:
            s.min_saturation = payload.filters['min_saturation']
        if 'max_suggestions_per_video' in payload.filters:
            s.max_suggestions_per_video = payload.filters['max_suggestions_per_video']
    
    if payload.niche:
        if payload.niche.topics is not None:
            s.niche_topics = payload.niche.topics
        if payload.niche.preferred_language:
            s.niche_preferred_language = payload.niche.preferred_language
        if payload.niche.target_audience is not None:
            s.niche_target_audience = payload.niche.target_audience
    
    if payload.llm:
        if payload.llm.model:
            s.llm_model = payload.llm.model
        if payload.llm.temperature is not None:
            s.llm_temperature = payload.llm.temperature
        if payload.llm.base_url is not None:
            s.llm_base_url = payload.llm.base_url.strip() or None
        if payload.llm.api_key:
            s.llm_api_key = payload.llm.api_key.strip()
    
    if payload.tiktok:
        if payload.tiktok.check_enabled is not None:
            s.tiktok_check_enabled = payload.tiktok.check_enabled
        # Don't update api_key_set (read-only field)
    
    s.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Settings updated"}
