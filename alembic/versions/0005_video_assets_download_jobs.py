"""video assets and download jobs

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-02 12:05:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_assets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("youtube_video_id", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "channel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "suggestion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suggestions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("view_count", sa.Integer, nullable=True, server_default="0"),
        sa.Column("duration_sec", sa.Integer, nullable=True, server_default="0"),
        sa.Column("youtube_url", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="downloaded"),
        sa.Column(
            "review_status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("downloaded_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.CheckConstraint(
            "status IN ('downloaded', 'failed', 'queued')",
            name="ck_video_assets_status",
        ),
        sa.CheckConstraint(
            "review_status IN ('pending', 'in_pool', 'skipped')",
            name="ck_video_assets_review_status",
        ),
    )
    op.create_index("idx_video_assets_youtube_video", "video_assets", ["youtube_video_id"])
    op.create_index("idx_video_assets_channel", "video_assets", ["channel_id"])
    op.create_index("idx_video_assets_suggestion", "video_assets", ["suggestion_id"])
    op.create_index("idx_video_assets_status", "video_assets", ["status"])
    op.create_index("idx_video_assets_review_status", "video_assets", ["review_status"])
    op.create_index("idx_video_assets_downloaded_at", "video_assets", ["downloaded_at"])
    op.create_index(
        "idx_video_assets_suggestion_review",
        "video_assets",
        ["suggestion_id", "review_status"],
    )

    op.create_table(
        "download_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column(
            "suggestion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suggestions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "cascade_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("keyword_cascade_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="started"),
        sa.Column("channels_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("videos_found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("videos_downloaded", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.CheckConstraint(
            "job_type IN ('bulk', 'watcher')",
            name="ck_download_jobs_job_type",
        ),
        sa.CheckConstraint(
            "status IN ('started', 'running', 'completed', 'failed')",
            name="ck_download_jobs_status",
        ),
    )
    op.create_index("idx_download_jobs_job_type", "download_jobs", ["job_type"])
    op.create_index("idx_download_jobs_status", "download_jobs", ["status"])
    op.create_index("idx_download_jobs_suggestion", "download_jobs", ["suggestion_id"])
    op.create_index("idx_download_jobs_cascade", "download_jobs", ["cascade_job_id"])
    op.create_index(
        "idx_download_jobs_type_created",
        "download_jobs",
        ["job_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_download_jobs_type_created", table_name="download_jobs")
    op.drop_index("idx_download_jobs_cascade", table_name="download_jobs")
    op.drop_index("idx_download_jobs_suggestion", table_name="download_jobs")
    op.drop_index("idx_download_jobs_status", table_name="download_jobs")
    op.drop_index("idx_download_jobs_job_type", table_name="download_jobs")
    op.drop_table("download_jobs")

    op.drop_index("idx_video_assets_suggestion_review", table_name="video_assets")
    op.drop_index("idx_video_assets_downloaded_at", table_name="video_assets")
    op.drop_index("idx_video_assets_review_status", table_name="video_assets")
    op.drop_index("idx_video_assets_status", table_name="video_assets")
    op.drop_index("idx_video_assets_suggestion", table_name="video_assets")
    op.drop_index("idx_video_assets_channel", table_name="video_assets")
    op.drop_index("idx_video_assets_youtube_video", table_name="video_assets")
    op.drop_table("video_assets")
