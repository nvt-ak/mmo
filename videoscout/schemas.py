"""Pydantic schemas for API requests/responses."""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
import uuid


# Component scores
class ComponentScores(BaseModel):
    relevance: float = Field(..., ge=0, le=1)
    specificity: float = Field(..., ge=0, le=1)
    saturation: float = Field(..., ge=0, le=1)
    trend: float = Field(..., ge=0, le=1)
    video_performance: float = Field(..., ge=0, le=1)


class SuggestedByEntry(BaseModel):
    source: str  # 'digest_scan' | 'agent_learning' | 'manual'
    video_id: Optional[str] = None
    channel_id: Optional[str] = None
    score: float = Field(..., ge=0, le=1)
    timestamp: datetime


class TikTokSearchStats(BaseModel):
    video_count_7d: int = Field(..., ge=0)
    avg_views: float = Field(..., ge=0)
    avg_likes: float = Field(..., ge=0)
    avg_comments: float = Field(..., ge=0)
    saturation_tier: Literal['fresh', 'moderate', 'saturated']


# Suggestion
class SuggestionBase(BaseModel):
    keyword: str
    status: str = 'pending'
    final_score: float
    component_scores: ComponentScores


class Suggestion(SuggestionBase):
    id: str
    suggested_by: List[SuggestedByEntry]
    tiktok_status: Optional[str] = None
    tiktok_count_at_suggest: Optional[int] = None
    tiktok_stats: Optional[TikTokSearchStats] = None
    tiktok_checked_at: Optional[datetime] = None
    created_at: datetime
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    reject_note: Optional[str] = None
    reported_at: Optional[datetime] = None
    actual_views: Optional[int] = None
    actual_likes: Optional[int] = None
    actual_comments: Optional[int] = None
    actual_shares: Optional[int] = None
    outcome: Optional[str] = None
    last_learned_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SuggestionListResponse(BaseModel):
    items: List[Suggestion]
    total: int
    limit: int
    offset: int


# Bulk operations
class BulkApproveRequest(BaseModel):
    keyword_ids: List[str] = Field(..., min_items=1, max_items=100)


class BulkApproveResponse(BaseModel):
    approved_count: int
    approved_keywords: List[str]
    cascade_job_ids: List[str] = []


class BulkRejectRequest(BaseModel):
    keyword_ids: List[str] = Field(..., min_items=1)
    reason: str  # 'too_broad' | 'too_competitive' | 'off_topic' | 'poor_quality' | 'other'
    note: Optional[str] = None
    per_item: Optional[Dict[str, Dict[str, str]]] = None


class BulkRejectResponse(BaseModel):
    rejected_count: int
    learning_triggered: bool


# Report
class ReportRequest(BaseModel):
    actual_views: int = Field(..., ge=0)
    actual_likes: int = Field(..., ge=0)
    actual_comments: int = Field(0, ge=0)
    actual_shares: int = Field(0, ge=0)
    outcome: str  # 'success' | 'neutral' | 'failure'
    tiktok_video_url: Optional[str] = None

    @validator('actual_views')
    def check_views(cls, v):
        if v == 0:
            raise ValueError('Views cannot be zero')
        return v


class ReportResponse(BaseModel):
    reported: bool
    engagement_rate: float
    warning: Optional[str] = None


# Improve trigger
class ImproveRequest(BaseModel):
    keyword_id: str
    force: bool = False


class WeightAdjustment(BaseModel):
    factor: str
    old_value: float
    new_value: float
    reason: str
    confidence: float = Field(..., ge=0, le=1)


class ImproveResponse(BaseModel):
    message: str
    new_keywords_generated: int
    new_keywords: List[str]
    weight_adjustments: Optional[List[WeightAdjustment]] = None


# Experiments
class ExperimentCreate(BaseModel):
    keyword: str
    suggestion_source: str  # 'agent_suggested' | 'user_manual'
    channel_id: Optional[str] = None
    channel_subscribers: Optional[int] = Field(None, ge=0)
    creator_avg_views: Optional[int] = Field(None, ge=0)
    agent_suggested_score: Optional[int] = Field(None, ge=0, le=100)
    predicted_score: int = Field(0, ge=0, le=100)
    prediction_reasoning: Optional[str] = None


class ExperimentReportRequest(BaseModel):
    actual_views: Optional[int] = Field(None, ge=0)
    actual_engagement: Optional[float] = Field(None, ge=0)
    actual_retention: Optional[float] = Field(None, ge=0)
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    user_comments: Optional[str] = None
    outcome_type: Optional[str] = None
    accuracy: Optional[float] = None
    reported_at: Optional[datetime] = None
    test_status: Optional[str] = None


