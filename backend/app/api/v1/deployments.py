"""FastAPI route controllers for Phase 8: Deployments and Rollbacks."""
from __future__ import annotations

import logging
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.constants import ProjectRole
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.deployment import (
    DeploymentCreateRequest,
    DeploymentLogSchema,
    DeploymentResponseSchema,
    RollbackResponseSchema,
    RollbackTriggerRequest,
)
from app.services.deployment_service import DeploymentService
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/projects/{project_id}/deployments",
    response_model=DeploymentResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a deployment for a project",
)
async def create_deployment(
    project_id: uuid.UUID,
    payload: DeploymentCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Execute deployment workflow through provider adapter."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.DEVELOPER)

    service = DeploymentService(db)
    dep = await service.trigger_deployment(
        project_id=project_id,
        provider=payload.provider.value,
        environment=payload.environment.value,
        commit_sha=payload.commit_sha,
        branch=payload.branch,
        pull_request_id=payload.pull_request_id,
        gate_id=payload.gate_id,
        configuration=payload.configuration,
        metadata_json=payload.metadata,
        actor_id=str(current_user.id),
    )
    return dep


@router.get(
    "/projects/{project_id}/deployments",
    response_model=List[DeploymentResponseSchema],
    summary="List deployments for a project",
)
def list_project_deployments(
    project_id: uuid.UUID,
    environment: Optional[str] = Query(None, description="Filter by environment"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List deployments newest first."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    service = DeploymentService(db)
    return service.list_deployments(project_id, environment=environment, limit=limit, offset=offset)


@router.get(
    "/deployments/{deployment_id}",
    response_model=DeploymentResponseSchema,
    summary="Get deployment details",
)
def get_deployment(
    deployment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Fetch deployment by UUID."""
    service = DeploymentService(db)
    dep = service.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    project_service = ProjectService(db)
    project_service._require_role(current_user, dep.project_id, ProjectRole.VIEWER)
    return dep


@router.get(
    "/deployments/{deployment_id}/logs",
    response_model=List[DeploymentLogSchema],
    summary="Fetch deployment build and runtime logs",
)
def get_deployment_logs(
    deployment_id: uuid.UUID,
    tail: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Fetch logs for a deployment."""
    service = DeploymentService(db)
    dep = service.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    project_service = ProjectService(db)
    project_service._require_role(current_user, dep.project_id, ProjectRole.VIEWER)
    return service.get_logs(deployment_id, tail=tail)


@router.post(
    "/deployments/{deployment_id}/rollback",
    response_model=RollbackResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Trigger rollback for active deployment",
)
async def rollback_deployment(
    deployment_id: uuid.UUID,
    payload: RollbackTriggerRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Roll back deployment to previous stable version."""
    service = DeploymentService(db)
    dep = service.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    project_service = ProjectService(db)
    project_service._require_role(current_user, dep.project_id, ProjectRole.MAINTAINER)

    try:
        rolled_back_dep = await service.rollback(
            deployment_id=deployment_id,
            target_deployment_id=payload.target_deployment_id,
            reason=payload.reason,
            actor_id=str(current_user.id),
        )
        return RollbackResponseSchema(
            rollback_id=str(uuid.uuid4()),
            state=rolled_back_dep.state,
            target_version=rolled_back_dep.commit_sha,
            initiated_at=str(rolled_back_dep.updated_at),
            message="Rollback completed successfully",
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
