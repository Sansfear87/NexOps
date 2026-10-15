"""Context Engine for synthesizing operational and code context for AI agents."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.orm import Session

from app.db.constants import EventType
from app.db.repositories.github_connection_repository import GitHubConnectionRepository
from app.db.repositories.platform_event_repository import PlatformEventRepository
from app.db.repositories.project_repository import ProjectRepository
from app.db.repositories.pull_request_repository import PullRequestRepository
from app.services.diff_parser import DiffParser
from app.services.github_service import GitHubService

logger = logging.getLogger(__name__)


class ContextEngine:
    """Assembles and optimizes contextual metadata for agent reasoning tasks."""

    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.connection_repo = GitHubConnectionRepository(db)
        self.pr_repo = PullRequestRepository(db)
        self.event_repo = PlatformEventRepository(db)
        self.diff_parser = DiffParser()

    def _truncate_to_token_budget(self, text: str, max_tokens: int = 8000) -> str:
        """Truncate text to approximate token budget using ~4 characters per token heuristic."""
        if not text:
            return ""
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        head_chars = int(max_chars * 0.7)
        tail_chars = int(max_chars * 0.25)
        truncation_notice = (
            f"\n\n... [TRUNCATED {len(text) - (head_chars + tail_chars)} CHARACTERS TO RESPECT {max_tokens} TOKEN BUDGET] ...\n\n"
        )
        return text[:head_chars] + truncation_notice + text[-tail_chars:]

    def build_pr_review_context(
        self, project_id: uuid.UUID, pull_number: int
    ) -> Dict[str, Any]:
        """Assemble complete context for reviewing a pull request."""
        project = self.project_repo.get_by_id(project_id)
        connections = self.connection_repo.get_by_project(project_id)
        if not connections:
            raise ValueError(f"No GitHub connection found for project {project_id}.")

        conn = connections[0]
        github_service = GitHubService(self.db)
        pr = github_service.get_pull_request(conn.id, pull_number)
        if not pr:
            raise ValueError(f"Pull request #{pull_number} could not be resolved.")

        # Ensure diff is cached or fetch it
        diff_text = pr.diff_text
        if not diff_text:
            try:
                diff_res = github_service.get_diff(conn.id, pull_number)
                diff_text = diff_res.get("diff_text", "")
            except Exception as exc:
                logger.warning("Could not fetch diff text during context build: %s", exc)
                diff_text = ""

        # Parse diff structure
        file_diffs = self.diff_parser.parse_unified_diff(diff_text or "")
        diff_summary = self.diff_parser.summarize(file_diffs)

        files_metadata = [
            {
                "filename": fd.filename,
                "status": fd.status,
                "additions": fd.additions,
                "deletions": fd.deletions,
                "language": fd.language,
                "changed_functions": self.diff_parser.get_changed_functions(fd),
            }
            for fd in file_diffs
        ]

        # Recent project events for situational awareness
        recent_events = self.event_repo.get_recent(project_id, limit=10)
        recent_events_summary = [
            {"event_type": e.event_type, "timestamp": e.created_at.isoformat()}
            for e in recent_events
        ]

        return {
            "context_type": "pr_review",
            "project": {
                "id": str(project.id) if project else str(project_id),
                "name": project.name if project else "Unknown",
                "slug": project.slug if project else "unknown",
            },
            "repository": {
                "owner": conn.owner,
                "name": conn.repo_name,
                "default_branch": conn.default_branch,
            },
            "pull_request": {
                "number": pr.pull_number,
                "title": pr.title,
                "author": pr.author,
                "head_branch": pr.head_branch,
                "base_branch": pr.base_branch,
                "head_sha": pr.head_sha,
                "body": pr.body or "",
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files_count": pr.changed_files,
            },
            "diff_summary": diff_summary,
            "changed_files": files_metadata,
            "diff_content": self._truncate_to_token_budget(diff_text or "", max_tokens=6000),
            "recent_events": recent_events_summary,
        }

    def build_deployment_context(
        self, project_id: uuid.UUID, environment: str = "staging"
    ) -> Dict[str, Any]:
        """Assemble context for deploying an application to target environment."""
        project = self.project_repo.get_by_id(project_id)
        connections = self.connection_repo.get_by_project(project_id)
        conn = connections[0] if connections else None

        recent_events = self.event_repo.get_recent(project_id, limit=20)
        deploy_events = [
            e for e in recent_events
            if e.event_type in (
                EventType.DEPLOYMENT_STARTED.value,
                EventType.DEPLOYMENT_COMPLETED.value,
                EventType.DEPLOYMENT_FAILED.value,
                EventType.TEST_COMPLETED.value,
            )
        ]

        return {
            "context_type": "deployment",
            "project_id": str(project_id),
            "project_name": project.name if project else "Unknown",
            "target_environment": environment,
            "repository": {
                "owner": conn.owner if conn else "",
                "name": conn.repo_name if conn else "",
                "default_branch": conn.default_branch if conn else "main",
            },
            "recent_deployments": [
                {
                    "event_type": de.event_type,
                    "payload": de.payload,
                    "timestamp": de.created_at.isoformat(),
                }
                for de in deploy_events
            ],
        }

    def build_incident_context(
        self, project_id: uuid.UUID, deployment_id: str
    ) -> Dict[str, Any]:
        """Assemble diagnostic context for an incident or deployment failure."""
        project = self.project_repo.get_by_id(project_id)
        recent_events = self.event_repo.get_recent(project_id, limit=30)

        incident_related_events = [
            {
                "event_type": e.event_type,
                "payload": e.payload,
                "timestamp": e.created_at.isoformat(),
            }
            for e in recent_events
            if e.event_type in (
                EventType.HEALTH_CHECK_FAILED.value,
                EventType.DEPLOYMENT_FAILED.value,
                EventType.INCIDENT_CREATED.value,
            )
        ]

        return {
            "context_type": "incident_diagnosis",
            "project_id": str(project_id),
            "project_name": project.name if project else "Unknown",
            "deployment_id": deployment_id,
            "incident_events": incident_related_events,
        }
