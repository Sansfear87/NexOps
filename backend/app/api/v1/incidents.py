"""FastAPI route controllers for Phase 10: Incidents & Autonomous Diagnosis."""
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
from app.schemas.incident import (
    DiagnosisRunResponse,
    IncidentCreateRequest,
    IncidentResolveRequest,
    IncidentResponse,
)
from app.services.incident_service import IncidentService
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/projects/{project_id}/incidents",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Declare an incident for a project",
)
def create_incident(
    project_id: uuid.UUID,
    payload: IncidentCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Declare a production or staging incident."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.DEVELOPER)

    service = IncidentService(db)
    inc = service.create_incident(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity.value,
        deployment_id=payload.deployment_id,
        actor_id=str(current_user.id),
    )
    return inc


@router.get(
    "/projects/{project_id}/incidents",
    response_model=List[IncidentResponse],
    summary="List incidents for a project",
)
def list_incidents(
    project_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List project incidents."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    service = IncidentService(db)
    return service.list_incidents(project_id, status=status_filter, limit=limit)


@router.get(
    "/incidents/{incident_id}",
    response_model=IncidentResponse,
    summary="Get incident details",
)
def get_incident(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Fetch incident by UUID."""
    service = IncidentService(db)
    inc = service.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    project_service = ProjectService(db)
    project_service._require_role(current_user, inc.project_id, ProjectRole.VIEWER)
    return inc


@router.post(
    "/incidents/{incident_id}/diagnose",
    response_model=DiagnosisRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger autonomous root-cause diagnosis for incident",
)
async def diagnose_incident(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Analyze logs, diffs, and health probes to determine root cause."""
    service = IncidentService(db)
    inc = service.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    project_service = ProjectService(db)
    project_service._require_role(current_user, inc.project_id, ProjectRole.DEVELOPER)

    diag = await service.diagnose_incident(incident_id, actor_id=str(current_user.id))
    return diag


@router.post(
    "/incidents/{incident_id}/resolve",
    response_model=IncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Remediate and resolve incident",
)
async def resolve_incident(
    incident_id: uuid.UUID,
    payload: IncidentResolveRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Resolve incident and trigger rollback/remediation."""
    service = IncidentService(db)
    inc = service.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    project_service = ProjectService(db)
    project_service._require_role(current_user, inc.project_id, ProjectRole.MAINTAINER)

    resolved = await service.remediate_and_resolve(
        incident_id=incident_id,
        auto_rollback=(payload.recommended_action.value == "ROLLBACK"),
        actor_id=str(current_user.id),
    )
    return resolved
