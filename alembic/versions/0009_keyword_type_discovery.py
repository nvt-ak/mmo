"""keyword_type and discovery_jobs for dual-track R7a

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-02 20:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _has_table(conn, name: str) -> bool:
    return name in inspect(conn).get_table_names()


def _has_column(conn, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(conn).get_columns(table)}


def _has_index(conn, table: str, index_name: str) -> bool:
    return index_name in {idx["name"] for idx in inspect(conn).get_indexes(table)}


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, "suggestions", "keyword_type"):
        op.add_column(
            "suggestions",
            sa.Column("keyword_type", sa.String(20), nullable=False, server_default="beta"),
        )
    if not _has_column(conn, "suggestions", "discovery_source"):
        op.add_column(
            "suggestions",
            sa.Column("discovery_source", sa.String(50), nullable=True),
        )
    if not _has_column(conn, "suggestions", "trend_signals"):
        op.add_column(
            "suggestions",
            sa.Column("trend_signals", JSONB, nullable=True),
        )
    if not _has_column(conn, "suggestions", "gate_profile"):
        op.add_column(
            "suggestions",
            sa.Column("gate_profile", sa.String(20), nullable=True),
        )
    if not _has_column(conn, "suggestions", "tiktok_unverified"):
        op.add_column(
            "suggestions",
            sa.Column("tiktok_unverified", sa.Boolean(), nullable=False, server_default="false"),
        )
    if not _has_index(conn, "suggestions", "ix_suggestions_keyword_type"):
        op.create_index("ix_suggestions_keyword_type", "suggestions", ["keyword_type"])

    if not _has_table(conn, "discovery_jobs"):
        op.create_table(
            "discovery_jobs",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("status", sa.String(50), nullable=False, server_default="started"),
            sa.Column("job_type", sa.String(50), nullable=False, server_default="trend_discovery"),
            sa.Column("keyword_type_filter", sa.String(20), nullable=False, server_default="both"),
            sa.Column("sources_scanned", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("keywords_generated", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )
    if _has_table(conn, "discovery_jobs") and not _has_index(conn, "discovery_jobs", "ix_discovery_jobs_status"):
        op.create_index("ix_discovery_jobs_status", "discovery_jobs", ["status"])


def downgrade() -> None:
    conn = op.get_bind()

    if _has_index(conn, "discovery_jobs", "ix_discovery_jobs_status"):
        op.drop_index("ix_discovery_jobs_status", table_name="discovery_jobs")
    if _has_table(conn, "discovery_jobs"):
        op.drop_table("discovery_jobs")
    if _has_index(conn, "suggestions", "ix_suggestions_keyword_type"):
        op.drop_index("ix_suggestions_keyword_type", table_name="suggestions")
    for col in (
        "tiktok_unverified",
        "gate_profile",
        "trend_signals",
        "discovery_source",
        "keyword_type",
    ):
        if _has_column(conn, "suggestions", col):
            op.drop_column("suggestions", col)
