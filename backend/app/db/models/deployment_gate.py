"""SQLAlchemy models for Phase 7: Deployment Guardrails, Risk Gates, and Audit Logs."""
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.db.constants import ActorType, GateStatus, ReviewRisk


class DeploymentGate(Base):
    """Deployment safety gate evaluating risk metrics and gating promotion to environments."""
    __tablename__ = "deployment_gates"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pull_request_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    review_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("reviews.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    test_run_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("test_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    risk_level = Column(String(32), default=ReviewRisk.LOW.value, nullable=False, index=True)
    gate_status = Column(String(32), default=GateStatus.REQUIRES_APPROVAL.value, nullable=False, index=True)
    risk_score = Column(Integer, default=0, nullable=False)
    summary = Column(Text, nullable=False)

    reasons = Column(
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        default=list,
        nullable=False,
    )
    critical_files = Column(
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        default=list,
        nullable=False,
    )
    policy_evaluations = Column(
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        default=list,
        nullable=False,
    )

    approved_by = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    bypass_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", backref="deployment_gates")
    pull_request = relationship("PullRequest", backref="deployment_gates")
    review = relationship("Review", backref="deployment_gates")
    test_run = relationship("TestRun", backref="deployment_gates")
    approver = relationship("User", foreign_keys=[approved_by])
    audit_logs = relationship(
        "GateAuditLog",
        back_populates="gate",
        cascade="all, delete-orphan",
        order_by="GateAuditLog.created_at.asc()",
    )


class GateAuditLog(Base):
    """Immutable audit trail for gate evaluations, approvals, rejections, and bypasses."""
    __tablename__ = "gate_audit_logs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gate_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("deployment_gates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = Column(String(32), nullable=False, index=True)
    actor_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_type = Column(String(32), default=ActorType.USER.value, nullable=False)
    previous_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=False)
    reason = Column(Text, nullable=True)
    audit_metadata = Column(
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        default=dict,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    gate = relationship("DeploymentGate", back_populates="audit_logs")
    actor = relationship("User", foreign_keys=[actor_id])
