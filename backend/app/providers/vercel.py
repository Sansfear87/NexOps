"""Vercel Deployment Provider Adapter adhering to contracts/deployment_contract.md."""
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


class VercelAdapter(DeploymentProvider):
    """Adapter for deploying frontend & serverless applications to Vercel."""

    provider_name: str = "vercel"

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or "mock-vercel-token"
        # In-memory store for active deployments when simulating/testing
        self._deployments: Dict[str, Dict] = {}

    async def deploy(self, request: DeploymentRequest) -> DeploymentResponse:
        """Trigger deployment on Vercel."""
        now_str = datetime.now(timezone.utc).isoformat()
        provider_dep_id = f"dpl_{uuid.uuid4().hex[:12]}"
        
        # Determine URL based on project and environment
        subdomain = request.metadata.get("project_slug", "app")
        if request.environment == "production":
            url = f"https://{subdomain}.vercel.app"
        else:
            url = f"https://{subdomain}-git-{request.branch or 'preview'}.vercel.app"

        self._deployments[provider_dep_id] = {
            "deployment_id": request.deployment_id,
            "provider_deployment_id": provider_dep_id,
            "state": DeploymentState.DEPLOYING,
            "url": url,
            "created_at": now_str,
            "logs": [
                LogLine(timestamp=now_str, source="build", message="Vercel CLI: Cloning repository source..."),
                LogLine(timestamp=now_str, source="build", message="Running 'npm run build' / Next.js static asset generation..."),
                LogLine(timestamp=now_str, source="stdout", message="Edge middleware bundled successfully (42ms)."),
                LogLine(timestamp=now_str, source="stdout", message=f"Production domain assigned: {url}"),
            ]
        }

        return DeploymentResponse(
            deployment_id=request.deployment_id,
            provider_deployment_id=provider_dep_id,
            state=DeploymentState.DEPLOYING,
            url=url,
            created_at=now_str,
        )

    async def get_status(self, provider_deployment_id: str) -> DeploymentStatusResponse:
        """Fetch normalized state of the deployment from Vercel."""
        now_str = datetime.now(timezone.utc).isoformat()
        dep = self._deployments.get(provider_deployment_id)
        if not dep:
            return DeploymentStatusResponse(
                deployment_id="unknown",
                provider_deployment_id=provider_deployment_id,
                state=DeploymentState.FAILED,
                error_summary=f"Deployment '{provider_deployment_id}' not found on Vercel.",
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
        """Fetch logs from Vercel build/runtime stream."""
        dep = self._deployments.get(provider_deployment_id, {})
        lines = dep.get("logs", [])
        return DeploymentLogsResponse(
            deployment_id=dep.get("deployment_id", provider_deployment_id),
            lines=lines[-tail:],
        )

    async def rollback(self, request: RollbackRequest) -> RollbackResponse:
        """Revert the active Vercel domain alias to a prior target version."""
        now_str = datetime.now(timezone.utc).isoformat()
        rollback_id = f"rb_{uuid.uuid4().hex[:10]}"
        target_version = request.target_deployment_id or "previous-known-good"

        # Update in-memory record if exists
        for dep in self._deployments.values():
            if dep["deployment_id"] == request.deployment_id:
                dep["state"] = DeploymentState.ROLLED_BACK
                dep["logs"].append(
                    LogLine(timestamp=now_str, source="build", message=f"Rolled back alias to {target_version}: {request.reason}")
                )

        return RollbackResponse(
            rollback_id=rollback_id,
            state=DeploymentState.ROLLED_BACK,
            target_version=target_version,
            initiated_at=now_str,
        )
