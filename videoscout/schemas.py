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
    keyword_type: str = 'beta'
    discovery_source: Optional[str] = None
    trend_signals: Optional[Dict[str, Any]] = None
    gate_profile: Optional[str] = None
    tiktok_unverified: bool = False
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


# Discovery (R7a)
class DiscoveryRunRequest(BaseModel):
    keyword_type_filter: str = 'both'  # nurture | beta | both
    region_code: str = 'DE'


class DiscoveryRunResponse(BaseModel):
    job_id: str
    status: str
    estimated_duration_seconds: int = 60
    max_keywords: int = 10


class DiscoveryJobResponse(BaseModel):
    id: str
    status: str
    job_type: str
    keyword_type_filter: str
    sources_scanned: int
    keywords_generated: int
    max_keywords: int = 10
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DiscoveryJobListResponse(BaseModel):
    items: List[DiscoveryJobResponse]
    total: int


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


class DownloadJobResponse(BaseModel):
    id: str
    job_type: str
    suggestion_id: Optional[str] = None
    cascade_job_id: Optional[str] = None
    status: str
    channels_total: int
    videos_found: int
    videos_downloaded: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class VideoAsset(BaseModel):
    id: str
    youtube_video_id: str
    channel_id: str
    suggestion_id: Optional[str] = None
    title: str
    view_count: Optional[int] = 0
    duration_sec: Optional[int] = 0
    youtube_url: str
    file_path: str
    status: str
    review_status: str
    downloaded_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class VideoAssetListResponse(BaseModel):
    items: List[VideoAsset]
    total: int
    limit: int


class BatchVideoAsset(VideoAsset):
    channel_name: Optional[str] = None
    keyword: Optional[str] = None
    thumbnail_url: Optional[str] = None


class BatchListResponse(BaseModel):
    items: List[BatchVideoAsset]
    total: int
    limit: int
    pending_count: int
    in_pool_count: int
    skipped_count: int


class VideoReviewAction(BaseModel):
    action: str = Field(..., pattern="^(keep|skip)$")


class BulkVideoReviewRequest(BaseModel):
    video_ids: List[str] = Field(..., min_length=1, max_length=200)
    action: str = Field(..., pattern="^(keep|skip)$")


class VideoReviewResponse(BaseModel):
    id: str
    review_status: str


class BulkVideoReviewResponse(BaseModel):
    updated_count: int
    review_status: str


class MergePoolVideo(BatchVideoAsset):
    pass


class MergePoolResponse(BaseModel):
    items: List[MergePoolVideo]
    total: int
    limit: int


class ManualMergeRequest(BaseModel):
    video_ids: List[str] = Field(..., min_length=2, max_length=2)


class RandomMergeRequest(BaseModel):
    suggestion_id: Optional[str] = None


class MergeJobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    video_a_id: Optional[str] = None
    video_b_id: Optional[str] = None
    suggestion_id: Optional[str] = None
    error_message: Optional[str] = None
    final_video_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class MergeEnqueueResponse(BaseModel):
    job_id: str
    video_ids: List[str]
    status: str


class FinalVideo(BaseModel):
    id: str
    merge_job_id: Optional[str] = None
    file_path: str
    keyword: Optional[str] = None
    suggestion_id: Optional[str] = None
    source_video_ids: List[str]
    duration_sec: Optional[int] = None
    pool_type: Optional[str] = None
    pool_status: Optional[str] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class FinalVideoListResponse(BaseModel):
    items: List[FinalVideo]
    total: int
    limit: int


# Profiles + typed pools (R7b)
class TikTokProfileCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=255)
    handle: str = Field(..., min_length=1, max_length=255)
    stage: str = Field(default="nurture")
    notes: Optional[str] = None


class TikTokProfileUpdate(BaseModel):
    label: Optional[str] = None
    handle: Optional[str] = None
    beta_eligible: Optional[bool] = None
    notes: Optional[str] = None


class TikTokProfile(BaseModel):
    id: str
    label: str
    handle: str
    stage: str
    beta_eligible: bool
    promoted_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime


class TikTokProfileListResponse(BaseModel):
    items: List[TikTokProfile]
    total: int


class PoolMediaItem(BaseModel):
    id: str
    kind: str  # video_asset | final_video
    pool_type: str
    pool_status: str
    title: str
    keyword: Optional[str] = None
    file_path: str
    duration_sec: Optional[int] = None
    created_at: datetime


class PoolListResponse(BaseModel):
    items: List[PoolMediaItem]
    total: int
    limit: int


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
    proposals_created: int = 0


class WeightProposal(BaseModel):
    id: str
    factor: str
    old_value: float
    new_value: float
    reason: Optional[str] = None
    confidence: float
    status: str
    keyword_type: str = "beta"
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WeightProposalListResponse(BaseModel):
    items: List[WeightProposal]
    total: int


class WeightProposalActionResponse(BaseModel):
    message: str
    proposal: WeightProposal


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
    base_url: str = 'http://localhost:20128/v1'
    api_key_set: bool = False


class UpdateLLMConfig(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class LLMModelsRequest(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class LLMModelsResponse(BaseModel):
    models: List[str]


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
    llm: Optional[UpdateLLMConfig] = None
    tiktok: Optional[TikTokConfig] = None


# Error response
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: ErrorDetail