class Experiment(BaseModel):
    id: str
    keyword: str
    channel_id: Optional[str] = None
    channel_subscribers: Optional[int] = None
    creator_avg_views: Optional[int] = None
    views_vs_baseline: Optional[float] = None
    suggestion_source: str
    agent_suggested_score: Optional[int] = None
    predicted_score: int
    prediction_reasoning: Optional[str] = None
    actual_views: Optional[int] = None
    actual_engagement: Optional[float] = None
    actual_retention: Optional[float] = None
    test_status: str
    user_rating: Optional[int] = None
    user_comments: Optional[str] = None
    accuracy: Optional[float] = None
    outcome_type: Optional[str] = None
    reported_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ExperimentListResponse(BaseModel):
    items: List[Experiment]
    total: int


# Scan
class ScanRunRequest(BaseModel):
    channel_ids: Optional[List[str]] = None
    force: bool = False


class ScanRunResponse(BaseModel):
    job_id: str
    status: str  # 'started' | 'queued'
    estimated_duration_seconds: int = 300


class ScanProgressResponse(BaseModel):
    job_id: str
    status: str  # 'running' | 'completed' | 'failed'
    progress: Dict[str, Any]
    error: Optional[str] = None


# Channels
class Channel(BaseModel):
    id: str
    channel_id: str
    name: Optional[str] = None
    scan_enabled: bool
    last_scan_at: Optional[datetime] = None
    video_count: int = 0
    suggestion_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class ChannelListResponse(BaseModel):
    items: List[Channel]
    total: int


class AddChannelRequest(BaseModel):
    channel_id: str
    scan_enabled: bool = True


class AddChannelResponse(BaseModel):
    id: str
    channel_id: str
    name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: Optional[int] = None


class SuggestionChannelLink(BaseModel):
    channel_id: str
    youtube_channel_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: Optional[int] = None
    discovery_score: float
    linked_at: datetime


class SuggestionChannelListResponse(BaseModel):
    items: List[SuggestionChannelLink]
    total: int


class CascadeJobResponse(BaseModel):
    id: str
    suggestion_id: str
    keyword: str
    status: str
    channels_discovered: int
    channels_subscribed: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# Learning
class RejectionPattern(BaseModel):
    reason: str
    frequency: int
    common_characteristics: Dict[str, Any]
    suggested_action: str


class SuccessPattern(BaseModel):
    keyword_example: str
    avg_views: int
    avg_engagement_rate: float
    common_characteristics: Dict[str, Any]
    replication_strategy: str


class FilterUpdate(BaseModel):
    parameter: str
    old_value: float
    new_value: float
    reason: str


class LearningInsightsResponse(BaseModel):
    timestamp: datetime
    rejection_patterns: Optional[List[RejectionPattern]] = None
    success_patterns: Optional[List[SuccessPattern]] = None
    weight_adjustments: Optional[List[WeightAdjustment]] = None
    filter_updates: Optional[List[FilterUpdate]] = None
    new_keywords_generated: int = 0
    summary_metrics: Optional[Dict[str, Any]] = None


class LearningCycleResponse(BaseModel):
    message: str
    report_id: str
    adjustments_made: int
    new_keywords_generated: int


# Settings
class ScoringWeights(BaseModel):
    relevance: float = 0.30
    specificity: float = 0.25
    saturation: float = 0.25
    trend: float = 0.10
    video_performance: float = 0.10


class NicheDefinition(BaseModel):
    topics: List[str] = []
    preferred_language: str = 'both'  # 'vi' | 'en' | 'both'
    target_audience: Optional[str] = None


class LLMConfig(BaseModel):
    model: str = 'gpt-4o'
    temperature: float = 0.7
    api_key_set: bool = False


class TikTokConfig(BaseModel):
    api_key_set: bool = False
    check_enabled: bool = True


class SettingsResponse(BaseModel):
    weights: ScoringWeights
    filters: Dict[str, Any]
    niche: NicheDefinition
    llm: LLMConfig
    tiktok: TikTokConfig


class UpdateSettingsRequest(BaseModel):
    weights: Optional[ScoringWeights] = None
    filters: Optional[Dict[str, Any]] = None
    niche: Optional[NicheDefinition] = None
    llm: Optional[LLMConfig] = None
    tiktok: Optional[TikTokConfig] = None


# Error response
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: ErrorDetail
