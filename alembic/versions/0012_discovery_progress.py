"""discovery_jobs progress columns (US-059)

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-02 23:30:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if not inspect(conn).has_table("discovery_jobs"):
        return

    if not _has_column(conn, "discovery_jobs", "videos_scanned"):
        op.add_column(
            "discovery_jobs",
            sa.Column("videos_scanned", sa.Integer(), nullable=False, server_default="0"),
        )
    if not _has_column(conn, "discovery_jobs", "candidates_checked"):
        op.add_column(
            "discovery_jobs",
            sa.Column("candidates_checked", sa.Integer(), nullable=False, server_default="0"),
        )
    if not _has_column(conn, "discovery_jobs", "progress_phase"):
        op.add_column(
            "discovery_jobs",
            sa.Column(
                "progress_phase",
                sa.String(30),
                nullable=False,
                server_default="starting",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if not inspect(conn).has_table("discovery_jobs"):
        return

    for col in ("progress_phase", "candidates_checked", "videos_scanned"):
        if _has_column(conn, "discovery_jobs", col):
            op.drop_column("discovery_jobs", col)
