"""SQLAlchemy models for Phase 10: Incidents, Autonomous Diagnosis, and Rollbacks."""
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.db.constants import IncidentSeverity, IncidentStatus, RemediationAction


class Incident(Base):
    """Production or staging incident triggered by probe failure or runtime regression."""
    __tablename__ = "incidents"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deployment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("deployments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    severity = Column(String(32), default=IncidentSeverity.SEV2.value, nullable=False, index=True)
    status = Column(String(32), default=IncidentStatus.OPEN.value, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    root_cause_summary = Column(Text, nullable=True)
    recommended_action = Column(String(32), default=RemediationAction.ROLLBACK.value, nullable=False)
    target_stable_version = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", backref="incidents")
    deployment = relationship("Deployment", backref="incidents")
    diagnoses = relationship(
        "DiagnosisRun",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="DiagnosisRun.created_at.desc()",
    )


class DiagnosisRun(Base):
    """Autonomous diagnosis agent execution analyzing logs and diffs for an incident."""
    __tablename__ = "diagnosis_runs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_run_id = Column(Uuid(as_uuid=True), nullable=True)
    diagnosis_summary = Column(Text, nullable=False)
    recommended_action = Column(String(32), default=RemediationAction.ROLLBACK.value, nullable=False)
    suspected_commits = Column(
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        default=list,
        nullable=False,
    )
    logs_analyzed = Column(
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        default=list,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    incident = relationship("Incident", back_populates="diagnoses")
