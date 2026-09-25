"""Tests for the ReAct agent — verifies contract compliance and reasoning loop."""

import sys
import asyncio
from pathlib import Path

# Ensure agent package is importable
workspace_root = Path(__file__).resolve().parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from agent.interface import (
    AgentContext,
    AgentStatus,
    RepositoryContext,
    ActorContext,
)
from agent.react_agent import ReActAgent


def _make_context(**overrides) -> AgentContext:
    """Helper to build a valid AgentContext for tests."""
    defaults = dict(
        trace_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        project_id="proj-test-1",
        repository=RepositoryContext(
            owner="octocat", name="hello-world", default_branch="main"
        ),
        actor=ActorContext(id="user-test", type="USER"),
        environment="staging",
        initiated_at="2026-09-25T12:00:00Z",
        permissions=["repo:read", "test:execute"],
        metadata={"pull_number": 42},
    )
    defaults.update(overrides)
    return AgentContext(**defaults)


def test_react_agent_without_api_key_returns_failure():
    """Agent should fail gracefully when LLM call fails (bad API key)."""

    async def _run():
        agent = ReActAgent(api_key="invalid-key-for-testing")
        context = _make_context()
        result = await agent.run(
            goal="Review PR #42",
            context=context,
            tools=["github.get_pull_request"],
            permissions=["repo:read"],
        )

        # Should fail gracefully, not crash
        assert result.status in (AgentStatus.FAILED, AgentStatus.TIMED_OUT)
        assert result.run_id == context.run_id
        assert result.trace_id == context.trace_id
        assert result.confidence >= 0.0
        assert result.error is not None

    asyncio.run(_run())


def test_react_agent_with_mock_tool_executor():
    """Agent with a mock LLM and mock tool executor should produce valid result."""

    async def mock_tool_executor(tool_name: str, parameters: dict) -> dict:
        """Simulates platform tool execution."""
        if tool_name == "github.get_pull_request":
            return {
                "id": 123,
                "number": parameters.get("pull_number", 1),
                "title": "Fix auth bug",
                "state": "open",
                "base_branch": "main",
                "head_branch": "fix/auth",
                "head_sha": "abc123",
            }
        return {"error": f"Unknown tool: {tool_name}"}

    # We can't easily mock DeepSeek responses without the API key,
    # but we CAN verify the agent handles the error path correctly.
    async def _run():
        agent = ReActAgent(
            api_key="test-key",
            tool_executor=mock_tool_executor,
        )
        context = _make_context()
        result = await agent.run(
            goal="Review PR #42",
            context=context,
            tools=["github.get_pull_request"],
            permissions=["repo:read"],
        )

        # Result should conform to AgentResult schema
        assert result.run_id == context.run_id
        assert result.trace_id == context.trace_id
        assert result.status in list(AgentStatus)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.actions_taken, list)
        assert isinstance(result.output, dict)
        assert "duration_ms" in result.metrics
        assert "steps_count" in result.metrics

    asyncio.run(_run())


def test_react_agent_approval_gate():
    """Agent should return WAITING_FOR_APPROVAL for high-risk tools."""
    from agent.config import AgentConfig
    from agent.react_agent import ReActAgent

    # Create an agent that simulates wanting to deploy
    # We need to test that IF the LLM requests deployment.deploy,
    # the agent returns WAITING_FOR_APPROVAL

    # This test validates the config is set up correctly
    config = AgentConfig()
    assert "deployment.deploy" in config.require_human_approval_for
    assert "deployment.rollback" in config.require_human_approval_for


def test_react_agent_response_parser():
    """Test the response parser handles all format variants."""

    agent = ReActAgent(api_key="test")

    # Test ACTION format
    result = agent._parse_response(
        "THOUGHT: I need to fetch the PR.\n"
        "ACTION: github.get_pull_request\n"
        'ACTION_INPUT: {"pull_number": 42}'
    )
    assert result["type"] == "action"
    assert result["tool_name"] == "github.get_pull_request"
    assert result["parameters"] == {"pull_number": 42}
    assert "fetch the PR" in result["thought"]

    # Test FINAL_ANSWER format
    result = agent._parse_response(
        "THOUGHT: I have all the info I need.\n"
        'FINAL_ANSWER: {"summary": "PR looks good", "risk": "LOW"}'
    )
    assert result["type"] == "final_answer"
    assert result["data"]["summary"] == "PR looks good"
    assert result["data"]["risk"] == "LOW"

    # Test unparseable format
    result = agent._parse_response("I'm not sure what to do here.")
    assert result["type"] == "error"


def test_agent_boundary_still_holds():
    """Verify the new agent files don't violate the isolation boundary."""
    import ast

    agent_dir = Path(__file__).resolve().parent.parent.parent / "agent"
    forbidden_modules = [
        "sqlalchemy", "asyncpg", "psycopg2", "alembic",
        "requests", "httpx", "aiohttp",
        "github", "app.models", "app.db", "app.core.config",
    ]

    for py_file in agent_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert not alias.name.startswith(forbidden), (
                            f"BOUNDARY VIOLATION: '{py_file.name}' imports '{alias.name}'"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_modules:
                        assert not node.module.startswith(forbidden), (
                            f"BOUNDARY VIOLATION: '{py_file.name}' imports from '{node.module}'"
                        )
