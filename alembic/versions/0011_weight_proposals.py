"""weight_proposals table (US-056)

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-02 23:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def _has_table(conn, name: str) -> bool:
    return name in inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "weight_proposals"):
        return

    op.create_table(
        "weight_proposals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("factor", sa.String(50), nullable=False),
        sa.Column("old_value", sa.Float(), nullable=False),
        sa.Column("new_value", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("keyword_type", sa.String(20), nullable=False, server_default="beta"),
        sa.Column("learning_report_id", UUID(as_uuid=True), sa.ForeignKey("learning_reports.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "factor IN ('relevance', 'specificity', 'saturation')",
            name="ck_weight_proposals_factor",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_weight_proposals_status",
        ),
    )
    op.create_index("ix_weight_proposals_factor", "weight_proposals", ["factor"])
    op.create_index("ix_weight_proposals_status", "weight_proposals", ["status"])
    op.create_index("ix_weight_proposals_created_at", "weight_proposals", ["created_at"])


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "weight_proposals"):
        return
    op.drop_index("ix_weight_proposals_created_at", table_name="weight_proposals")
    op.drop_index("ix_weight_proposals_status", table_name="weight_proposals")
    op.drop_index("ix_weight_proposals_factor", table_name="weight_proposals")
    op.drop_table("weight_proposals")
