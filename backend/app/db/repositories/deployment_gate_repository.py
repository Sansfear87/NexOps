"""Repository for DeploymentGate and GateAuditLog database operations."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.constants import ActorType, GateAction, GateStatus, ReviewRisk
from app.db.models.deployment_gate import DeploymentGate, GateAuditLog


class DeploymentGateRepository:
    """Repository handling database access for deployment gates and immutable audit trails."""

    def __init__(self, db: Session):
        self.db = db

    def create_gate(
        self,
        project_id: UUID,
        risk_level: ReviewRisk,
        gate_status: GateStatus,
        risk_score: int,
        summary: str,
        reasons: List[str],
        critical_files: List[str],
        policy_evaluations: List[Dict[str, Any]],
        pull_request_id: Optional[UUID] = None,
        review_id: Optional[UUID] = None,
        test_run_id: Optional[UUID] = None,
        actor_id: Optional[UUID] = None,
        actor_type: ActorType = ActorType.SYSTEM,
    ) -> DeploymentGate:
        """Create a new deployment risk gate and initialize its first audit log."""
        gate = DeploymentGate(
            project_id=project_id,
            pull_request_id=pull_request_id,
            review_id=review_id,
            test_run_id=test_run_id,
            risk_level=risk_level.value if isinstance(risk_level, ReviewRisk) else risk_level,
            gate_status=gate_status.value if isinstance(gate_status, GateStatus) else gate_status,
            risk_score=risk_score,
            summary=summary,
            reasons=reasons,
            critical_files=critical_files,
            policy_evaluations=policy_evaluations,
        )
        self.db.add(gate)
        self.db.flush()

        # Create initial audit log entry
        initial_action = (
            GateAction.APPROVAL_REQUESTED
            if gate.gate_status == GateStatus.REQUIRES_APPROVAL.value
            else GateAction.EVALUATED
        )
        audit_log = GateAuditLog(
            gate_id=gate.id,
            action=initial_action.value,
            actor_id=actor_id,
            actor_type=actor_type.value if isinstance(actor_type, ActorType) else actor_type,
            previous_status=None,
            new_status=gate.gate_status,
            reason="Initial automated safety gate evaluation completed.",
            audit_metadata={
                "risk_score": risk_score,
                "risk_level": gate.risk_level,
                "critical_files_count": len(critical_files),
            },
        )
        self.db.add(audit_log)
        self.db.flush()

        return gate

    def get_by_id(self, gate_id: UUID) -> Optional[DeploymentGate]:
        """Fetch a deployment gate by its UUID."""
        return self.db.query(DeploymentGate).filter(DeploymentGate.id == gate_id).first()

    def get_latest_by_pr(self, pull_request_id: UUID) -> Optional[DeploymentGate]:
        """Fetch the most recent gate evaluation for a given pull request."""
        return (
            self.db.query(DeploymentGate)
            .filter(DeploymentGate.pull_request_id == pull_request_id)
            .order_by(DeploymentGate.created_at.desc())
            .first()
        )

    def list_by_project(
        self,
        project_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[DeploymentGate]:
        """List deployment gates for a project, optionally filtered by status."""
        query = self.db.query(DeploymentGate).filter(DeploymentGate.project_id == project_id)
        if status:
            query = query.filter(DeploymentGate.gate_status == status)
        return query.order_by(DeploymentGate.created_at.desc()).offset(offset).limit(limit).all()

    def update_gate_status(
        self,
        gate_id: UUID,
        action: GateAction,
        new_status: GateStatus,
        actor_id: Optional[UUID],
        actor_type: ActorType = ActorType.USER,
        reason: Optional[str] = None,
        approval_notes: Optional[str] = None,
        bypass_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[DeploymentGate]:
        """Update a gate status and record an immutable audit log entry."""
        gate = self.get_by_id(gate_id)
        if not gate:
            return None

        previous_status = gate.gate_status
        gate.gate_status = new_status.value if isinstance(new_status, GateStatus) else new_status

        now = datetime.now(timezone.utc)
        if new_status in (GateStatus.APPROVED, GateStatus.BYPASSED):
            gate.approved_by = actor_id
            gate.approved_at = now
            if approval_notes:
                gate.approval_notes = approval_notes
            if bypass_reason:
                gate.bypass_reason = bypass_reason

        # Append immutable audit entry
        audit_log = GateAuditLog(
            gate_id=gate.id,
            action=action.value if isinstance(action, GateAction) else action,
            actor_id=actor_id,
            actor_type=actor_type.value if isinstance(actor_type, ActorType) else actor_type,
            previous_status=previous_status,
            new_status=gate.gate_status,
            reason=reason or approval_notes or bypass_reason,
            audit_metadata=metadata or {},
        )
        self.db.add(audit_log)
        self.db.flush()

        return gate

    def get_audit_logs(self, gate_id: UUID) -> List[GateAuditLog]:
        """Retrieve audit log history for a deployment gate in chronological order."""
        return (
            self.db.query(GateAuditLog)
            .filter(GateAuditLog.gate_id == gate_id)
            .order_by(GateAuditLog.created_at.asc())
            .all()
        )
