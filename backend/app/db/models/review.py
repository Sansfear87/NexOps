"""AI code review and review findings database models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin, json_column, utc_now
from app.db.constants import (
    FindingCategory,
    FindingSeverity,
    ReviewRisk,
    ReviewStatus,
    ReviewVerdict,
)

if TYPE_CHECKING:
    from app.db.models.pull_request import PullRequest


class Review(Base, UUIDMixin, TimestampMixin):
    """Stores AI code reviews evaluating pull request changes."""

    __tablename__ = "reviews"

    pull_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    head_sha: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=ReviewStatus.COMPLETED.value,
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    overall_risk: Mapped[str] = mapped_column(
        String(32),
        default=ReviewRisk.LOW.value,
        nullable=False,
        index=True,
    )
    risk_rationale: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    verdict: Mapped[str] = mapped_column(
        String(32),
        default=ReviewVerdict.APPROVE.value,
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        default="deepseek-coder",
        nullable=False,
    )
    token_usage: Mapped[Dict[str, Any]] = mapped_column(
        json_column(),
        default=dict,
        nullable=False,
    )
    review_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        json_column(),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    findings: Mapped[List["ReviewFinding"]] = relationship(
        "ReviewFinding",
        back_populates="review",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    pull_request: Mapped["PullRequest"] = relationship(
        "PullRequest",
        back_populates="reviews",
        lazy="selectin",
    )


class ReviewFinding(Base, UUIDMixin):
    """Discrete, file-and-line anchored code issue or recommendation."""

    __tablename__ = "review_findings"

    review_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    line: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    end_line: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(64),
        default=FindingCategory.BUG.value,
        nullable=False,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(32),
        default=FindingSeverity.WARNING.value,
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    recommendation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    suggested_diff: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    review: Mapped["Review"] = relationship(
        "Review",
        back_populates="findings",
    )
