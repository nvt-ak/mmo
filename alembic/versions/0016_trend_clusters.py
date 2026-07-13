"""trend_clusters table + suggestions.cluster_id (US-066)

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-13 10:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def _has_table(conn, table: str) -> bool:
    return table in inspect(conn).get_table_names()


def _has_column(conn, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "trend_clusters"):
        op.create_table(
            "trend_clusters",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("canonical_keyword", sa.String(255), nullable=False, index=True),
            sa.Column("member_keyword_ids", JSONB, nullable=False, server_default="[]"),
            sa.Column("member_keywords", JSONB, nullable=False, server_default="[]"),
            sa.Column("pipeline_run_id", UUID(as_uuid=True), nullable=True, index=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        )

    if not _has_column(conn, "suggestions", "cluster_id"):
        op.add_column(
            "suggestions",
            sa.Column(
                "cluster_id",
                UUID(as_uuid=True),
                sa.ForeignKey("trend_clusters.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "suggestions", "cluster_id"):
        op.drop_column("suggestions", "cluster_id")
    if _has_table(conn, "trend_clusters"):
        op.drop_table("trend_clusters")
