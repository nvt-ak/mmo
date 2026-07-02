"""link performance reports to final videos

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-02 16:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "performance_reports",
        sa.Column(
            "final_video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("final_videos.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_performance_reports_final_video",
        "performance_reports",
        ["final_video_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_performance_reports_final_video", table_name="performance_reports")
    op.drop_column("performance_reports", "final_video_id")
