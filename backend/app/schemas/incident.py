"""Pydantic schemas for Phase 10: Incidents & Autonomous Diagnosis."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.constants import IncidentSeverity, IncidentStatus, RemediationAction


class IncidentCreateRequest(BaseModel):
    """Payload to declare an incident."""
    title: str = Field(min_length=3, max_length=255)
    description: Optional[str] = None
    severity: IncidentSeverity = IncidentSeverity.SEV2
    deployment_id: Optional[UUID] = None


class DiagnosisRunResponse(BaseModel):
    """Public representation of an automated diagnosis run."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    agent_run_id: Optional[UUID] = None
    diagnosis_summary: str
    recommended_action: RemediationAction
    suspected_commits: List[Dict[str, Any]] = Field(default_factory=list)
    logs_analyzed: List[str] = Field(default_factory=list)
    created_at: datetime


class IncidentResponse(BaseModel):
    """Public representation of an incident ticket."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    deployment_id: Optional[UUID] = None
    severity: IncidentSeverity
    status: IncidentStatus
    title: str
    description: Optional[str] = None
    root_cause_summary: Optional[str] = None
    recommended_action: RemediationAction
    target_stable_version: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    diagnoses: Optional[List[DiagnosisRunResponse]] = None


class IncidentResolveRequest(BaseModel):
    """Payload to close/resolve an incident."""
    root_cause_summary: str = Field(min_length=3)
    recommended_action: RemediationAction = RemediationAction.ROLLBACK
