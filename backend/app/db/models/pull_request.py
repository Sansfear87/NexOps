"""Pull request model."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Text, ForeignKey, UniqueConstraint, Uuid, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDMixin, TimestampMixin
from app.db.constants import PRState

if TYPE_CHECKING:
    from app.db.models.github_connection import GitHubConnection
    from app.db.models.review import Review


class PullRequest(Base, UUIDMixin, TimestampMixin):
    """Stores GitHub Pull Request records synchronized from GitHub."""

    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint(
            "github_connection_id", "pull_number",
            name="uq_pull_requests_connection_pull_number"
        ),
    )

    github_connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("github_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pull_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(
        String(32),
        default=PRState.OPEN.value,
        nullable=False,
    )
    author: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    head_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    base_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    head_sha: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    body: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    additions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    deletions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    changed_files: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    diff_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Cached unified diff text for context engine analysis",
    )
    github_created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    github_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    github_connection: Mapped["GitHubConnection"] = relationship(
        "GitHubConnection",
        back_populates="pull_requests",
        lazy="selectin",
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="pull_request",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
