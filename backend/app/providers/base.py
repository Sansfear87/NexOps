"""Deployment Provider Abstraction for AI DevOps Assistant.

Adheres strictly to contracts/deployment_contract.md.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DeploymentState(str, Enum):
    PENDING = "PENDING"
    BUILDING = "BUILDING"
    TESTING = "TESTING"
    APPROVED = "APPROVED"
    DEPLOYING = "DEPLOYING"
    HEALTH_CHECK = "HEALTH_CHECK"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"


class DeploymentRequest(BaseModel):
    deployment_id: str
    project_id: str
    environment: str = Field(..., description="staging or production")
    commit_sha: str
    branch: Optional[str] = None
    provider: str = Field(..., description="vercel, render, or nebius")
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeploymentResponse(BaseModel):
    deployment_id: str
    provider_deployment_id: str
    state: DeploymentState
    url: Optional[str] = None
    created_at: str


class DeploymentStatusResponse(BaseModel):
    deployment_id: str
    provider_deployment_id: str
    state: DeploymentState
    url: Optional[str] = None
    error_summary: Optional[str] = None
    updated_at: str


class LogLine(BaseModel):
    timestamp: str
    source: str = "build"  # build, stdout, stderr, health_check
    message: str


class DeploymentLogsResponse(BaseModel):
    deployment_id: str
    lines: List[LogLine] = Field(default_factory=list)


class RollbackRequest(BaseModel):
    deployment_id: str
    target_deployment_id: Optional[str] = None
    reason: str


class RollbackResponse(BaseModel):
    rollback_id: str
    state: DeploymentState
    target_version: str
    initiated_at: str


class DeploymentProvider(ABC):
    """Abstract interface defining the contract for all deployment providers."""

    provider_name: str

    @abstractmethod
    async def deploy(self, request: DeploymentRequest) -> DeploymentResponse:
        """Trigger deployment on the target provider."""
        pass

    @abstractmethod
    async def get_status(self, provider_deployment_id: str) -> DeploymentStatusResponse:
        """Fetch normalized state of the deployment from the provider."""
        pass

    @abstractmethod
    async def get_logs(self, provider_deployment_id: str, tail: int = 100) -> DeploymentLogsResponse:
        """Fetch logs from the provider build or runtime stream."""
        pass

    @abstractmethod
    async def rollback(self, request: RollbackRequest) -> RollbackResponse:
        """Revert the active deployment to a prior target version."""
        pass
