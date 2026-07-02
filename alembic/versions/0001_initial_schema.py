"""Initial schema — suggestions, learning_events, learning_reports, channels, settings, scan_jobs

Revision ID: 0001
Revises:
Create Date: 2026-07-01 15:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # suggestions
    op.create_table(
        'suggestions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('keyword', sa.String(255), nullable=False, unique=True),
        sa.Column('suggested_by', postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column('final_score', sa.Float, nullable=False),
        sa.Column('component_scores', postgresql.JSONB, nullable=False),
        sa.Column('tiktok_status', sa.String(50), nullable=True),
        sa.Column('tiktok_count_at_suggest', sa.Integer, nullable=True),
        sa.Column('tiktok_checked_at', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('reject_reason', sa.String(50), nullable=True),
        sa.Column('reject_note', sa.Text, nullable=True),
        sa.Column('rejected_at', sa.DateTime, nullable=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('reported_at', sa.DateTime, nullable=True),
        sa.Column('actual_views', sa.Integer, nullable=True),
        sa.Column('actual_likes', sa.Integer, nullable=True),
        sa.Column('actual_comments', sa.Integer, nullable=True),
        sa.Column('actual_shares', sa.Integer, nullable=True),
        sa.Column('outcome', sa.String(50), nullable=True),
        sa.Column('last_learned_at', sa.DateTime, nullable=True),
        sa.Column('learn_weight', sa.Float, nullable=True),
    )
    op.create_index('idx_suggestions_status', 'suggestions', ['status'])
    op.create_index('idx_suggestions_keyword', 'suggestions', ['keyword'])
    op.create_index('idx_suggestions_created_at', 'suggestions', ['created_at'])
    op.create_index('idx_suggestions_status_created', 'suggestions', ['status', 'created_at'])

    # learning_events
    op.create_table(
        'learning_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('keyword', sa.String(255), nullable=False),
        sa.Column('reason', sa.String(50), nullable=True),
        sa.Column('note', sa.Text, nullable=True),
        sa.Column('outcome', sa.String(50), nullable=True),
        sa.Column('predicted_score', sa.Float, nullable=True),
        sa.Column('actual_views', sa.Integer, nullable=True),
        sa.Column('actual_engagement_rate', sa.Float, nullable=True),
        sa.Column('scores', postgresql.JSONB, nullable=True),
        sa.Column('final_score', sa.Float, nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('suggestion_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suggestions.id', ondelete='CASCADE'), nullable=True),
    )
    op.create_index('idx_learning_events_type', 'learning_events', ['type'])
    op.create_index('idx_learning_events_timestamp', 'learning_events', ['timestamp'])
    op.create_index('idx_learning_events_type_timestamp', 'learning_events', ['type', 'timestamp'])

    # learning_reports
    op.create_table(
        'learning_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('timestamp', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('rejection_patterns', postgresql.JSONB, nullable=True),
        sa.Column('success_patterns', postgresql.JSONB, nullable=True),
        sa.Column('weight_adjustments', postgresql.JSONB, nullable=True),
        sa.Column('filter_updates', postgresql.JSONB, nullable=True),
        sa.Column('new_keywords_generated', sa.Integer, nullable=True),
        sa.Column('total_rejections', sa.Integer, nullable=True),
        sa.Column('total_reports', sa.Integer, nullable=True),
        sa.Column('avg_prediction_error', sa.Float, nullable=True),
    )
    op.create_index('idx_learning_reports_timestamp', 'learning_reports', ['timestamp'])

    # channels
    op.create_table(
        'channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('channel_id', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('subscriber_count', sa.Integer, nullable=True),
        sa.Column('scan_enabled', sa.Boolean, server_default=sa.text('true')),
        sa.Column('last_scan_at', sa.DateTime, nullable=True),
        sa.Column('last_video_count', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # settings
    op.create_table(
        'settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('weight_relevance', sa.Float, server_default='0.30'),
        sa.Column('weight_specificity', sa.Float, server_default='0.25'),
        sa.Column('weight_saturation', sa.Float, server_default='0.25'),
        sa.Column('weight_trend', sa.Float, server_default='0.10'),
        sa.Column('weight_video_performance', sa.Float, server_default='0.10'),
        sa.Column('min_score_threshold', sa.Float, server_default='0.4'),
        sa.Column('min_specificity', sa.Float, server_default='0.4'),
        sa.Column('min_saturation', sa.Float, server_default='0.3'),
        sa.Column('max_suggestions_per_video', sa.Integer, server_default='20'),
        sa.Column('niche_topics', postgresql.JSONB, server_default=sa.text("'[]'")),
        sa.Column('niche_preferred_language', sa.String(50), server_default='both'),
        sa.Column('niche_target_audience', sa.String(255), nullable=True),
        sa.Column('llm_model', sa.String(100), server_default='gpt-4o'),
        sa.Column('llm_temperature', sa.Float, server_default='0.7'),
        sa.Column('llm_api_key', sa.String(500), nullable=True),
        sa.Column('tiktok_api_key', sa.String(500), nullable=True),
        sa.Column('tiktok_check_enabled', sa.Boolean, server_default=sa.text('true')),
        sa.Column('scheduler_enabled', sa.Boolean, server_default=sa.text('true')),
        sa.Column('scheduler_daily_time', sa.String(50), server_default='09:00'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # scan_jobs
    op.create_table(
        'scan_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('status', sa.String(50), server_default='started'),
        sa.Column('channels_total', sa.Integer, server_default='0'),
        sa.Column('channels_processed', sa.Integer, server_default='0'),
        sa.Column('videos_processed', sa.Integer, server_default='0'),
        sa.Column('suggestions_generated', sa.Integer, server_default='0'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )
    op.create_index('idx_scan_jobs_status', 'scan_jobs', ['status'])


def downgrade() -> None:
    op.drop_table('scan_jobs')
    op.drop_table('settings')
    op.drop_table('channels')
    op.drop_table('learning_reports')
    op.drop_table('learning_events')
    op.drop_table('suggestions')
