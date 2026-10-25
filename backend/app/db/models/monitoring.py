"""SQLAlchemy models for Phase 9: Monitoring, Health Checks, and Synthetic Probes."""
import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class HealthCheck(Base):
    """Synthetic health check probe record for a deployment."""
    __tablename__ = "health_checks"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("deployments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint = Column(String(512), nullable=False)
    status_code = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=False, default=0.0)
    is_healthy = Column(Boolean, nullable=False, default=True, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    deployment = relationship("Deployment", backref="health_checks")
    project = relationship("Project", backref="health_checks")


class HealthMetric(Base):
    """Aggregated health & runtime performance metric (error rate, latency p95, memory)."""
    __tablename__ = "health_metrics"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("deployments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_name = Column(String(64), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(32), default="ms", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    deployment = relationship("Deployment", backref="health_metrics")
    project = relationship("Project", backref="health_metrics")
