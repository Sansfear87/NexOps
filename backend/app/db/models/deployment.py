"""SQLAlchemy models for Phase 8: Deployments and Deployment Logs."""
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.db.constants import (
    DeploymentEnvironment,
    DeploymentProviderType,
    DeploymentState,
)


class Deployment(Base):
    """Stores deployments transitioning through the 10 canonical deployment states."""
    __tablename__ = "deployments"

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
    gate_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("deployment_gates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    provider = Column(String(32), default=DeploymentProviderType.RENDER.value, nullable=False, index=True)
    environment = Column(String(32), default=DeploymentEnvironment.STAGING.value, nullable=False, index=True)
    state = Column(String(32), default=DeploymentState.PENDING.value, nullable=False, index=True)

    commit_sha = Column(String(64), nullable=False, index=True)
    branch = Column(String(255), default="main", nullable=False)
    url = Column(String(512), nullable=True)
    provider_deployment_id = Column(String(255), nullable=True, index=True)
    error_summary = Column(Text, nullable=True)

    configuration = Column(
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        default=dict,
        nullable=False,
    )
    metadata_json = Column(
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        default=dict,
        nullable=False,
    )

    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", backref="deployments")
    pull_request = relationship("PullRequest", backref="deployments")
    gate = relationship("DeploymentGate", backref="deployments")
    logs = relationship(
        "DeploymentLog",
        back_populates="deployment",
        cascade="all, delete-orphan",
        order_by="DeploymentLog.timestamp.asc()",
    )


class DeploymentLog(Base):
    """Streamed runtime or build log line for a deployment."""
    __tablename__ = "deployment_logs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("deployments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source = Column(String(32), default="build", nullable=False)  # build, stdout, stderr, health_check
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    deployment = relationship("Deployment", back_populates="logs")
