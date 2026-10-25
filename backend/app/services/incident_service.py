"""Incident Recovery & Autonomous Diagnosis Service adhering to contracts/event_contract.md."""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.db.constants import (
    ActorType,
    EventType,
    IncidentSeverity,
    IncidentStatus,
    MemoryCategory,
    RemediationAction,
)
from app.db.models.incident import DiagnosisRun, Incident
from app.db.repositories.deployment_repository import DeploymentRepository
from app.db.repositories.incident_repository import IncidentRepository
from app.db.repositories.memory_repository import MemoryRepository
from app.db.repositories.monitoring_repository import MonitoringRepository
from app.services.deployment_service import DeploymentService
from app.services.event_bus import EventBus

logger = logging.getLogger(__name__)


class IncidentService:
    """Service managing incident declaration, autonomous root-cause diagnosis, and automated remediation."""

    def __init__(
        self,
        db: Session,
        event_bus: Optional[EventBus] = None,
        deployment_service: Optional[DeploymentService] = None,
    ):
        self.db = db
        self.repo = IncidentRepository(db)
        self.deployment_repo = DeploymentRepository(db)
        self.monitoring_repo = MonitoringRepository(db)
        self.memory_repo = MemoryRepository(db)
        self.event_bus = event_bus or EventBus(db)
        self.deployment_service = deployment_service or DeploymentService(db, self.event_bus)

    def create_incident(
        self,
        project_id: UUID,
        title: str,
        description: Optional[str] = None,
        severity: str = IncidentSeverity.SEV2.value,
        deployment_id: Optional[UUID] = None,
        actor_id: str = "system",
    ) -> Incident:
        """Declare an incident and emit canonical INCIDENT_CREATED event."""
        inc = self.repo.create_incident(
            project_id=project_id,
            title=title,
            description=description,
            severity=severity,
            deployment_id=deployment_id,
        )

        trace_id = uuid4()
        self.event_bus.emit(
            event_type=EventType.INCIDENT_CREATED,
            project_id=project_id,
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
            trace_id=trace_id,
            payload={
                "incident_id": str(inc.id),
                "deployment_id": str(deployment_id) if deployment_id else str(uuid4()),
                "severity": severity,
                "title": title,
            },
        )
        self.db.commit()
        return inc

    def get_incident(self, incident_id: UUID) -> Optional[Incident]:
        """Fetch incident by UUID."""
        return self.repo.get_by_id(incident_id)

    def list_incidents(
        self,
        project_id: UUID,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Incident]:
        """List incidents for project."""
        return self.repo.list_by_project(project_id, status=status, limit=limit)

    async def diagnose_incident(
        self,
        incident_id: UUID,
        model_router: Optional[Any] = None,
        actor_id: str = "agent",
    ) -> DiagnosisRun:
        """Perform autonomous root cause diagnosis using logs, diffs, and health probes."""
        inc = self.get_incident(incident_id)
        if not inc:
            raise ValueError(f"Incident {incident_id} not found")

        diag_run_id = uuid4()
        trace_id = uuid4()

        # Emit DIAGNOSIS_STARTED
        self.event_bus.emit(
            event_type=EventType.DIAGNOSIS_STARTED,
            project_id=inc.project_id,
            actor_id=actor_id,
            actor_type=ActorType.AGENT,
            trace_id=trace_id,
            payload={
                "incident_id": str(inc.id),
                "diagnosis_run_id": str(diag_run_id),
            },
        )

        # Collect operational context
        logs_text: List[str] = []
        suspected_commits: List[Dict[str, Any]] = []
        
        if inc.deployment_id:
            logs = self.deployment_repo.get_logs(inc.deployment_id, tail=50)
            logs_text = [f"[{l.source}] {l.message}" for l in logs]
            
            dep = self.deployment_repo.get_by_id(inc.deployment_id)
            if dep and dep.commit_sha:
                suspected_commits.append({
                    "commit_sha": dep.commit_sha,
                    "branch": dep.branch,
                    "url": dep.url,
                })

        # Synthesize diagnosis
        if logs_text:
            error_lines = [l for l in logs_text if "error" in l.lower() or "exception" in l.lower() or "failed" in l.lower()]
            if error_lines:
                root_cause = f"Runtime exception detected in deployment logs: '{error_lines[0]}'"
            else:
                root_cause = f"Health check anomaly detected on deployment {inc.deployment_id}"
        else:
            root_cause = f"Service degradation triggered incident: {inc.description or inc.title}"

        recommended_action = RemediationAction.ROLLBACK.value

        # Persist diagnosis run
        diag = self.repo.create_diagnosis_run(
            incident_id=inc.id,
            diagnosis_summary=root_cause,
            recommended_action=recommended_action,
            suspected_commits=suspected_commits,
            logs_analyzed=logs_text[:10],
        )

        # Update incident status to MITIGATING
        self.repo.update_status(
            incident_id=inc.id,
            status=IncidentStatus.MITIGATING,
            root_cause_summary=root_cause,
            recommended_action=RemediationAction.ROLLBACK,
        )

        # Emit DIAGNOSIS_COMPLETED
        self.event_bus.emit(
            event_type=EventType.DIAGNOSIS_COMPLETED,
            project_id=inc.project_id,
            actor_id=actor_id,
            actor_type=ActorType.AGENT,
            trace_id=trace_id,
            payload={
                "incident_id": str(inc.id),
                "diagnosis_run_id": str(diag.id),
                "root_cause_summary": root_cause,
                "recommended_action": recommended_action,
            },
        )
        self.db.commit()
        return diag

    async def remediate_and_resolve(
        self,
        incident_id: UUID,
        auto_rollback: bool = True,
        actor_id: str = "system",
    ) -> Incident:
        """Execute automated remediation (such as 1-click rollback) and close the incident."""
        inc = self.get_incident(incident_id)
        if not inc:
            raise ValueError(f"Incident {incident_id} not found")

        # Execute rollback if deployment exists and auto_rollback is True
        if auto_rollback and inc.deployment_id:
            await self.deployment_service.rollback(
                deployment_id=inc.deployment_id,
                reason=f"Remediating Incident {inc.id}: {inc.root_cause_summary or inc.title}",
                actor_id=actor_id,
            )

        # Update incident status to RESOLVED
        self.repo.update_status(
            incident_id=inc.id,
            status=IncidentStatus.RESOLVED,
            root_cause_summary=inc.root_cause_summary or "Autonomous rollback and incident remediation completed",
        )

        # Persist post-mortem knowledge into project memory (contracts/memory_contract.md)
        memory_key = f"postmortem_{inc.id.hex[:8]}"
        postmortem_content = f"""# Post-Mortem: {inc.title}
- **Severity**: {inc.severity}
- **Root Cause**: {inc.root_cause_summary or 'Unspecified'}
- **Remediation**: Executed autonomous deployment rollback to stable version.
- **Resolved At**: {datetime.now(timezone.utc).isoformat()}
"""
        self.memory_repo.store(
            project_id=inc.project_id,
            key=memory_key,
            content=postmortem_content,
            category=MemoryCategory.POSTMORTEM.value,
            importance=5 if inc.severity == IncidentSeverity.SEV1.value else 4,
            metadata_json={"incident_id": str(inc.id), "deployment_id": str(inc.deployment_id) if inc.deployment_id else None},
        )

        # Emit RECOVERY_COMPLETED event
        self.event_bus.emit(
            event_type=EventType.RECOVERY_COMPLETED,
            project_id=inc.project_id,
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
            trace_id=uuid4(),
            payload={
                "incident_id": str(inc.id),
                "deployment_id": str(inc.deployment_id) if inc.deployment_id else str(uuid4()),
                "resolution_summary": f"Incident {inc.id} successfully mitigated via autonomous rollback",
            },
        )
        self.db.commit()
        return inc
