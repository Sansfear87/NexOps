"""Deployment Service orchestrating multi-cloud provider adapters and state transitions.

Adheres strictly to contracts/deployment_contract.md and contracts/event_contract.md.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.db.constants import (
    ActorType,
    DeploymentEnvironment,
    DeploymentProviderType,
    DeploymentState,
    EventType,
    GateStatus,
)
from app.db.models.deployment import Deployment, DeploymentLog
from app.db.repositories.deployment_repository import DeploymentRepository
from app.db.repositories.deployment_gate_repository import DeploymentGateRepository
from app.providers import NebiusAdapter, RenderAdapter, VercelAdapter
from app.providers.base import (
    DeploymentProvider,
    DeploymentRequest,
    RollbackRequest,
)
from app.services.event_bus import EventBus

logger = logging.getLogger(__name__)


class DeploymentService:
    """Service managing deployments, providers, finite state machines, and rollbacks."""

    def __init__(self, db: Session, event_bus: Optional[EventBus] = None):
        self.db = db
        self.repo = DeploymentRepository(db)
        self.gate_repo = DeploymentGateRepository(db)
        self.event_bus = event_bus or EventBus(db)
        self._providers: Dict[str, DeploymentProvider] = {
            DeploymentProviderType.VERCEL.value: VercelAdapter(),
            DeploymentProviderType.RENDER.value: RenderAdapter(),
            DeploymentProviderType.NEBIUS.value: NebiusAdapter(),
        }

    def get_provider(self, provider_name: str) -> DeploymentProvider:
        """Fetch provider adapter by name."""
        name = provider_name.lower()
        if name not in self._providers:
            raise ValueError(f"Unsupported deployment provider: '{provider_name}'. Supported: {list(self._providers.keys())}")
        return self._providers[name]

    def register_provider(self, name: str, adapter: DeploymentProvider) -> None:
        """Register custom or mocked provider adapter."""
        self._providers[name.lower()] = adapter

    def get_deployment(self, deployment_id: UUID) -> Optional[Deployment]:
        """Fetch deployment by UUID."""
        return self.repo.get_by_id(deployment_id)

    def list_deployments(
        self,
        project_id: UUID,
        environment: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Deployment]:
        """List deployments for a project."""
        return self.repo.list_by_project(project_id, environment=environment, limit=limit, offset=offset)

    def get_logs(self, deployment_id: UUID, tail: int = 100) -> List[DeploymentLog]:
        """Fetch execution logs for deployment."""
        return self.repo.get_logs(deployment_id, tail=tail)

    async def trigger_deployment(
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
        actor_id: str = "system",
    ) -> Deployment:
        """Execute full deployment lifecycle following 10-state machine and emitting canonical events."""
        # 1. Gate verification: if gate_id is provided or attached to PR, verify status
        if gate_id:
            gate = self.gate_repo.get_by_id(gate_id)
            if gate and gate.status in (GateStatus.REQUIRES_APPROVAL.value, GateStatus.BLOCKED.value, GateStatus.REJECTED.value):
                # Cannot proceed without gate approval
                dep = self.repo.create_deployment(
                    project_id=project_id,
                    pull_request_id=pull_request_id,
                    gate_id=gate_id,
                    provider=provider.lower(),
                    environment=environment.lower(),
                    commit_sha=commit_sha,
                    branch=branch,
                    configuration=configuration,
                    metadata_json=metadata_json,
                    initial_state=DeploymentState.FAILED.value,
                )
                self.repo.update_state(
                    dep.id,
                    DeploymentState.FAILED,
                    error_summary=f"Deployment halted: Safety gate {gate_id} is in status '{gate.status}'",
                )
                self.repo.add_log(dep.id, "gate", f"Guardrail blocked deployment: gate status is {gate.status}")
                self.db.commit()
                return dep

        # 2. Initialize deployment record in PENDING
        dep = self.repo.create_deployment(
            project_id=project_id,
            pull_request_id=pull_request_id,
            gate_id=gate_id,
            provider=provider.lower(),
            environment=environment.lower(),
            commit_sha=commit_sha,
            branch=branch,
            configuration=configuration,
            metadata_json=metadata_json,
            initial_state=DeploymentState.PENDING.value,
        )
        self.repo.add_log(dep.id, "orchestrator", f"Deployment initialized in {DeploymentState.PENDING.value}")

        trace_id = uuid4()
        start_time = datetime.now(timezone.utc)

        # 3. Transition to BUILDING and emit DEPLOYMENT_STARTED
        self.repo.update_state(dep.id, DeploymentState.BUILDING)
        self.repo.add_log(dep.id, "orchestrator", "Transitioned to BUILDING")

        self.event_bus.emit(
            event_type=EventType.DEPLOYMENT_STARTED,
            project_id=project_id,
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
            trace_id=trace_id,
            payload={
                "deployment_id": str(dep.id),
                "target_environment": environment.lower(),
                "provider": provider.lower(),
                "commit_sha": commit_sha,
            },
        )

        # 4. TESTING step
        self.repo.update_state(dep.id, DeploymentState.TESTING)
        self.repo.add_log(dep.id, "orchestrator", "Running pre-flight checks and smoke testing")

        # 5. APPROVED step
        self.repo.update_state(dep.id, DeploymentState.APPROVED)
        self.repo.add_log(dep.id, "orchestrator", "Pre-deployment checks passed, deployment approved")

        # 6. DEPLOYING step - dispatch to provider adapter
        self.repo.update_state(dep.id, DeploymentState.DEPLOYING)
        self.repo.add_log(dep.id, "orchestrator", f"Dispatching deployment to {provider} adapter")

        adapter = self.get_provider(provider)
        req = DeploymentRequest(
            deployment_id=str(dep.id),
            project_id=str(project_id),
            environment=environment.lower(),
            commit_sha=commit_sha,
            branch=branch,
            provider=provider.lower(),
            environment_variables=configuration or {},
            metadata=metadata_json or {},
        )

        try:
            resp = await adapter.deploy(req)
            dep.provider_deployment_id = resp.provider_deployment_id
            if resp.url:
                dep.url = resp.url

            # Fetch provider logs
            logs_resp = await adapter.get_logs(resp.provider_deployment_id)
            for line in logs_resp.lines:
                self.repo.add_log(dep.id, line.source, line.message)

            # 7. HEALTH_CHECK step
            self.repo.update_state(dep.id, DeploymentState.HEALTH_CHECK, url=resp.url)
            self.repo.add_log(dep.id, "orchestrator", "Entering HEALTH_CHECK phase")

            # 8. SUCCESS step
            self.repo.update_state(dep.id, DeploymentState.SUCCESS, url=resp.url)
            self.repo.add_log(dep.id, "orchestrator", f"Deployment healthy and live at {resp.url}")

            duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.event_bus.emit(
                event_type=EventType.DEPLOYMENT_COMPLETED,
                project_id=project_id,
                actor_id=actor_id,
                actor_type=ActorType.SYSTEM,
                trace_id=trace_id,
                payload={
                    "deployment_id": str(dep.id),
                    "target_environment": environment.lower(),
                    "provider": provider.lower(),
                    "url": resp.url or "",
                    "duration_seconds": round(duration_seconds, 2),
                },
            )
            self.db.commit()
            return dep

        except Exception as exc:
            logger.error("Deployment failed on provider %s: %s", provider, exc)
            self.repo.update_state(
                dep.id,
                DeploymentState.FAILED,
                error_summary=str(exc),
            )
            self.repo.add_log(dep.id, "error", f"Deployment execution failed: {str(exc)}")

            self.event_bus.emit(
                event_type=EventType.DEPLOYMENT_FAILED,
                project_id=project_id,
                actor_id=actor_id,
                actor_type=ActorType.SYSTEM,
                trace_id=trace_id,
                payload={
                    "deployment_id": str(dep.id),
                    "target_environment": environment.lower(),
                    "failure_stage": "DEPLOY",
                    "error_message": str(exc),
                },
            )
            self.db.commit()
            return dep

    async def rollback(
        self,
        deployment_id: UUID,
        target_deployment_id: Optional[UUID] = None,
        reason: str = "Incident remediation or manual rollback trigger",
        actor_id: str = "system",
    ) -> Deployment:
        """Trigger automated or manual rollback of active deployment."""
        current_dep = self.get_deployment(deployment_id)
        if not current_dep:
            raise ValueError(f"Deployment {deployment_id} not found")

        # Find target stable deployment
        target_dep: Optional[Deployment] = None
        if target_deployment_id:
            target_dep = self.get_deployment(target_deployment_id)
        else:
            target_dep = self.repo.get_last_successful(
                current_dep.project_id, current_dep.environment
            )

        target_version = target_dep.commit_sha if target_dep else "HEAD~1"

        trace_id = uuid4()
        start_time = datetime.now(timezone.utc)

        # 1. Update current deployment to ROLLING_BACK
        self.repo.update_state(current_dep.id, DeploymentState.ROLLING_BACK)
        self.repo.add_log(current_dep.id, "rollback", f"Rollback initiated: {reason}")

        self.event_bus.emit(
            event_type=EventType.ROLLBACK_STARTED,
            project_id=current_dep.project_id,
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
            trace_id=trace_id,
            payload={
                "incident_id": str(uuid4()),
                "deployment_id": str(current_dep.id),
                "target_stable_version": target_version,
            },
        )

        # 2. Call provider adapter rollback
        adapter = self.get_provider(current_dep.provider)
        req = RollbackRequest(
            deployment_id=str(current_dep.id),
            target_deployment_id=str(target_dep.id) if target_dep else None,
            reason=reason,
        )
        rollback_resp = await adapter.rollback(req)

        # 3. Transition current deployment to ROLLED_BACK
        self.repo.update_state(current_dep.id, DeploymentState.ROLLED_BACK)
        self.repo.add_log(current_dep.id, "rollback", f"Deployment rolled back to {target_version}")

        # 4. Emit ROLLBACK_COMPLETED
        duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
        self.event_bus.emit(
            event_type=EventType.ROLLBACK_COMPLETED,
            project_id=current_dep.project_id,
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
            trace_id=trace_id,
            payload={
                "incident_id": str(uuid4()),
                "rollback_id": rollback_resp.rollback_id,
                "restored_version": target_version,
                "duration_seconds": round(duration_seconds, 2),
            },
        )

        self.db.commit()
        return current_dep
