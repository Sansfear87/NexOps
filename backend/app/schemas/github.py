"""Pydantic schemas for GitHub integration."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ConnectRepoRequest(BaseModel):
    """Payload to connect a GitHub repository."""
    owner: str = Field(..., description="Repository owner or organization")
    repo: Optional[str] = Field(None, description="Repository name")
    repo_name: Optional[str] = Field(None, description="Alternative key for repository name")
    token: str = Field(..., description="GitHub Personal Access Token")
    webhook_secret: Optional[str] = Field(None, description="Optional webhook secret for HMAC-SHA256 verification")
    default_branch: Optional[str] = Field("main", description="Default branch name")

    def get_repo_name(self) -> str:
        """Return resolved repository name from repo or repo_name."""
        val = self.repo or self.repo_name
        if not val:
            raise ValueError("Either 'repo' or 'repo_name' must be provided.")
        return val.strip()


class GitHubConnectionRead(BaseModel):
    """Safe representation of a GitHub repository connection."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    owner: str
    repo_name: str
    default_branch: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PullRequestRead(BaseModel):
    """Representation of a synchronized Pull Request."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    github_connection_id: uuid.UUID
    pull_number: int
    title: str
    state: str
    author: str
    head_branch: str
    base_branch: str
    head_sha: str
    body: Optional[str] = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    diff_text: Optional[str] = None
    github_created_at: Optional[datetime] = None
    github_updated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PullRequestDiffResponse(BaseModel):
    """PR diff response payload."""
    pull_number: int
    diff_text: str
    files_changed: List[Dict[str, Any]]
