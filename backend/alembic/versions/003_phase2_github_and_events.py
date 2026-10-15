"""Phase 2 migration for github_connections, pull_requests, webhook_events, and platform_events.

Revision ID: 003_phase2_github_and_events
Revises: 002_phase1_api_keys
Create Date: 2026-10-15 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003_phase2_github_and_events"
down_revision: Union[str, None] = "002_phase1_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. github_connections table
    op.create_table(
        "github_connections",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("installation_id", sa.BigInteger(), nullable=True),
        sa.Column("personal_access_token_hash", sa.Text(), nullable=True),
        sa.Column("owner", sa.String(length=100), nullable=False),
        sa.Column("repo_name", sa.String(length=100), nullable=False),
        sa.Column("default_branch", sa.String(length=100), server_default="main", nullable=False),
        sa.Column("webhook_secret_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "project_id", "owner", "repo_name",
            name="uq_github_connections_project_owner_repo"
        ),
    )
    op.create_index("ix_github_connections_project_id", "github_connections", ["project_id"], unique=False)

    # 2. pull_requests table
    op.create_table(
        "pull_requests",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "github_connection_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("github_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pull_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), server_default="OPEN", nullable=False),
        sa.Column("author", sa.String(length=100), nullable=False),
        sa.Column("head_branch", sa.String(length=255), nullable=False),
        sa.Column("base_branch", sa.String(length=255), nullable=False),
        sa.Column("head_sha", sa.String(length=64), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("additions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deletions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("changed_files", sa.Integer(), server_default="0", nullable=False),
        sa.Column("diff_text", sa.Text(), nullable=True),
        sa.Column("github_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("github_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "github_connection_id", "pull_number",
            name="uq_pull_requests_connection_pull_number"
        ),
    )
    op.create_index("ix_pull_requests_github_connection_id", "pull_requests", ["github_connection_id"], unique=False)
    op.create_index("ix_pull_requests_pull_number", "pull_requests", ["pull_number"], unique=False)

    # 3. webhook_events table
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "github_connection_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("github_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("delivery_id", sa.String(length=128), nullable=False),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("processed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_webhook_events_github_connection_id", "webhook_events", ["github_connection_id"], unique=False)
    op.create_index("ix_webhook_events_delivery_id", "webhook_events", ["delivery_id"], unique=True)
    op.create_index("ix_webhook_events_event_type", "webhook_events", ["event_type"], unique=False)

    # 4. platform_events table
    op.create_table(
        "platform_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=16), server_default="1.0", nullable=False),
        sa.Column("trace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("processed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_platform_events_event_type", "platform_events", ["event_type"], unique=False)
    op.create_index("ix_platform_events_trace_id", "platform_events", ["trace_id"], unique=False)
    op.create_index("ix_platform_events_project_id", "platform_events", ["project_id"], unique=False)
    op.create_index("ix_platform_events_created_at", "platform_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("platform_events")
    op.drop_table("webhook_events")
    op.drop_table("pull_requests")
    op.drop_table("github_connections")
