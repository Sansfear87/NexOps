"""Repository for Deployment and DeploymentLog database operations."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.constants import DeploymentEnvironment, DeploymentProviderType, DeploymentState
from app.db.models.deployment import Deployment, DeploymentLog
from app.db.repositories.base import BaseRepository


class DeploymentRepository(BaseRepository[Deployment]):
    """Repository handling Deployment state machines and streaming logs."""

    def __init__(self, db: Session):
        super().__init__(Deployment, db)

    def create_deployment(
        self,
        project_id: UUID,
        provider: str,
        environment: str,
        commit_sha: str,
        branch: str = "main",
        pull_request_id: Optional[UUID] = None,
        gate_id: Optional[UUID] = None,
        configuration: Optional[Dict[str, Any]] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
        initial_state: str = DeploymentState.PENDING.value,
    ) -> Deployment:
        """Create a new deployment record."""
        dep = Deployment(
            project_id=project_id,
            pull_request_id=pull_request_id,
            gate_id=gate_id,
            provider=provider,
            environment=environment,
            commit_sha=commit_sha,
            branch=branch,
            state=initial_state,
            configuration=configuration or {},
            metadata_json=metadata_json or {},
        )
        self.db.add(dep)
        self.db.flush()
        return dep

    def get_by_id(self, deployment_id: UUID) -> Optional[Deployment]:
        """Fetch deployment by UUID."""
        return self.db.query(Deployment).filter(Deployment.id == deployment_id).first()

    def list_by_project(
        self,
        project_id: UUID,
        environment: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Deployment]:
        """List deployments for a project, newest first."""
        query = self.db.query(Deployment).filter(Deployment.project_id == project_id)
        if environment:
            query = query.filter(Deployment.environment == environment)
        return query.order_by(Deployment.created_at.desc()).offset(offset).limit(limit).all()

    def update_state(
        self,
        deployment_id: UUID,
        new_state: DeploymentState,
        url: Optional[str] = None,
        error_summary: Optional[str] = None,
        provider_deployment_id: Optional[str] = None,
    ) -> Optional[Deployment]:
        """Transition deployment state machine."""
        dep = self.get_by_id(deployment_id)
        if not dep:
            return None

        state_val = new_state.value if isinstance(new_state, DeploymentState) else new_state
        dep.state = state_val
        if url:
            dep.url = url
        if error_summary:
            dep.error_summary = error_summary
        if provider_deployment_id:
            dep.provider_deployment_id = provider_deployment_id

        if state_val in (DeploymentState.SUCCESS.value, DeploymentState.FAILED.value, DeploymentState.ROLLED_BACK.value):
            dep.completed_at = datetime.now(timezone.utc)

        self.db.flush()
        return dep

    def add_log(
        self,
        deployment_id: UUID,
        source: str,
        message: str,
        timestamp: Optional[datetime] = None,
    ) -> DeploymentLog:
        """Append a log line to the deployment stream."""
        log = DeploymentLog(
            deployment_id=deployment_id,
            source=source,
            message=message,
            timestamp=timestamp or datetime.now(timezone.utc),
        )
        self.db.add(log)
        self.db.flush()
        return log

    def get_logs(self, deployment_id: UUID, tail: int = 100) -> List[DeploymentLog]:
        """Fetch the most recent log lines for a deployment."""
        return (
            self.db.query(DeploymentLog)
            .filter(DeploymentLog.deployment_id == deployment_id)
            .order_by(DeploymentLog.timestamp.asc())
            .limit(tail)
            .all()
        )

    def get_last_successful(self, project_id: UUID, environment: str) -> Optional[Deployment]:
        """Fetch the most recent SUCCESS deployment for this environment (for safe rollback target)."""
        return (
            self.db.query(Deployment)
            .filter(
                Deployment.project_id == project_id,
                Deployment.environment == environment,
                Deployment.state == DeploymentState.SUCCESS.value,
            )
            .order_by(Deployment.created_at.desc())
            .first()
        )
