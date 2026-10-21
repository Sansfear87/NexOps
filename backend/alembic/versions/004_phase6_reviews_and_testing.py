"""Phase 6 migration for reviews, review_findings, test_runs, and test_results.

Revision ID: 004_phase6_reviews_and_testing
Revises: 003_phase2_github_and_events
Create Date: 2026-10-21 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004_phase6_reviews_and_testing"
down_revision: Union[str, None] = "003_phase2_github_and_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. reviews table
    op.create_table(
        "reviews",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "pull_request_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("pull_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_run_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("head_sha", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="COMPLETED", nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("overall_risk", sa.String(length=32), server_default="LOW", nullable=False),
        sa.Column("risk_rationale", sa.Text(), nullable=True),
        sa.Column("verdict", sa.String(length=32), server_default="APPROVE", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("model_name", sa.String(length=100), server_default="deepseek-coder", nullable=False),
        sa.Column(
            "token_usage",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "review_metadata",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reviews_pull_request_id", "reviews", ["pull_request_id"], unique=False)
    op.create_index("ix_reviews_head_sha", "reviews", ["head_sha"], unique=False)
    op.create_index("ix_reviews_overall_risk", "reviews", ["overall_risk"], unique=False)
    op.create_index("ix_reviews_verdict", "reviews", ["verdict"], unique=False)
    op.create_index("ix_reviews_created_at", "reviews", ["created_at"], unique=False)

    # 2. review_findings table
    op.create_table(
        "review_findings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "review_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("reviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file", sa.String(length=512), nullable=False),
        sa.Column("line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=64), server_default="BUG", nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="WARNING", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("suggested_diff", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_review_findings_review_id", "review_findings", ["review_id"], unique=False)
    op.create_index("ix_review_findings_category", "review_findings", ["category"], unique=False)
    op.create_index("ix_review_findings_severity", "review_findings", ["severity"], unique=False)

    # 3. test_runs table
    op.create_table(
        "test_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pull_request_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("pull_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("agent_run_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("suite_name", sa.String(length=100), server_default="unit", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PASSED", nullable=False),
        sa.Column("passed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("total_tests", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_tests", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duration_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("summary_output", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_test_runs_project_id", "test_runs", ["project_id"], unique=False)
    op.create_index("ix_test_runs_pull_request_id", "test_runs", ["pull_request_id"], unique=False)
    op.create_index("ix_test_runs_commit_sha", "test_runs", ["commit_sha"], unique=False)
    op.create_index("ix_test_runs_status", "test_runs", ["status"], unique=False)
    op.create_index("ix_test_runs_created_at", "test_runs", ["created_at"], unique=False)

    # 4. test_results table
    op.create_table(
        "test_results",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "test_run_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("test_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("test_case_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PASSED", nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_test_results_test_run_id", "test_results", ["test_run_id"], unique=False)


def downgrade() -> None:
    op.drop_table("test_results")
    op.drop_table("test_runs")
    op.drop_table("review_findings")
    op.drop_table("reviews")
