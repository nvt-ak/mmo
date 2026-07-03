"""suggestions.trend_evidence JSONB (US-062)

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-03 16:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "suggestions", "trend_evidence"):
        op.add_column("suggestions", sa.Column("trend_evidence", JSONB, nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "suggestions", "trend_evidence"):
        op.drop_column("suggestions", "trend_evidence")
