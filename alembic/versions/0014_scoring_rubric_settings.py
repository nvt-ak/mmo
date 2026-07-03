"""settings scoring rubric overrides (US-061)

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "settings", "nurture_scoring_rubric"):
        op.add_column("settings", sa.Column("nurture_scoring_rubric", sa.Text(), nullable=True))
    if not _has_column(conn, "settings", "beta_scoring_rubric"):
        op.add_column("settings", sa.Column("beta_scoring_rubric", sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "settings", "beta_scoring_rubric"):
        op.drop_column("settings", "beta_scoring_rubric")
    if _has_column(conn, "settings", "nurture_scoring_rubric"):
        op.drop_column("settings", "nurture_scoring_rubric")
