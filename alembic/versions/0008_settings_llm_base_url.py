"""add llm_base_url to settings

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-02 18:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "settings",
        sa.Column("llm_base_url", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("settings", "llm_base_url")
