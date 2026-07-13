"""
SQLAlchemy models for VideoScout hybrid backend.
Maps to PostgreSQL database.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, JSON, Enum, 
    ForeignKey, UniqueConstraint, Index, Boolean, Text, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


class SuggestionModel(Base):
    """
    Suggestion records with full lifecycle tracking.
    Deduplicated by keyword across all sources.
    """
    __tablename__ = 'suggestions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword = Column(String(255), unique=True, nullable=False, index=True)
    
    # Multi-source tracking
    suggested_by = Column(JSONB, nullable=False, default=[])
    # Format: [{"source": "digest_scan|agent_learning|manual", "video_id?": str, "channel_id?": str, "score": float, "timestamp": ISO8601}]
    
    final_score = Column(Float, nullable=False)
    component_scores = Column(JSONB, nullable=False)
    # Format: {"relevance": float, "specificity": float, "saturation": float, "trend": float, "video_performance": float}
    
    # TikTok saturation check (Phase 1: check 1 lần lúc generate)
    tiktok_status = Column(String(50), nullable=True)  # 'low' | 'moderate' | 'saturated'
    tiktok_count_at_suggest = Column(Integer, nullable=True)
    tiktok_stats = Column(JSONB, nullable=True)
    tiktok_checked_at = Column(DateTime, nullable=True)
    
    # Dual-track discovery (R7a)
    keyword_type = Column(String(20), nullable=False, default='beta', index=True)
    discovery_source = Column(String(50), nullable=True)
    trend_signals = Column(JSONB, nullable=True)
    trend_evidence = Column(JSONB, nullable=True)
    platform_signals = Column(JSONB, nullable=True)
    gate_profile = Column(String(20), nullable=True)  # light | full
    tiktok_unverified = Column(Boolean, nullable=False, default=False)
    cluster_id = Column(
        UUID(as_uuid=True),
        ForeignKey("trend_clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Lifecycle
    status = Column(String(50), nullable=False, default='pending', index=True)
    # 'pending' | 'approved' | 'rejected' | 'reported'
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Rejection flow
    reject_reason = Column(String(50), nullable=True)
    # 'too_broad' | 'too_competitive' | 'off_topic' | 'poor_quality' | 'other'
    reject_note = Column(Text, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    # Approval
    approved_at = Column(DateTime, nullable=True)
    
    # Report flow (after user uploads)
    reported_at = Column(DateTime, nullable=True)
    actual_views = Column(Integer, nullable=True)
    actual_likes = Column(Integer, nullable=True)
    actual_comments = Column(Integer, nullable=True)
    actual_shares = Column(Integer, nullable=True)
    outcome = Column(String(50), nullable=True)  # 'success' | 'neutral' | 'failure'
    
    # Learning
    last_learned_at = Column(DateTime, nullable=True)
    learn_weight = Column(Float, nullable=True)
    
    # Relationships
    learning_events = relationship('LearningEventModel', back_populates='suggestion', cascade='all, delete-orphan')
    
    cluster = relationship("TrendClusterModel", back_populates="members")

    __table_args__ = (
        Index('idx_suggestions_status_created', 'status', 'created_at'),
        Index('idx_suggestions_keyword', 'keyword'),
    )


class TrendClusterModel(Base):
    """Near-duplicate keyword grouping from discovery (US-066 / ADR 0014 Phase 2)."""

    __tablename__ = "trend_clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_keyword = Column(String(255), nullable=False, index=True)
    member_keyword_ids = Column(JSONB, nullable=False, default=list)
    member_keywords = Column(JSONB, nullable=False, default=list)
    pipeline_run_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    members = relationship("SuggestionModel", back_populates="cluster")


class LearningEventModel(Base):
    """
    Learning feedback events from rejections and reports.
    """
    __tablename__ = 'learning_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False, index=True)  # 'rejection' | 'report'
    keyword = Column(String(255), nullable=False)
    
    # Rejection fields
    reason = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    
    # Report fields
    outcome = Column(String(50), nullable=True)  # 'success' | 'neutral' | 'failure'
    predicted_score = Column(Float, nullable=True)
    actual_views = Column(Integer, nullable=True)
    actual_engagement_rate = Column(Float, nullable=True)
    
    # Shared
    scores = Column(JSONB, nullable=True)
    final_score = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Foreign key
    suggestion_id = Column(UUID(as_uuid=True), ForeignKey('suggestions.id', ondelete='CASCADE'), nullable=True)
    
    # Relationships
    suggestion = relationship('SuggestionModel', back_populates='learning_events')
    
    __table_args__ = (
        Index('idx_learning_events_type_timestamp', 'type', 'timestamp'),
    )


class LearningReportModel(Base):
    """
    Weekly learning cycle reports and insights.
    """
    __tablename__ = 'learning_reports'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    rejection_patterns = Column(JSONB, nullable=True)  # RejectionPattern[]
    success_patterns = Column(JSONB, nullable=True)    # SuccessPattern[]
    weight_adjustments = Column(JSONB, nullable=True)  # WeightAdjustment[]
    filter_updates = Column(JSONB, nullable=True)      # FilterUpdate[]
    
    new_keywords_generated = Column(Integer, nullable=True)
    
    # Summary metrics
    total_rejections = Column(Integer, nullable=True)
    total_reports = Column(Integer, nullable=True)
    avg_prediction_error = Column(Float, nullable=True)


class WeightProposalModel(Base):
    """Pending human-approved beta scoring weight changes (US-056)."""

    __tablename__ = "weight_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factor = Column(String(50), nullable=False, index=True)
    old_value = Column(Float, nullable=False)
    new_value = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.7)
    status = Column(String(20), nullable=False, default="pending", index=True)
    keyword_type = Column(String(20), nullable=False, default="beta")
    learning_report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("learning_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "factor IN ('relevance', 'specificity', 'saturation')",
            name="ck_weight_proposals_factor",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_weight_proposals_status",
        ),
    )


class ChannelModel(Base):
    """
    YouTube channels being scanned.
    """
    __tablename__ = 'channels'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(String(255), unique=True, nullable=False, index=True)  # YouTube channel ID
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    subscriber_count = Column(Integer, nullable=True)
    
    scan_enabled = Column(Boolean, default=True)
    last_scan_at = Column(DateTime, nullable=True)
    last_video_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SettingsModel(Base):
    """
    User settings and configuration.
    Single row per installation.
    """
    __tablename__ = 'settings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Scoring weights
    weight_relevance = Column(Float, default=0.30)
    weight_specificity = Column(Float, default=0.25)
    weight_saturation = Column(Float, default=0.25)
    weight_trend = Column(Float, default=0.10)
    weight_video_performance = Column(Float, default=0.10)
    
    # Filters
    min_score_threshold = Column(Float, default=0.55)
    min_specificity = Column(Float, default=0.4)
    min_saturation = Column(Float, default=0.3)
    max_suggestions_per_video = Column(Integer, default=20)
    
    # Niche definition
    niche_topics = Column(JSONB, default=[])  # ["topic1", "topic2", ...]
    niche_preferred_language = Column(String(50), default='both')  # 'vi' | 'en' | 'both'
    niche_target_audience = Column(String(255), nullable=True)

    # Runtime LLM scoring rubrics (null = ship default from rubrics/*.md)
    nurture_scoring_rubric = Column(Text, nullable=True)
    beta_scoring_rubric = Column(Text, nullable=True)

    # LLM config
    llm_model = Column(String(100), default='gpt-4o')  # 'gpt-4o' | 'claude-sonnet-4'
    llm_temperature = Column(Float, default=0.7)
    llm_base_url = Column(String(500), nullable=True)
    llm_api_key = Column(String(500), nullable=True)  # Encrypted in production
    
    # TikTok config
    tiktok_api_key = Column(String(500), nullable=True)  # Encrypted in production
    tiktok_check_enabled = Column(Boolean, default=True)
    
    # Scheduler config
    scheduler_enabled = Column(Boolean, default=True)
    scheduler_daily_time = Column(String(50), default='09:00')  # HH:MM format
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class DiscoveryJobModel(Base):
    """Trend discovery job tracking (R7a)."""

    __tablename__ = 'discovery_jobs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(50), default='started', index=True)
    job_type = Column(String(50), nullable=False, default='trend_discovery')
    keyword_type_filter = Column(String(20), nullable=False, default='both')
    sources_scanned = Column(Integer, default=0)
    videos_scanned = Column(Integer, default=0)
    candidates_checked = Column(Integer, default=0)
    progress_phase = Column(String(30), default='starting')
    keywords_generated = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class TikTokProfileModel(Base):
    """TikTok account registry for nurture/beta distribution (R7b)."""

    __tablename__ = 'tiktok_profiles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label = Column(String(255), nullable=False)
    handle = Column(String(255), nullable=False, unique=True, index=True)
    stage = Column(String(20), nullable=False, default='nurture', index=True)
    beta_eligible = Column(Boolean, nullable=False, default=False)
    promoted_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ScanJobModel(Base):
    """
    Scan job tracking for background tasks.
    """
    __tablename__ = 'scan_jobs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(50), default='started', index=True)  # 'started' | 'running' | 'completed' | 'failed'
    
    channels_total = Column(Integer, default=0)
    channels_processed = Column(Integer, default=0)
    videos_processed = Column(Integer, default=0)
    suggestions_generated = Column(Integer, default=0)
    
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class KeywordExperimentModel(Base):
    """Tracked experiment for validating keyword performance."""

    __tablename__ = "keyword_experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword = Column(String(255), nullable=False, index=True)
    channel_id = Column(
        String(255),
        ForeignKey("channels.channel_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    channel_subscribers = Column(Integer, nullable=True)
    creator_avg_views = Column(Integer, nullable=True)
    views_vs_baseline = Column(Float, nullable=True)

    suggestion_source = Column(String(50), nullable=False)
    agent_suggested_score = Column(Integer, nullable=True)

    predicted_score = Column(Integer, nullable=False, default=0)
    prediction_reasoning = Column(Text, nullable=True)
    predicted_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    actual_views = Column(Integer, nullable=True)
    actual_engagement = Column(Float, nullable=True)
    actual_retention = Column(Float, nullable=True)
    test_status = Column(String(50), nullable=False, default="in_progress", index=True)

    user_rating = Column(Integer, nullable=True)
    user_comments = Column(Text, nullable=True)

    accuracy = Column(Float, nullable=True)
    outcome_type = Column(String(50), nullable=True)

    reported_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        CheckConstraint(
            "suggestion_source IN ('agent_suggested', 'user_manual')",
            name="ck_keyword_experiments_suggestion_source",
        ),
        CheckConstraint(
            "test_status IN ('in_progress', 'success', 'failed', 'partial')",
            name="ck_keyword_experiments_test_status",
        ),
        CheckConstraint(
            "user_rating BETWEEN 1 AND 5",
            name="ck_keyword_experiments_user_rating",
        ),
        CheckConstraint(
            "outcome_type IN ('true_positive', 'false_positive', 'true_negative', 'false_negative')",
            name="ck_keyword_experiments_outcome_type",
        ),
    )


class KeywordPatternModel(Base):
    """Persisted learning pattern extracted from experiments."""

    __tablename__ = "keyword_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pattern_type = Column(String(100), nullable=False)
    keyword_trait = Column(String(255), nullable=False)
    outcome_type = Column(String(50), nullable=False)

    insight = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True)
    example_keywords = Column(Text, nullable=True)

    occurrence_count = Column(Integer, nullable=False, default=1)
    avg_predicted = Column(Float, nullable=True)
    avg_actual = Column(Float, nullable=True)
    confidence = Column(Float, nullable=False, default=0.5)
    suggested_adjustment = Column(JSONB, nullable=True)
    experiment_ids = Column(JSONB, nullable=True, default=list)

    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PerformanceReportModel(Base):
    """Reported keyword outcomes used for later analysis."""

    __tablename__ = "performance_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword = Column(String(255), nullable=False, index=True)
    suggestion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suggestions.id", ondelete="SET NULL"),
        nullable=True,
    )
    final_video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("final_videos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    actual_views = Column(Integer, nullable=False)
    actual_likes = Column(Integer, nullable=True)
    actual_comments = Column(Integer, nullable=True)
    actual_shares = Column(Integer, nullable=True)
    followers_gained = Column(Integer, nullable=True)
    engagement_rate = Column(Float, nullable=True)
    outcome = Column(String(50), nullable=True)
    reported_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    notes = Column(Text, nullable=True)

    suggestion = relationship("SuggestionModel")

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('success', 'neutral', 'failure')",
            name="ck_performance_reports_outcome",
        ),
    )


class ChannelKeywordLinkModel(Base):
    """Link approved keyword suggestions to discovered channels."""

    __tablename__ = "channel_keyword_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suggestion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suggestions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    youtube_channel_id = Column(String(255), nullable=False, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    discovery_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "suggestion_id",
            "channel_id",
            name="uq_channel_keyword_links_suggestion_channel",
        ),
        Index(
            "idx_channel_keyword_links_suggestion_created",
            "suggestion_id",
            "created_at",
        ),
    )


class KeywordCascadeJobModel(Base):
    """Background keyword cascade job status tracking."""

    __tablename__ = "keyword_cascade_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suggestion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suggestions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    keyword = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="started", index=True)

    channels_discovered = Column(Integer, nullable=False, default=0)
    channels_subscribed = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('started', 'running', 'completed', 'completed_no_source', 'failed')",
            name="ck_keyword_cascade_jobs_status",
        ),
        Index(
            "idx_keyword_cascade_jobs_suggestion_created",
            "suggestion_id",
            "created_at",
        ),
    )


class VideoAssetModel(Base):
    """Downloaded video asset linked to channel and optional suggestion."""

    __tablename__ = "video_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    youtube_video_id = Column(String(255), nullable=False, unique=True, index=True)
    channel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    suggestion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suggestions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(500), nullable=False)
    view_count = Column(Integer, nullable=True, default=0)
    duration_sec = Column(Integer, nullable=True, default=0)
    youtube_url = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    status = Column(String(50), nullable=False, default="downloaded", index=True)
    review_status = Column(String(50), nullable=False, default="pending", index=True)
    pool_type = Column(String(20), nullable=False, default="beta", index=True)
    pool_status = Column(String(30), nullable=False, default="pending_review", index=True)
    downloaded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    metadata_json = Column("metadata", JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('downloaded', 'failed', 'queued')",
            name="ck_video_assets_status",
        ),
        CheckConstraint(
            "review_status IN ('pending', 'in_pool', 'skipped', 'merged')",
            name="ck_video_assets_review_status",
        ),
        Index(
            "idx_video_assets_suggestion_review",
            "suggestion_id",
            "review_status",
        ),
    )


class DownloadJobModel(Base):
    """Bulk/watcher ingestion job status tracking."""

    __tablename__ = "download_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(50), nullable=False, index=True)
    suggestion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suggestions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cascade_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("keyword_cascade_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(50), nullable=False, default="started", index=True)
    channels_total = Column(Integer, nullable=False, default=0)
    videos_found = Column(Integer, nullable=False, default=0)
    videos_downloaded = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "job_type IN ('bulk', 'watcher')",
            name="ck_download_jobs_job_type",
        ),
        CheckConstraint(
            "status IN ('started', 'running', 'completed', 'failed')",
            name="ck_download_jobs_status",
        ),
        Index(
            "idx_download_jobs_type_created",
            "job_type",
            "created_at",
        ),
    )


class MergeJobModel(Base):
    """Merge two pool videos into a final output."""

    __tablename__ = "merge_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="queued", index=True)
    video_a_id = Column(
        UUID(as_uuid=True),
        ForeignKey("video_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    video_b_id = Column(
        UUID(as_uuid=True),
        ForeignKey("video_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    suggestion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suggestions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "job_type IN ('manual', 'random')",
            name="ck_merge_jobs_job_type",
        ),
        CheckConstraint(
            "status IN ('queued', 'processing', 'done', 'failed')",
            name="ck_merge_jobs_status",
        ),
    )


class FinalVideoModel(Base):
    """Registry of merged output files in data/finals/."""

    __tablename__ = "final_videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merge_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("merge_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_path = Column(String(1000), nullable=False)
    keyword = Column(String(500), nullable=True)
    suggestion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suggestions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_video_ids = Column(JSONB, nullable=False)
    duration_sec = Column(Integer, nullable=True)
    pool_type = Column(String(20), nullable=False, default="beta", index=True)
    pool_status = Column(String(30), nullable=False, default="pending_review", index=True)
    metadata_json = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
