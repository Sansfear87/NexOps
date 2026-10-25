"""Pydantic schemas for Phase 8: Deployments and Deployment Logs."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.constants import DeploymentEnvironment, DeploymentProviderType, DeploymentState


class DeploymentCreateRequest(BaseModel):
    """Payload to trigger a deployment."""
    provider: DeploymentProviderType = DeploymentProviderType.RENDER
    environment: DeploymentEnvironment = DeploymentEnvironment.STAGING
    commit_sha: str = Field(min_length=7, max_length=64)
    branch: str = "main"
    pull_request_id: Optional[UUID] = None
    gate_id: Optional[UUID] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeploymentLogSchema(BaseModel):
    """Schema representing a single build/runtime log line."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deployment_id: UUID
    source: str
    message: str
    timestamp: datetime


class DeploymentResponseSchema(BaseModel):
    """Public representation of a deployment."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    pull_request_id: Optional[UUID] = None
    gate_id: Optional[UUID] = None
    provider: DeploymentProviderType
    environment: DeploymentEnvironment
    state: DeploymentState
    commit_sha: str
    branch: str
    url: Optional[str] = None
    provider_deployment_id: Optional[str] = None
    error_summary: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    logs: Optional[List[DeploymentLogSchema]] = None


class RollbackTriggerRequest(BaseModel):
    """Payload to trigger a rollback for a deployment."""
    reason: str = Field(min_length=3, max_length=1000)
    target_deployment_id: Optional[UUID] = None


class RollbackResponseSchema(BaseModel):
    """Response of a completed or initiated rollback."""
    rollback_id: str
    state: DeploymentState
    target_version: str
    initiated_at: str
    message: str
