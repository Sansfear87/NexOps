"""Raw webhook event log model."""
from __future__ import annotations

import uuid
from typing import Optional, Any, Dict, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDMixin, TimestampMixin, json_column

if TYPE_CHECKING:
    from app.db.models.github_connection import GitHubConnection


class WebhookEvent(Base, UUIDMixin, TimestampMixin):
    """Raw incoming webhook payload log for auditing and idempotency."""

    __tablename__ = "webhook_events"

    github_connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("github_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    delivery_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
        doc="GitHub delivery GUID from X-GitHub-Delivery header",
    )
    payload: Mapped[Dict[str, Any]] = mapped_column(
        json_column(),
        nullable=False,
    )
    processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    github_connection: Mapped["GitHubConnection"] = relationship(
        "GitHubConnection",
        back_populates="webhook_events",
        lazy="selectin",
    )
