"""GitHub repository connection model."""
from __future__ import annotations

import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text, ForeignKey, UniqueConstraint, Uuid, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.project import Project
    from app.db.models.pull_request import PullRequest
    from app.db.models.webhook_event import WebhookEvent


class GitHubConnection(Base, UUIDMixin, TimestampMixin):
    """Represents a GitHub repository linked to a project."""

    __tablename__ = "github_connections"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "owner", "repo_name",
            name="uq_github_connections_project_owner_repo"
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    installation_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
    personal_access_token_hash: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Symmetrically encrypted personal access token for GitHub API operations",
    )
    owner: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    repo_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    default_branch: Mapped[str] = mapped_column(
        String(100),
        default="main",
        nullable=False,
    )
    webhook_secret_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="github_connections",
        lazy="selectin",
    )
    pull_requests: Mapped[List["PullRequest"]] = relationship(
        "PullRequest",
        back_populates="github_connection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    webhook_events: Mapped[List["WebhookEvent"]] = relationship(
        "WebhookEvent",
        back_populates="github_connection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
