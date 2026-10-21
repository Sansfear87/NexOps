"""FastAPI route controllers for Phase 7: Deployment Guardrails, Risk Gates, and Audit Logs."""
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
from app.schemas.deployment_gate import (
    DeploymentGateResponse,
    GateApprovalRequest,
    GateAuditLogSchema,
    GateBypassRequest,
    GateEvaluationRequest,
    GateRejectionRequest,
)
from app.services.project_service import ProjectService
from app.services.risk_service import RiskService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/projects/{project_id}/gates/evaluate",
    response_model=DeploymentGateResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate deployment safety guardrails for a pull request",
)
def evaluate_project_gate(
    project_id: uuid.UUID,
    payload: GateEvaluationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Run deterministic risk assessment against diff, tests, and review findings."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.DEVELOPER)

    risk_service = RiskService(db)
    try:
        gate = risk_service.evaluate_gate(
            project_id=project_id,
            pull_request_id=payload.pull_request_id,
            review_id=payload.review_id,
            test_run_id=payload.test_run_id,
            actor_id=current_user.id,
        )
        return gate
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/projects/{project_id}/gates",
    response_model=List[DeploymentGateResponse],
    status_code=status.HTTP_200_OK,
    summary="List deployment gates for a project",
)
def list_project_gates(
    project_id: uuid.UUID,
    gate_status: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve all deployment gates for a given project with optional status filter."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    risk_service = RiskService(db)
    gates = risk_service.gate_repo.list_by_project(
        project_id=project_id,
        limit=limit,
        offset=offset,
        status=gate_status,
    )
    return gates


@router.get(
    "/gates/{gate_id}",
    response_model=DeploymentGateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get deployment gate details by ID",
)
def get_gate(
    gate_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Fetch a single deployment gate including its audit logs and policy evaluations."""
    risk_service = RiskService(db)
    gate = risk_service.get_gate_with_audit(gate_id)
    if not gate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment gate not found.")

    project_service = ProjectService(db)
    project_service._require_role(current_user, gate.project_id, ProjectRole.VIEWER)

    return gate


@router.post(
    "/gates/{gate_id}/approve",
    response_model=DeploymentGateResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a deployment gate",
)
def approve_gate(
    gate_id: uuid.UUID,
    payload: Optional[GateApprovalRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Human-in-the-loop approval allowing gated deployment to advance."""
    risk_service = RiskService(db)
    gate = risk_service.gate_repo.get_by_id(gate_id)
    if not gate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment gate not found.")

    project_service = ProjectService(db)
    project_service._require_role(current_user, gate.project_id, ProjectRole.MAINTAINER)

    notes = payload.notes if payload else None
    try:
        updated_gate = risk_service.approve_gate(
            gate_id=gate_id,
            approver_id=current_user.id,
            notes=notes,
        )
        return updated_gate
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/gates/{gate_id}/reject",
    response_model=DeploymentGateResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject a deployment gate",
)
def reject_gate(
    gate_id: uuid.UUID,
    payload: GateRejectionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Human operator rejects deployment progression."""
    risk_service = RiskService(db)
    gate = risk_service.gate_repo.get_by_id(gate_id)
    if not gate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment gate not found.")

    project_service = ProjectService(db)
    project_service._require_role(current_user, gate.project_id, ProjectRole.MAINTAINER)

    try:
        updated_gate = risk_service.reject_gate(
            gate_id=gate_id,
            actor_id=current_user.id,
            reason=payload.reason,
        )
        return updated_gate
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/gates/{gate_id}/bypass",
    response_model=DeploymentGateResponse,
    status_code=status.HTTP_200_OK,
    summary="Bypass deployment gate with mandatory audit justification",
)
def bypass_gate(
    gate_id: uuid.UUID,
    payload: GateBypassRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Admin overrides and bypasses a blocked/pending gate with immutable audit log."""
    risk_service = RiskService(db)
    gate = risk_service.gate_repo.get_by_id(gate_id)
    if not gate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment gate not found.")

    project_service = ProjectService(db)
    # Bypass requires OWNER role
    project_service._require_role(current_user, gate.project_id, ProjectRole.OWNER)

    try:
        updated_gate = risk_service.bypass_gate(
            gate_id=gate_id,
            actor_id=current_user.id,
            bypass_reason=payload.reason,
        )
        return updated_gate
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/gates/{gate_id}/audit-logs",
    response_model=List[GateAuditLogSchema],
    status_code=status.HTTP_200_OK,
    summary="Get complete audit log history for a deployment gate",
)
def get_gate_audit_logs(
    gate_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve the chronological audit trail for a safety gate."""
    risk_service = RiskService(db)
    gate = risk_service.gate_repo.get_by_id(gate_id)
    if not gate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment gate not found.")

    project_service = ProjectService(db)
    project_service._require_role(current_user, gate.project_id, ProjectRole.VIEWER)

    return risk_service.gate_repo.get_audit_logs(gate_id)
