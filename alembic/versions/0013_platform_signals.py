"""suggestions.platform_signals JSONB (US-060)

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-02 24:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "suggestions", "platform_signals"):
        op.add_column("suggestions", sa.Column("platform_signals", JSONB, nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "suggestions", "platform_signals"):
        op.drop_column("suggestions", "platform_signals")
