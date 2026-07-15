"""Add keyword_experiments.suggestion_id + prediction_signals (US-082)

Revision ID: 0020
Revises: 0019
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "keyword_experiments", "suggestion_id"):
        op.add_column(
            "keyword_experiments",
            sa.Column(
                "suggestion_id",
                UUID(as_uuid=True),
                sa.ForeignKey("suggestions.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_keyword_experiments_suggestion_id",
            "keyword_experiments",
            ["suggestion_id"],
        )
    if not _has_column(conn, "keyword_experiments", "prediction_signals"):
        op.add_column(
            "keyword_experiments",
            sa.Column("prediction_signals", JSONB(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "keyword_experiments", "prediction_signals"):
        op.drop_column("keyword_experiments", "prediction_signals")
    if _has_column(conn, "keyword_experiments", "suggestion_id"):
        op.drop_index(
            "ix_keyword_experiments_suggestion_id",
            table_name="keyword_experiments",
        )
        op.drop_column("keyword_experiments", "suggestion_id")
