"""Pydantic schemas for Phase 9: Monitoring & Synthetic Health Checks."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HealthCheckTriggerRequest(BaseModel):
    """Payload to trigger synthetic probe check."""
    endpoint: Optional[str] = "/health"


class HealthCheckResponse(BaseModel):
    """Public representation of a synthetic health probe check."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deployment_id: UUID
    project_id: UUID
    endpoint: str
    status_code: Optional[int] = None
    latency_ms: float
    is_healthy: bool
    error_message: Optional[str] = None
    created_at: datetime


class HealthMetricResponse(BaseModel):
    """Public representation of a performance metric."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deployment_id: UUID
    project_id: UUID
    metric_name: str
    value: float
    unit: str
    created_at: datetime


class ProjectHealthSummaryResponse(BaseModel):
    """Summary of project deployment health."""
    project_id: UUID
    active_deployments: int
    healthy_deployments: int
    recent_checks: List[HealthCheckResponse] = Field(default_factory=list)
    average_latency_ms: float
    overall_status: str
