"""Platform event model for internal event bus."""
from __future__ import annotations

import uuid
from typing import Any, Dict, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDMixin, TimestampMixin, json_column

if TYPE_CHECKING:
    from app.db.models.project import Project


class PlatformEvent(Base, UUIDMixin, TimestampMixin):
    """Canonical event record representing lifecycle transitions across the platform."""

    __tablename__ = "platform_events"

    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(
        String(16),
        default="1.0",
        nullable=False,
    )
    trace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
        doc="Correlates all actions triggered across this operational lifecycle",
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    actor_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
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

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        lazy="selectin",
    )
