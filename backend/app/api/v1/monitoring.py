"""FastAPI route controllers for Phase 9: Monitoring & Synthetic Health Checks."""
from __future__ import annotations

import logging
from typing import Any, Dict, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.constants import ProjectRole
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.monitoring import (
    HealthCheckResponse,
    HealthCheckTriggerRequest,
    HealthMetricResponse,
)
from app.services.deployment_service import DeploymentService
from app.services.monitoring_service import MonitoringService
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/deployments/{deployment_id}/probes",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger a synthetic health probe against a deployment",
)
async def trigger_health_probe(
    deployment_id: uuid.UUID,
    payload: HealthCheckTriggerRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Execute synthetic HTTP probe and store latency telemetry."""
    dep_service = DeploymentService(db)
    dep = dep_service.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    project_service = ProjectService(db)
    project_service._require_role(current_user, dep.project_id, ProjectRole.DEVELOPER)

    monitoring_service = MonitoringService(db)
    probe = await monitoring_service.execute_probe(
        deployment_id=deployment_id,
        endpoint=payload.endpoint,
    )
    return probe


@router.get(
    "/deployments/{deployment_id}/probes",
    response_model=List[HealthCheckResponse],
    summary="List synthetic health probes for a deployment",
)
def list_probes(
    deployment_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List historical health check probes."""
    dep_service = DeploymentService(db)
    dep = dep_service.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    project_service = ProjectService(db)
    project_service._require_role(current_user, dep.project_id, ProjectRole.VIEWER)

    monitoring_service = MonitoringService(db)
    return monitoring_service.get_probes(deployment_id, limit=limit)


@router.get(
    "/deployments/{deployment_id}/health",
    response_model=Dict[str, Any],
    summary="Get deployment health summary and error rates",
)
def get_deployment_health(
    deployment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get calculated health ratio and latency percentiles."""
    dep_service = DeploymentService(db)
    dep = dep_service.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    project_service = ProjectService(db)
    project_service._require_role(current_user, dep.project_id, ProjectRole.VIEWER)

    monitoring_service = MonitoringService(db)
    return monitoring_service.get_health_summary(deployment_id)


@router.get(
    "/deployments/{deployment_id}/metrics",
    response_model=List[HealthMetricResponse],
    summary="Get performance and latency metrics for deployment",
)
def get_deployment_metrics(
    deployment_id: uuid.UUID,
    metric_name: str = Query("probe_latency_ms"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Fetch time-series latency and health metrics."""
    dep_service = DeploymentService(db)
    dep = dep_service.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    project_service = ProjectService(db)
    project_service._require_role(current_user, dep.project_id, ProjectRole.VIEWER)

    monitoring_service = MonitoringService(db)
    return monitoring_service.get_metrics(deployment_id, metric_name=metric_name)
