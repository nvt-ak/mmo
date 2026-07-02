"""merge jobs and final videos

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-02 14:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_video_assets_review_status", "video_assets", type_="check")
    op.create_check_constraint(
        "ck_video_assets_review_status",
        "video_assets",
        "review_status IN ('pending', 'in_pool', 'skipped', 'merged')",
    )

    op.create_table(
        "merge_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column(
            "video_a_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("video_assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "video_b_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("video_assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "suggestion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suggestions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "job_type IN ('manual', 'random')",
            name="ck_merge_jobs_job_type",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'done', 'failed')",
            name="ck_merge_jobs_status",
        ),
    )
    op.create_index("idx_merge_jobs_status", "merge_jobs", ["status"])
    op.create_index("idx_merge_jobs_created", "merge_jobs", ["created_at"])

    op.create_table(
        "final_videos",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "merge_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("merge_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("keyword", sa.String(500), nullable=True),
        sa.Column(
            "suggestion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suggestions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_video_ids", postgresql.JSONB(), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_final_videos_created", "final_videos", ["created_at"])
    op.create_index("idx_final_videos_suggestion", "final_videos", ["suggestion_id"])


def downgrade() -> None:
    op.drop_index("idx_final_videos_suggestion", table_name="final_videos")
    op.drop_index("idx_final_videos_created", table_name="final_videos")
    op.drop_table("final_videos")
    op.drop_index("idx_merge_jobs_created", table_name="merge_jobs")
    op.drop_index("idx_merge_jobs_status", table_name="merge_jobs")
    op.drop_table("merge_jobs")

    op.drop_constraint("ck_video_assets_review_status", "video_assets", type_="check")
    op.create_check_constraint(
        "ck_video_assets_review_status",
        "video_assets",
        "review_status IN ('pending', 'in_pool', 'skipped')",
    )
