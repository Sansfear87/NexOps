"""Pydantic schemas for GitHub integration."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse owner and repo name from various GitHub URL formats."""
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]

    patterns = [
        r"^(?:https?:\/\/)?(?:www\.)?github\.com\/([^\/\s]+)\/([^\/\s]+)",
        r"^git@github\.com:([^\/\s]+)\/([^\/\s]+)",
        r"^([a-zA-Z0-9_\-\.]+)\/([a-zA-Z0-9_\-\.]+)$",
    ]
    for pattern in patterns:
        m = re.match(pattern, cleaned)
        if m:
            owner, repo = m.group(1), m.group(2)
            repo = repo.split("/")[0].split("?")[0].split("#")[0]
            return owner, repo
    raise ValueError(f"Could not parse GitHub repository owner and name from URL: '{url}'")


class ConnectRepoRequest(BaseModel):
    """Payload to connect a GitHub repository (supports public link or owner/repo)."""
    url: Optional[str] = Field(None, description="Public GitHub repository URL (e.g. https://github.com/owner/repo or owner/repo)")
    owner: Optional[str] = Field(None, description="Repository owner or organization")
    repo: Optional[str] = Field(None, description="Repository name")
    repo_name: Optional[str] = Field(None, description="Alternative key for repository name")
    token: Optional[str] = Field("", description="GitHub Personal Access Token (optional for public repositories)")
    webhook_secret: Optional[str] = Field(None, description="Optional webhook secret for HMAC-SHA256 verification")
    default_branch: Optional[str] = Field("main", description="Default branch name")

    def resolve_owner_and_repo(self) -> tuple[str, str]:
        """Resolve repository owner and repo name from URL or explicit fields."""
        if self.url and self.url.strip():
            return parse_github_url(self.url)

        if not self.owner or not self.owner.strip():
            raise ValueError("Either 'url' or 'owner' must be provided.")

        repo_val = self.repo or self.repo_name
        if not repo_val or not repo_val.strip():
            raise ValueError("Either 'url' or 'repo'/'repo_name' must be provided.")

        return self.owner.strip(), repo_val.strip()

    def get_repo_name(self) -> str:
        """Return resolved repository name from repo or repo_name."""
        _, r = self.resolve_owner_and_repo()
        return r


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
