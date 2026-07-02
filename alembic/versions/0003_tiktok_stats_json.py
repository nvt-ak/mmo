"""add tiktok_stats on suggestions

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-02 10:35:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "suggestions",
        sa.Column("tiktok_stats", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("suggestions", "tiktok_stats")
