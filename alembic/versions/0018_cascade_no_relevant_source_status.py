"""Add completed_no_relevant_source to keyword_cascade_jobs status (US-075)

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-13 09:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
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
        sa.text(
            "status IN ('started', 'running', 'completed', 'completed_no_source', 'completed_no_relevant_source', 'failed')"
        ),
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
        sa.text(
            "status IN ('started', 'running', 'completed', 'completed_no_source', 'failed')"
        ),
    )
