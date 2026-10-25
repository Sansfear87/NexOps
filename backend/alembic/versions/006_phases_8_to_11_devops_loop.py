"""Alembic migration for Phases 8 to 11: Deployments, Monitoring, Incidents, and Project Memory.

Revision ID: 006_phases_8_to_11_devops_loop
Revises: 005_phase7_risk_guardrails
Create Date: 2026-10-25 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006_phases_8_to_11_devops_loop"
down_revision: Union[str, None] = "005_phase7_risk_guardrails"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. deployments table
    op.create_table(
        "deployments",
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
            "gate_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("deployment_gates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provider", sa.String(length=32), server_default="render", nullable=False),
        sa.Column("environment", sa.String(length=32), server_default="staging", nullable=False),
        sa.Column("state", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("branch", sa.String(length=255), server_default="main", nullable=False),
        sa.Column("url", sa.String(length=512), nullable=True),
        sa.Column("provider_deployment_id", sa.String(length=255), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "configuration",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "metadata_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deployments_project_id", "deployments", ["project_id"], unique=False)
    op.create_index("ix_deployments_pull_request_id", "deployments", ["pull_request_id"], unique=False)
    op.create_index("ix_deployments_gate_id", "deployments", ["gate_id"], unique=False)
    op.create_index("ix_deployments_state", "deployments", ["state"], unique=False)
    op.create_index("ix_deployments_provider", "deployments", ["provider"], unique=False)
    op.create_index("ix_deployments_environment", "deployments", ["environment"], unique=False)
    op.create_index("ix_deployments_commit_sha", "deployments", ["commit_sha"], unique=False)
    op.create_index("ix_deployments_provider_deployment_id", "deployments", ["provider_deployment_id"], unique=False)
    op.create_index("ix_deployments_created_at", "deployments", ["created_at"], unique=False)

    # 2. deployment_logs table
    op.create_table(
        "deployment_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "deployment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("deployments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=32), server_default="build", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deployment_logs_deployment_id", "deployment_logs", ["deployment_id"], unique=False)
    op.create_index("ix_deployment_logs_timestamp", "deployment_logs", ["timestamp"], unique=False)

    # 3. health_checks table
    op.create_table(
        "health_checks",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "deployment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("deployments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.String(length=512), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("is_healthy", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_health_checks_deployment_id", "health_checks", ["deployment_id"], unique=False)
    op.create_index("ix_health_checks_project_id", "health_checks", ["project_id"], unique=False)
    op.create_index("ix_health_checks_is_healthy", "health_checks", ["is_healthy"], unique=False)
    op.create_index("ix_health_checks_created_at", "health_checks", ["created_at"], unique=False)

    # 4. health_metrics table
    op.create_table(
        "health_metrics",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "deployment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("deployments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_name", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), server_default="ms", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_health_metrics_deployment_id", "health_metrics", ["deployment_id"], unique=False)
    op.create_index("ix_health_metrics_project_id", "health_metrics", ["project_id"], unique=False)
    op.create_index("ix_health_metrics_metric_name", "health_metrics", ["metric_name"], unique=False)

    # 5. incidents table
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "deployment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("deployments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("severity", sa.String(length=32), server_default="SEV2", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="OPEN", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("root_cause_summary", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.String(length=32), server_default="ROLLBACK", nullable=False),
        sa.Column("target_stable_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_incidents_project_id", "incidents", ["project_id"], unique=False)
    op.create_index("ix_incidents_deployment_id", "incidents", ["deployment_id"], unique=False)
    op.create_index("ix_incidents_severity", "incidents", ["severity"], unique=False)
    op.create_index("ix_incidents_status", "incidents", ["status"], unique=False)
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"], unique=False)

    # 6. diagnosis_runs table
    op.create_table(
        "diagnosis_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_run_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("diagnosis_summary", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.String(length=32), server_default="ROLLBACK", nullable=False),
        sa.Column(
            "suspected_commits",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "logs_analyzed",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_diagnosis_runs_incident_id", "diagnosis_runs", ["incident_id"], unique=False)

    # 7. project_memory table
    op.create_table(
        "project_memory",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=32), server_default="incident_postmortem", nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.Integer(), server_default="3", nullable=False),
        sa.Column(
            "embedding",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "metadata_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("access_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_project_memory_project_id", "project_memory", ["project_id"], unique=False)
    op.create_index("ix_project_memory_category", "project_memory", ["category"], unique=False)
    op.create_index("ix_project_memory_key", "project_memory", ["key"], unique=False)


def downgrade() -> None:
    op.drop_table("project_memory")
    op.drop_table("diagnosis_runs")
    op.drop_table("incidents")
    op.drop_table("health_metrics")
    op.drop_table("health_checks")
    op.drop_table("deployment_logs")
    op.drop_table("deployments")
