import sys
from pathlib import Path
import pytest

# Ensure root workspace is in sys.path so 'agent' package is importable
workspace_root = Path(__file__).resolve().parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from agent.interface import (
    AgentContext,
    RepositoryContext,
    ActorContext,
    AgentStatus,
)
from agent.mock_agent import MockAgent
from app.tools.base import BaseTool, ToolRegistry
from app.providers.base import DeploymentState


class SampleGetPrTool(BaseTool):
    name = "github.get_pull_request"
    description = "Mock PR fetcher"
    input_schema = {"type": "object", "required": ["pull_number"]}
    output_schema = {"type": "object", "required": ["id", "title"]}
    required_permissions = ["repo:read"]

    async def execute(self, parameters, context):
        return {"id": 123, "title": "Test PR", "pull_number": parameters["pull_number"]}


def test_tool_registry_permission_enforcement():
    async def _run():
        registry = ToolRegistry()
        registry.register(SampleGetPrTool())

        context = {"trace_id": "test-trace", "run_id": "test-run"}

        # Test permission denial
        envelope_denied = await registry.dispatch(
            tool_name="github.get_pull_request",
            parameters={"pull_number": 42},
            context=context,
            granted_permissions=[],  # Missing repo:read
        )
        assert envelope_denied.status == "PERMISSION_DENIED"
        assert envelope_denied.error is not None
        assert envelope_denied.error.code == "PERMISSION_DENIED"
        assert envelope_denied.error.retryable is False

        # Test permission granted
        envelope_allowed = await registry.dispatch(
            tool_name="github.get_pull_request",
            parameters={"pull_number": 42},
            context=context,
            granted_permissions=["repo:read"],
        )
        assert envelope_allowed.status == "SUCCESS"
        assert envelope_allowed.data == {"id": 123, "title": "Test PR", "pull_number": 42}

    import asyncio
    asyncio.run(_run())


def test_mock_agent_contract_adherence():
    async def _run():
        agent = MockAgent()
        context = AgentContext(
            trace_id="00000000-0000-0000-0000-000000000001",
            run_id="00000000-0000-0000-0000-000000000002",
            project_id="proj-demo-1",
            repository=RepositoryContext(
                owner="octocat",
                name="hello-world",
                default_branch="main"
            ),
            actor=ActorContext(id="user-1", type="USER"),
            environment="staging",
            initiated_at="2026-09-23T12:00:00Z",
            permissions=["repo:read"],
            metadata={"pull_number": 42}
        )

        result = await agent.run(
            goal="Review PR #42",
            context=context,
            tools=["github.get_pull_request"],
            permissions=["repo:read"]
        )

        assert result.status == AgentStatus.COMPLETED
        assert result.confidence >= 0.0 and result.confidence <= 1.0
        assert result.run_id == context.run_id
        assert len(result.actions_taken) == 1
        assert result.actions_taken[0].tool_name == "github.get_pull_request"

    import asyncio
    asyncio.run(_run())


def test_canonical_deployment_states():
    # Verify the 10 canonical states exist
    states = [s.value for s in DeploymentState]
    expected = [
        "PENDING", "BUILDING", "TESTING", "APPROVED", "DEPLOYING",
        "HEALTH_CHECK", "SUCCESS", "FAILED", "ROLLING_BACK", "ROLLED_BACK"
    ]
    for exp in expected:
        assert exp in states
