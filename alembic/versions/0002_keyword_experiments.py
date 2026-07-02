"""keyword experiments schema

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-02 10:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "keyword_experiments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("keyword", sa.String(255), nullable=False),
        sa.Column(
            "channel_id",
            sa.String(255),
            sa.ForeignKey("channels.channel_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("channel_subscribers", sa.Integer, nullable=True),
        sa.Column("creator_avg_views", sa.Integer, nullable=True),
        sa.Column("views_vs_baseline", sa.Float, nullable=True),
        sa.Column("suggestion_source", sa.String(50), nullable=False),
        sa.Column("agent_suggested_score", sa.Integer, nullable=True),
        sa.Column("predicted_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("prediction_reasoning", sa.Text, nullable=True),
        sa.Column("predicted_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("actual_views", sa.Integer, nullable=True),
        sa.Column("actual_engagement", sa.Float, nullable=True),
        sa.Column("actual_retention", sa.Float, nullable=True),
        sa.Column("test_status", sa.String(50), nullable=False, server_default="in_progress"),
        sa.Column("user_rating", sa.Integer, nullable=True),
        sa.Column("user_comments", sa.Text, nullable=True),
        sa.Column("accuracy", sa.Float, nullable=True),
        sa.Column("outcome_type", sa.String(50), nullable=True),
        sa.Column("reported_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "suggestion_source IN ('agent_suggested', 'user_manual')",
            name="ck_keyword_experiments_suggestion_source",
        ),
        sa.CheckConstraint(
            "test_status IN ('in_progress', 'success', 'failed', 'partial')",
            name="ck_keyword_experiments_test_status",
        ),
        sa.CheckConstraint(
            "user_rating BETWEEN 1 AND 5",
            name="ck_keyword_experiments_user_rating",
        ),
        sa.CheckConstraint(
            "outcome_type IN ('true_positive', 'false_positive', 'true_negative', 'false_negative')",
            name="ck_keyword_experiments_outcome_type",
        ),
    )
    op.create_index("idx_experiments_keyword", "keyword_experiments", ["keyword"])
    op.create_index("idx_experiments_status", "keyword_experiments", ["test_status"])
    op.create_index("idx_experiments_source", "keyword_experiments", ["suggestion_source"])
    op.create_index("idx_experiments_channel", "keyword_experiments", ["channel_id"])
    op.create_index(
        "idx_experiments_created", "keyword_experiments", ["created_at"]
    )

    op.create_table(
        "keyword_patterns",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("pattern_type", sa.String(100), nullable=False),
        sa.Column("keyword_trait", sa.String(255), nullable=False),
        sa.Column("outcome_type", sa.String(50), nullable=False),
        sa.Column("insight", sa.Text, nullable=False),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("example_keywords", sa.Text, nullable=True),
        sa.Column("occurrence_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("avg_predicted", sa.Float, nullable=True),
        sa.Column("avg_actual", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("suggested_adjustment", postgresql.JSONB, nullable=True),
        sa.Column("experiment_ids", postgresql.JSONB, nullable=True, server_default=sa.text("'[]'")),
        sa.Column("discovered_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "performance_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("keyword", sa.String(255), nullable=False),
        sa.Column(
            "suggestion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suggestions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actual_views", sa.Integer, nullable=False),
        sa.Column("actual_likes", sa.Integer, nullable=True),
        sa.Column("actual_comments", sa.Integer, nullable=True),
        sa.Column("actual_shares", sa.Integer, nullable=True),
        sa.Column("followers_gained", sa.Integer, nullable=True),
        sa.Column("engagement_rate", sa.Float, nullable=True),
        sa.Column("outcome", sa.String(50), nullable=True),
        sa.Column("reported_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text, nullable=True),
        sa.CheckConstraint(
            "outcome IN ('success', 'neutral', 'failure')",
            name="ck_performance_reports_outcome",
        ),
    )
    op.create_index("idx_performance_reports_keyword", "performance_reports", ["keyword"])
    op.create_index("idx_performance_reports_reported_at", "performance_reports", ["reported_at"])


def downgrade() -> None:
    op.drop_index("idx_performance_reports_reported_at", table_name="performance_reports")
    op.drop_index("idx_performance_reports_keyword", table_name="performance_reports")
    op.drop_table("performance_reports")

    op.drop_table("keyword_patterns")

    op.drop_index("idx_experiments_created", table_name="keyword_experiments")
    op.drop_index("idx_experiments_channel", table_name="keyword_experiments")
    op.drop_index("idx_experiments_source", table_name="keyword_experiments")
    op.drop_index("idx_experiments_status", table_name="keyword_experiments")
    op.drop_index("idx_experiments_keyword", table_name="keyword_experiments")
    op.drop_table("keyword_experiments")
