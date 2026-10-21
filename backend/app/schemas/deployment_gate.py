"""Pydantic schemas for Phase 7: Deployment Guardrails, Risk Gates, and Audit Logs."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.constants import ActorType, GateAction, GateStatus, ReviewRisk


class PolicyRuleResultSchema(BaseModel):
    """Result of an individual guardrail policy evaluation."""
    model_config = ConfigDict(from_attributes=True)

    rule: str
    passed: bool
    score: int = Field(ge=0, le=100)
    detail: str


class GateAuditLogSchema(BaseModel):
    """Schema representing an immutable audit trail entry for gate decisions."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gate_id: UUID
    action: GateAction
    actor_id: Optional[UUID] = None
    actor_type: ActorType
    previous_status: Optional[GateStatus] = None
    new_status: GateStatus
    reason: Optional[str] = None
    audit_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class GateEvaluationRequest(BaseModel):
    """Request payload to trigger guardrail evaluation for a pull request."""
    pull_request_id: UUID
    review_id: Optional[UUID] = None
    test_run_id: Optional[UUID] = None


class GateApprovalRequest(BaseModel):
    """Payload to approve a high/critical risk deployment gate."""
    notes: Optional[str] = None


class GateRejectionRequest(BaseModel):
    """Payload to reject a deployment gate."""
    reason: str = Field(min_length=3, max_length=2000, description="Mandatory explanation for rejection.")


class GateBypassRequest(BaseModel):
    """Payload to bypass a safety gate (requires elevated privileges)."""
    reason: str = Field(min_length=10, max_length=2000, description="Mandatory detailed justification for overriding guardrails.")


class DeploymentGateResponse(BaseModel):
    """Public representation of a deployment risk gate."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    pull_request_id: Optional[UUID] = None
    review_id: Optional[UUID] = None
    test_run_id: Optional[UUID] = None
    risk_level: ReviewRisk
    gate_status: GateStatus
    risk_score: int = Field(ge=0, le=100)
    summary: str
    reasons: List[str] = Field(default_factory=list)
    critical_files: List[str] = Field(default_factory=list)
    policy_evaluations: List[PolicyRuleResultSchema] = Field(default_factory=list)
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    bypass_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    audit_logs: Optional[List[GateAuditLogSchema]] = None
