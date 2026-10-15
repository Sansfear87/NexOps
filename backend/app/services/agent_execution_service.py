"""Agent Execution Service connecting the ReAct reasoning agent with platform context and tools."""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.orm import Session

# Add NexOps root to sys.path to enable importing agent package
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from agent.interface import (
    ActorContext,
    AgentContext,
    AgentResult,
    RepositoryContext,
)
from agent.react_agent import ReActAgent
from app.core.security import decrypt_token
from app.db.constants import ActorType, EventType
from app.db.repositories.github_connection_repository import GitHubConnectionRepository
from app.db.repositories.project_repository import ProjectRepository
from app.services.event_bus import EventBus
from app.services.tool_execution_service import ToolExecutionService

logger = logging.getLogger(__name__)

DEFAULT_AGENT_PERMISSIONS: List[str] = [
    "repo:read",
    "repo:write",
    "test:run",
    "deploy:staging",
    "deploy:production",
    "logs:read",
    "metrics:read",
    "k8s:read",
    "k8s:write",
]


class AgentExecutionService:
    """Orchestrates ReActAgent invocations with database context and event emission."""

    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.connection_repo = GitHubConnectionRepository(db)
        self.event_bus = EventBus(db)
        self.tool_service = ToolExecutionService(db)

    async def run_agent(
        self,
        goal: str,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        environment: str = "staging",
        tools: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute autonomous ReActAgent on behalf of user to accomplish a DevOps goal.

        Args:
            goal: Natural language objective.
            project_id: Target project UUID.
            user_id: Requesting user UUID.
            environment: Operating environment (e.g., development, staging, production).
            tools: Optional tool names whitelist.
            permissions: Explicit granted permission tokens.
            metadata: Supplemental non-sensitive contextual dictionary.

        Returns:
            Dictionary matching AgentResult schema.
        """
        meta = metadata.copy() if metadata else {}
        perms = permissions if permissions is not None else DEFAULT_AGENT_PERMISSIONS

        project = self.project_repo.get_by_id(project_id)
        connections = self.connection_repo.get_by_project(project_id)
        conn = connections[0] if connections else None

        github_token = ""
        owner = "unknown"
        repo_name = "unknown"
        default_branch = "main"

        if conn:
            owner = conn.owner
            repo_name = conn.repo_name
            default_branch = conn.default_branch
            github_token = decrypt_token(conn.personal_access_token_hash or "")

        run_id_str = str(uuid.uuid4())
        trace_id_uuid = uuid.uuid4()
        trace_id_str = str(trace_id_uuid)

        # 1. Build Agent Context
        agent_context = AgentContext(
            trace_id=trace_id_str,
            run_id=run_id_str,
            project_id=str(project_id),
            repository=RepositoryContext(
                owner=owner,
                name=repo_name,
                default_branch=default_branch,
                current_ref=meta.get("ref", default_branch),
            ),
            actor=ActorContext(
                id=str(user_id),
                type="USER",
            ),
            environment=environment,
            initiated_at=datetime.now(timezone.utc).isoformat(),
            permissions=perms,
            metadata=meta,
        )

        # 2. Build Tool Context and Tool Executor
        tool_ctx = {
            "trace_id": trace_id_str,
            "run_id": run_id_str,
            "project_id": str(project_id),
            "owner": owner,
            "repo": repo_name,
            "github_token": github_token,
            "environment": environment,
            "actor": {"id": str(user_id), "type": "USER"},
        }
        tool_executor = self.tool_service.get_tool_executor(
            permissions=perms, context=tool_ctx
        )

        # 3. Available Tools
        available_tools = (
            tools
            if tools is not None
            else [t["name"] for t in self.tool_service.list_available_tools()]
        )

        # 4. Emit Lifecycle Event: REVIEW_STARTED if goal indicates review
        is_review = "review" in goal.lower() or meta.get("context_type") == "pr_review"
        if is_review:
            self.event_bus.emit(
                event_type=EventType.REVIEW_STARTED,
                project_id=project_id,
                actor_id=str(user_id),
                actor_type=ActorType.AGENT,
                payload={
                    "pull_number": meta.get("pull_number", 1),
                    "head_sha": meta.get("head_sha", "HEAD"),
                    "review_run_id": run_id_str,
                },
                trace_id=trace_id_uuid,
            )

        # 5. Initialize ReActAgent
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "mock-deepseek-key")
        agent = ReActAgent(
            api_key=deepseek_key,
            tool_executor=tool_executor,
        )

        # 6. Execute Agent Loop
        result: AgentResult = await agent.run(
            goal=goal,
            context=agent_context,
            tools=available_tools,
            permissions=perms,
        )

        # 7. Emit Completion Event
        if is_review:
            verdict = "APPROVE"
            if isinstance(result.output, dict):
                verdict = result.output.get("verdict", "APPROVE")
            self.event_bus.emit(
                event_type=EventType.REVIEW_COMPLETED,
                project_id=project_id,
                actor_id=str(user_id),
                actor_type=ActorType.AGENT,
                payload={
                    "pull_number": meta.get("pull_number", 1),
                    "head_sha": meta.get("head_sha", "HEAD"),
                    "review_run_id": run_id_str,
                    "overall_risk": result.output.get("overall_risk", "LOW")
                    if isinstance(result.output, dict)
                    else "LOW",
                    "findings_count": len(result.output.get("findings", []))
                    if isinstance(result.output, dict)
                    and isinstance(result.output.get("findings"), list)
                    else 0,
                    "verdict": verdict,
                },
                trace_id=trace_id_uuid,
            )

        return result.model_dump()
