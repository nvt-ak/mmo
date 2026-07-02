"""tiktok_profiles and typed media pools (R7b)

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-02 22:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def _has_table(conn, name: str) -> bool:
    return name in inspect(conn).get_table_names()


def _has_column(conn, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, "tiktok_profiles"):
        op.create_table(
            "tiktok_profiles",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("label", sa.String(255), nullable=False),
            sa.Column("handle", sa.String(255), nullable=False),
            sa.Column("stage", sa.String(20), nullable=False, server_default="nurture"),
            sa.Column("beta_eligible", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("promoted_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_tiktok_profiles_stage", "tiktok_profiles", ["stage"])
        op.create_index("ix_tiktok_profiles_handle", "tiktok_profiles", ["handle"], unique=True)

    for table in ("video_assets", "final_videos"):
        if not _has_column(conn, table, "pool_type"):
            op.add_column(
                table,
                sa.Column("pool_type", sa.String(20), nullable=False, server_default="beta"),
            )
        if not _has_column(conn, table, "pool_status"):
            op.add_column(
                table,
                sa.Column(
                    "pool_status",
                    sa.String(30),
                    nullable=False,
                    server_default="pending_review",
                ),
            )

    if _has_table(conn, "video_assets"):
        indexes = {idx["name"] for idx in inspect(conn).get_indexes("video_assets")}
        if "ix_video_assets_pool_type_status" not in indexes:
            op.create_index(
                "ix_video_assets_pool_type_status",
                "video_assets",
                ["pool_type", "pool_status"],
            )
    if _has_table(conn, "final_videos"):
        indexes = {idx["name"] for idx in inspect(conn).get_indexes("final_videos")}
        if "ix_final_videos_pool_type_status" not in indexes:
            op.create_index(
                "ix_final_videos_pool_type_status",
                "final_videos",
                ["pool_type", "pool_status"],
            )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "final_videos"):
        indexes = {idx["name"] for idx in inspect(conn).get_indexes("final_videos")}
        if "ix_final_videos_pool_type_status" in indexes:
            op.drop_index("ix_final_videos_pool_type_status", table_name="final_videos")
    if _has_table(conn, "video_assets"):
        indexes = {idx["name"] for idx in inspect(conn).get_indexes("video_assets")}
        if "ix_video_assets_pool_type_status" in indexes:
            op.drop_index("ix_video_assets_pool_type_status", table_name="video_assets")
    for table in ("final_videos", "video_assets"):
        if _has_column(conn, table, "pool_status"):
            op.drop_column(table, "pool_status")
        if _has_column(conn, table, "pool_type"):
            op.drop_column(table, "pool_type")
    if _has_table(conn, "tiktok_profiles"):
        op.drop_index("ix_tiktok_profiles_handle", table_name="tiktok_profiles")
        op.drop_index("ix_tiktok_profiles_stage", table_name="tiktok_profiles")
        op.drop_table("tiktok_profiles")
