"""Settings API endpoints - Full implementation with DB persistence."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from videoscout.db import get_db
from videoscout.db.models import SettingsModel
from videoscout.schemas import (
    SettingsResponse, UpdateSettingsRequest,
    ScoringWeights, NicheDefinition, LLMConfig, TikTokConfig
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
            api_key_set=bool(s.llm_api_key)
        ),
        tiktok=TikTokConfig(
            api_key_set=bool(s.tiktok_api_key),
            check_enabled=s.tiktok_check_enabled
        )
    )


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
        # Don't update api_key_set (read-only field)
    
    if payload.tiktok:
        if payload.tiktok.check_enabled is not None:
            s.tiktok_check_enabled = payload.tiktok.check_enabled
        # Don't update api_key_set (read-only field)
    
    s.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Settings updated"}
