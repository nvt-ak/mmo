"""Add settings.discovery_region_codes JSONB (US-079)

Revision ID: 0019
Revises: 0018
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "settings", "discovery_region_codes"):
        op.add_column(
            "settings",
            sa.Column(
                "discovery_region_codes",
                JSONB(),
                nullable=False,
                server_default=sa.text("'[\"US\"]'::jsonb"),
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "settings", "discovery_region_codes"):
        op.drop_column("settings", "discovery_region_codes")
