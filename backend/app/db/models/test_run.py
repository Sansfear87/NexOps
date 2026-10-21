"""Test run and test case execution database models."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin, utc_now
from app.db.constants import TestCaseStatus, TestStatus

if TYPE_CHECKING:
    from app.db.models.project import Project
    from app.db.models.pull_request import PullRequest


class TestRun(Base, UUIDMixin, TimestampMixin):
    """Stores automated test suite execution instances."""

    __test__ = False
    __tablename__ = "test_runs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pull_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    commit_sha: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    suite_name: Mapped[str] = mapped_column(
        String(100),
        default="unit",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=TestStatus.PASSED.value,
        nullable=False,
        index=True,
    )
    passed: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    total_tests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_tests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    duration_seconds: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    summary_output: Mapped[Optional[str]] = mapped_column(
        Text,
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
    results: Mapped[List["TestResult"]] = relationship(
        "TestResult",
        back_populates="test_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    project: Mapped["Project"] = relationship(
        "Project",
        lazy="selectin",
    )
    pull_request: Mapped[Optional["PullRequest"]] = relationship(
        "PullRequest",
        lazy="selectin",
    )


class TestResult(Base, UUIDMixin):
    """Outcome for an individual test case within a test run."""

    __test__ = False
    __tablename__ = "test_results"

    test_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=TestCaseStatus.PASSED.value,
        nullable=False,
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    test_run: Mapped["TestRun"] = relationship(
        "TestRun",
        back_populates="results",
    )
