"""channel keyword links and cascade jobs

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-02 11:05:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "channel_keyword_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "suggestion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suggestions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("youtube_channel_id", sa.String(255), nullable=False),
        sa.Column("keyword", sa.String(255), nullable=False),
        sa.Column("discovery_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "suggestion_id",
            "channel_id",
            name="uq_channel_keyword_links_suggestion_channel",
        ),
    )
    op.create_index(
        "idx_channel_keyword_links_suggestion_created",
        "channel_keyword_links",
        ["suggestion_id", "created_at"],
    )
    op.create_index(
        "idx_channel_keyword_links_suggestion",
        "channel_keyword_links",
        ["suggestion_id"],
    )
    op.create_index(
        "idx_channel_keyword_links_channel",
        "channel_keyword_links",
        ["channel_id"],
    )
    op.create_index(
        "idx_channel_keyword_links_youtube_channel",
        "channel_keyword_links",
        ["youtube_channel_id"],
    )
    op.create_index(
        "idx_channel_keyword_links_keyword",
        "channel_keyword_links",
        ["keyword"],
    )

    op.create_table(
        "keyword_cascade_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "suggestion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suggestions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("keyword", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="started"),
        sa.Column("channels_discovered", sa.Integer, nullable=False, server_default="0"),
        sa.Column("channels_subscribed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.CheckConstraint(
            "status IN ('started', 'running', 'completed', 'failed')",
            name="ck_keyword_cascade_jobs_status",
        ),
    )
    op.create_index(
        "idx_keyword_cascade_jobs_status",
        "keyword_cascade_jobs",
        ["status"],
    )
    op.create_index(
        "idx_keyword_cascade_jobs_suggestion",
        "keyword_cascade_jobs",
        ["suggestion_id"],
    )
    op.create_index(
        "idx_keyword_cascade_jobs_suggestion_created",
        "keyword_cascade_jobs",
        ["suggestion_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_keyword_cascade_jobs_suggestion_created",
        table_name="keyword_cascade_jobs",
    )
    op.drop_index("idx_keyword_cascade_jobs_suggestion", table_name="keyword_cascade_jobs")
    op.drop_index("idx_keyword_cascade_jobs_status", table_name="keyword_cascade_jobs")
    op.drop_table("keyword_cascade_jobs")

    op.drop_index(
        "idx_channel_keyword_links_keyword",
        table_name="channel_keyword_links",
    )
    op.drop_index(
        "idx_channel_keyword_links_youtube_channel",
        table_name="channel_keyword_links",
    )
    op.drop_index(
        "idx_channel_keyword_links_channel",
        table_name="channel_keyword_links",
    )
    op.drop_index(
        "idx_channel_keyword_links_suggestion",
        table_name="channel_keyword_links",
    )
    op.drop_index(
        "idx_channel_keyword_links_suggestion_created",
        table_name="channel_keyword_links",
    )
    op.drop_table("channel_keyword_links")
