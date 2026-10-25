"""Repository for Incident and DiagnosisRun database operations."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.constants import IncidentSeverity, IncidentStatus, RemediationAction
from app.db.models.incident import DiagnosisRun, Incident
from app.db.repositories.base import BaseRepository


class IncidentRepository(BaseRepository[Incident]):
    """Repository managing incident records, autonomous diagnosis runs, and mitigations."""

    def __init__(self, db: Session):
        super().__init__(Incident, db)

    def create_incident(
        self,
        project_id: UUID,
        title: str,
        description: Optional[str] = None,
        severity: str = IncidentSeverity.SEV2.value,
        deployment_id: Optional[UUID] = None,
        target_stable_version: Optional[str] = None,
    ) -> Incident:
        """Create a new incident ticket."""
        inc = Incident(
            project_id=project_id,
            deployment_id=deployment_id,
            title=title,
            description=description,
            severity=severity,
            status=IncidentStatus.OPEN.value,
            target_stable_version=target_stable_version,
        )
        self.db.add(inc)
        self.db.flush()
        return inc

    def get_by_id(self, incident_id: UUID) -> Optional[Incident]:
        """Fetch incident by UUID with diagnoses."""
        return self.db.query(Incident).filter(Incident.id == incident_id).first()

    def list_by_project(
        self,
        project_id: UUID,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Incident]:
        """List incidents for a project, newest first."""
        query = self.db.query(Incident).filter(Incident.project_id == project_id)
        if status:
            query = query.filter(Incident.status == status)
        return query.order_by(Incident.created_at.desc()).limit(limit).all()

    def update_status(
        self,
        incident_id: UUID,
        status: IncidentStatus,
        root_cause_summary: Optional[str] = None,
        recommended_action: Optional[RemediationAction] = None,
    ) -> Optional[Incident]:
        """Update incident progress and resolution."""
        inc = self.get_by_id(incident_id)
        if not inc:
            return None

        status_val = status.value if isinstance(status, IncidentStatus) else status
        inc.status = status_val
        if root_cause_summary:
            inc.root_cause_summary = root_cause_summary
        if recommended_action:
            inc.recommended_action = recommended_action.value if isinstance(recommended_action, RemediationAction) else recommended_action

        if status_val in (IncidentStatus.RESOLVED.value, IncidentStatus.CLOSED.value):
            inc.resolved_at = datetime.now(timezone.utc)

        self.db.flush()
        return inc

    def create_diagnosis_run(
        self,
        incident_id: UUID,
        diagnosis_summary: str,
        recommended_action: str = RemediationAction.ROLLBACK.value,
        suspected_commits: Optional[List[Dict[str, Any]]] = None,
        logs_analyzed: Optional[List[str]] = None,
        agent_run_id: Optional[UUID] = None,
    ) -> DiagnosisRun:
        """Persist a diagnosis execution analyzing logs and diffs."""
        diag = DiagnosisRun(
            incident_id=incident_id,
            agent_run_id=agent_run_id,
            diagnosis_summary=diagnosis_summary,
            recommended_action=recommended_action,
            suspected_commits=suspected_commits or [],
            logs_analyzed=logs_analyzed or [],
        )
        self.db.add(diag)
        self.db.flush()
        return diag
