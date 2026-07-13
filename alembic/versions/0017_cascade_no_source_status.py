"""Add completed_no_source to keyword_cascade_jobs status (US-074)

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-13 08:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_keyword_cascade_jobs_status",
        "keyword_cascade_jobs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_keyword_cascade_jobs_status",
        "keyword_cascade_jobs",
        sa.text("status IN ('started', 'running', 'completed', 'completed_no_source', 'failed')"),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_keyword_cascade_jobs_status",
        "keyword_cascade_jobs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_keyword_cascade_jobs_status",
        "keyword_cascade_jobs",
        sa.text("status IN ('started', 'running', 'completed', 'failed')"),
    )
