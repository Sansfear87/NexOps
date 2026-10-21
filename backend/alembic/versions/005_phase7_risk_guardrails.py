"""Phase 7 migration for deployment_gates and gate_audit_logs.

Revision ID: 005_phase7_risk_guardrails
Revises: 004_phase6_reviews_and_testing
Create Date: 2026-10-21 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005_phase7_risk_guardrails"
down_revision: Union[str, None] = "004_phase6_reviews_and_testing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. deployment_gates table
    op.create_table(
        "deployment_gates",
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
        sa.Column(
            "review_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("reviews.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "test_run_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("test_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("risk_level", sa.String(length=32), server_default="LOW", nullable=False),
        sa.Column("gate_status", sa.String(length=32), server_default="REQUIRES_APPROVAL", nullable=False),
        sa.Column("risk_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "reasons",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "critical_files",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "policy_evaluations",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "approved_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_notes", sa.Text(), nullable=True),
        sa.Column("bypass_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deployment_gates_project_id", "deployment_gates", ["project_id"], unique=False)
    op.create_index("ix_deployment_gates_pull_request_id", "deployment_gates", ["pull_request_id"], unique=False)
    op.create_index("ix_deployment_gates_review_id", "deployment_gates", ["review_id"], unique=False)
    op.create_index("ix_deployment_gates_test_run_id", "deployment_gates", ["test_run_id"], unique=False)
    op.create_index("ix_deployment_gates_risk_level", "deployment_gates", ["risk_level"], unique=False)
    op.create_index("ix_deployment_gates_gate_status", "deployment_gates", ["gate_status"], unique=False)
    op.create_index("ix_deployment_gates_approved_by", "deployment_gates", ["approved_by"], unique=False)
    op.create_index("ix_deployment_gates_created_at", "deployment_gates", ["created_at"], unique=False)

    # 2. gate_audit_logs table
    op.create_table(
        "gate_audit_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "gate_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("deployment_gates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column(
            "actor_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_type", sa.String(length=32), server_default="USER", nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "audit_metadata",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gate_audit_logs_gate_id", "gate_audit_logs", ["gate_id"], unique=False)
    op.create_index("ix_gate_audit_logs_action", "gate_audit_logs", ["action"], unique=False)
    op.create_index("ix_gate_audit_logs_actor_id", "gate_audit_logs", ["actor_id"], unique=False)
    op.create_index("ix_gate_audit_logs_created_at", "gate_audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("gate_audit_logs")
    op.drop_table("deployment_gates")
