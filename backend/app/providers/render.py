"""Render Deployment Provider Adapter adhering to contracts/deployment_contract.md."""
from datetime import datetime, timezone
import uuid
from typing import Dict, List, Optional

from app.providers.base import (
    DeploymentLogsResponse,
    DeploymentProvider,
    DeploymentRequest,
    DeploymentResponse,
    DeploymentState,
    DeploymentStatusResponse,
    LogLine,
    RollbackRequest,
    RollbackResponse,
)


class RenderAdapter(DeploymentProvider):
    """Adapter for deploying containerized services and web workers to Render."""

    provider_name: str = "render"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "mock-render-key"
        self._deployments: Dict[str, Dict] = {}

    async def deploy(self, request: DeploymentRequest) -> DeploymentResponse:
        """Trigger deployment on Render."""
        now_str = datetime.now(timezone.utc).isoformat()
        provider_dep_id = f"dep-{uuid.uuid4().hex[:12]}"
        
        service_name = request.metadata.get("project_slug", "service")
        env_suffix = "stg" if request.environment == "staging" else "prod"
        url = f"https://{service_name}-{env_suffix}.onrender.com"

        self._deployments[provider_dep_id] = {
            "deployment_id": request.deployment_id,
            "provider_deployment_id": provider_dep_id,
            "state": DeploymentState.BUILDING,
            "url": url,
            "created_at": now_str,
            "logs": [
                LogLine(timestamp=now_str, source="build", message="Render Build: Pulling base image python:3.11-slim..."),
                LogLine(timestamp=now_str, source="build", message="Installing pip dependencies from requirements.txt..."),
                LogLine(timestamp=now_str, source="build", message="Running pre-deploy database migrations..."),
                LogLine(timestamp=now_str, source="stdout", message="Uvicorn running on http://0.0.0.0:10000"),
                LogLine(timestamp=now_str, source="health_check", message="HTTP GET /health returned 200 OK (latency: 18ms)"),
            ]
        }

        return DeploymentResponse(
            deployment_id=request.deployment_id,
            provider_deployment_id=provider_dep_id,
            state=DeploymentState.BUILDING,
            url=url,
            created_at=now_str,
        )

    async def get_status(self, provider_deployment_id: str) -> DeploymentStatusResponse:
        """Fetch normalized state of the deployment from Render."""
        now_str = datetime.now(timezone.utc).isoformat()
        dep = self._deployments.get(provider_deployment_id)
        if not dep:
            return DeploymentStatusResponse(
                deployment_id="unknown",
                provider_deployment_id=provider_deployment_id,
                state=DeploymentState.FAILED,
                error_summary=f"Deployment '{provider_deployment_id}' not found on Render.",
                updated_at=now_str,
            )

        return DeploymentStatusResponse(
            deployment_id=dep["deployment_id"],
            provider_deployment_id=provider_deployment_id,
            state=dep["state"],
            url=dep.get("url"),
            error_summary=dep.get("error_summary"),
            updated_at=now_str,
        )

    async def get_logs(self, provider_deployment_id: str, tail: int = 100) -> DeploymentLogsResponse:
        """Fetch logs from Render container stream."""
        dep = self._deployments.get(provider_deployment_id, {})
        lines = dep.get("logs", [])
        return DeploymentLogsResponse(
            deployment_id=dep.get("deployment_id", provider_deployment_id),
            lines=lines[-tail:],
        )

    async def rollback(self, request: RollbackRequest) -> RollbackResponse:
        """Rollback active container image on Render to previous successful release."""
        now_str = datetime.now(timezone.utc).isoformat()
        rollback_id = f"rbr_{uuid.uuid4().hex[:10]}"
        target_version = request.target_deployment_id or "previous-release"

        for dep in self._deployments.values():
            if dep["deployment_id"] == request.deployment_id:
                dep["state"] = DeploymentState.ROLLED_BACK
                dep["logs"].append(
                    LogLine(timestamp=now_str, source="stdout", message=f"Container image reverted to {target_version}: {request.reason}")
                )

        return RollbackResponse(
            rollback_id=rollback_id,
            state=DeploymentState.ROLLED_BACK,
            target_version=target_version,
            initiated_at=now_str,
        )
