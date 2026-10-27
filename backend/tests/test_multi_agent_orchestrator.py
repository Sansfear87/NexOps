"""Tests for Multi-Agent Orchestration, Dual-Model Routing, and Credit Efficiency.

Verifies:
1. Pricing models and accurate USD cost calculations for DeepSeek & NVIDIA Nemotron.
2. Token budget enforcement, warning thresholds, and hard spending limits.
3. Semantic complexity routing between fast coder (DeepSeek) and deep reasoning (Nemotron).
4. Prompt pruning & observation truncation token savings.
5. In-memory response caching for deterministic queries and tools.
6. Multi-agent role selection and dynamic inter-agent handoffs.
7. Full end-to-end multi-agent orchestration lifecycle and metric reporting.
8. Strict architectural isolation boundary adherence.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is in python path
workspace_root = Path(__file__).resolve().parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from agent.config import AgentConfig
from agent.credit_optimizer import (
    ComplexityTier,
    ModelPricing,
    PromptPruner,
    ResponseCache,
    SemanticComplexityRouter,
    TokenBudgetManager,
    get_model_pricing,
)
from agent.interface import (
    ActorContext,
    AgentAction,
    AgentContext,
    AgentResult,
    AgentStatus,
    RepositoryContext,
)
from agent.llm_client import (
    ChatMessage,
    DeepSeekClient,
    LLMResponse,
    MultiModelLLMClient,
    NemotronClient,
)
from agent.orchestrator import (
    AgentCapability,
    AgentOrchestrator,
    AgentRole,
    HandoffRequest,
)
from agent.planner import AgentPlan, SubTask, TaskDecomposer
from agent.react_agent import ReActAgent


def _make_test_context(**overrides) -> AgentContext:
    defaults = dict(
        trace_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        project_id="proj-orchestrator-test",
        repository=RepositoryContext(
            owner="nexops", name="cloud-service", default_branch="main"
        ),
        actor=ActorContext(id="dev-user", type="USER"),
        environment="staging",
        initiated_at="2026-10-27T12:00:00Z",
        permissions=["repo:read", "deployment:write", "test:execute"],
        metadata={"pull_number": 99},
    )
    defaults.update(overrides)
    return AgentContext(**defaults)


# ---------------------------------------------------------------------------
# 1. Credit Optimizer & Pricing Tests
# ---------------------------------------------------------------------------

def test_model_pricing_and_registry():
    """Verify accurate pricing tables for DeepSeek and Nemotron."""
    deepseek_pricing = get_model_pricing("deepseek-chat")
    assert deepseek_pricing.input_cost_per_million == 0.14
    assert deepseek_pricing.output_cost_per_million == 0.28

    # Test calculation: 10,000 prompt + 2,000 completion
    # Cost = (10000/1M * 0.14) + (2000/1M * 0.28) = 0.0014 + 0.00056 = 0.00196 USD
    cost = deepseek_pricing.calculate_cost(10_000, 2_000)
    assert abs(cost - 0.00196) < 1e-5

    nemotron_pricing = get_model_pricing("nvidia/nemotron-4-340b-instruct")
    assert nemotron_pricing.input_cost_per_million == 1.00
    assert nemotron_pricing.output_cost_per_million == 3.00

    # Nemotron calculation: 10,000 prompt + 2,000 completion
    # Cost = (10000/1M * 1.00) + (2000/1M * 3.00) = 0.01 + 0.006 = 0.016 USD
    nemo_cost = nemotron_pricing.calculate_cost(10_000, 2_000)
    assert abs(nemo_cost - 0.016) < 1e-5


def test_token_budget_manager():
    """Verify TokenBudgetManager tracks tokens, costs, warnings, and limits."""
    mgr = TokenBudgetManager(max_tokens_budget=10_000, max_cost_usd_budget=0.05)

    assert not mgr.is_budget_exceeded()
    assert mgr.remaining_tokens() == 10_000
    assert mgr.remaining_budget_usd() == 0.05

    # Record DeepSeek usage
    cost1 = mgr.record_usage("deepseek-chat", prompt_tokens=2000, completion_tokens=500, role="REVIEWER")
    assert cost1 > 0.0
    assert mgr.total_tokens == 2500
    assert mgr.tokens_by_role["REVIEWER"]["total_tokens"] == 2500

    # Record Nemotron usage
    cost2 = mgr.record_usage("nvidia/nemotron-4-340b-instruct", prompt_tokens=5000, completion_tokens=1000, role="DIAGNOSTICIAN")
    assert cost2 > 0.0
    assert mgr.total_tokens == 8500
    assert mgr.is_warning_threshold()  # 8500 / 10000 = 85% >= 80%

    metrics = mgr.get_metrics()
    assert "deepseek-chat" in metrics["tokens_by_model"]
    assert "nvidia/nemotron-4-340b-instruct" in metrics["tokens_by_model"]

    # Exceed limit
    mgr.record_usage("deepseek-chat", prompt_tokens=2000, completion_tokens=500)
    assert mgr.is_budget_exceeded()
    assert mgr.remaining_tokens() == 0


def test_semantic_complexity_routing():
    """Verify SemanticComplexityRouter routes routine tasks to DeepSeek and deep tasks to Nemotron."""
    # Routine diff / syntax / lint -> DeepSeek
    route1 = SemanticComplexityRouter.decide_route(goal="Run lint and diff check on PR #12")
    assert route1.complexity == ComplexityTier.FAST
    assert "deepseek" in route1.model_name.lower()

    # Incident / Root cause -> Nemotron
    route2 = SemanticComplexityRouter.decide_route(goal="Diagnose incident #404: memory leak in auth service")
    assert route2.complexity == ComplexityTier.REASONING
    assert "nemotron" in route2.model_name.lower()

    # High risk score (0.85 >= 0.65) -> Nemotron
    route3 = SemanticComplexityRouter.decide_route(goal="Deploy to production", risk_score=0.85)
    assert route3.complexity == ComplexityTier.REASONING
    assert "nemotron" in route3.model_name.lower()


def test_prompt_pruning_and_compression():
    """Verify PromptPruner truncates huge observations and compacts history."""
    pruner = PromptPruner(max_observation_chars=300, max_history_turns=4)

    # 1. Observation Truncation
    huge_log = "Error log line timestamp: 2026-10-27\n" * 100  # ~3600 chars
    pruned_obs, tokens_saved = pruner.prune_observation(huge_log)
    assert len(pruned_obs) < len(huge_log)
    assert "[... OMITTED" in pruned_obs
    assert tokens_saved > 0
    assert pruner.total_tokens_saved_estimate > 0

    # 2. History Sliding Window Compression
    messages = [
        ChatMessage(role="system", content="System instruction"),
        ChatMessage(role="user", content="Initial goal"),
    ]
    # Add 10 intermediate turns
    for i in range(10):
        messages.append(ChatMessage(role="assistant", content=f"THOUGHT: thinking\nACTION: tool_{i}\nACTION_INPUT: {{}}"))
        messages.append(ChatMessage(role="user", content=f"OBSERVATION: result_{i}"))

    compressed = pruner.compress_history(messages, keep_recent_turns=4)
    # Head (2) + Summary (1) + Tail (4) = 7
    assert len(compressed) <= 8
    assert compressed[0].content == "System instruction"
    assert compressed[1].content == "Initial goal"
    assert "SUMMARY OF PRIOR INTERMEDIATE STEPS:" in compressed[2].content


def test_response_cache():
    """Verify ResponseCache stores, retrieves, and counts savings."""
    cache = ResponseCache(max_entries=10)

    key = ResponseCache.hash_key("tool:get_metrics", {"service": "backend"})
    assert cache.get(key) is None
    assert cache.misses == 1

    cache.set(key, {"cpu": 45, "status": "healthy"}, tokens_estimate=50, cost_estimate_usd=0.0001)
    cached_val = cache.get(key)
    assert cached_val is not None
    assert cached_val["cpu"] == 45
    assert cache.hits == 1
    assert cache.tokens_saved == 50

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["entries_count"] == 1


# ---------------------------------------------------------------------------
# 2. Multi-Model Client & Role Routing Tests
# ---------------------------------------------------------------------------

def test_multi_model_client_initialization():
    """Verify MultiModelLLMClient and specialized subclasses."""
    config = AgentConfig(
        model_name="deepseek-chat",
        nemotron_model_name="nvidia/nemotron-4-340b-instruct",
        nebius_api_key="test-nebius-key",
    )
    client = MultiModelLLMClient(api_key="test-deepseek-key", config=config)
    assert client.default_model == "deepseek-chat"
    assert client._nebius_api_key == "test-nebius-key"

    deepseek_sub = DeepSeekClient(api_key="test-ds-key", config=config)
    assert deepseek_sub.default_model == "deepseek-chat"

    nemotron_sub = NemotronClient(api_key="test-nemo-key", config=config)
    assert nemotron_sub.default_model == "nvidia/nemotron-4-340b-instruct"


def test_task_decomposer_rule_based_decomposition():
    """Verify TaskDecomposer generates structured multi-agent plans."""
    decomposer = TaskDecomposer()

    # 1. PR Review Plan
    pr_plan = decomposer._rule_based_decompose("Review PR #42 for security and merge", ["github_api", "code_analyzer"])
    assert len(pr_plan.sub_tasks) >= 3
    assert any(t.assigned_role == "REVIEWER" for t in pr_plan.sub_tasks)
    assert any("nemotron" in t.recommended_model.lower() for t in pr_plan.sub_tasks)

    # 2. Deployment Plan
    deploy_plan = decomposer._rule_based_decompose("Deploy release v2.4 to staging", ["test_runner", "deployment.deploy"])
    assert len(deploy_plan.sub_tasks) >= 3
    assert any(t.assigned_role == "DEPLOYER" for t in deploy_plan.sub_tasks)
    assert any(t.assigned_role == "MONITOR" for t in deploy_plan.sub_tasks)

    # 3. Incident Plan
    incident_plan = decomposer._rule_based_decompose("Diagnose incident: database connection pool exhausted", ["log_viewer"])
    assert any(t.assigned_role == "DIAGNOSTICIAN" for t in incident_plan.sub_tasks)
    assert any("nemotron" in t.recommended_model.lower() for t in incident_plan.sub_tasks)


def test_agent_orchestrator_capabilities_and_handoffs():
    """Verify AgentOrchestrator capability registration, model selection, and dynamic handoffs."""
    orchestrator = AgentOrchestrator()

    # Role selection
    assert orchestrator.select_agent("Review PR #88") == AgentRole.REVIEWER
    assert orchestrator.select_agent("Deploy to staging") == AgentRole.DEPLOYER
    assert orchestrator.select_agent("Diagnose production 500 spike") == AgentRole.DIAGNOSTICIAN
    assert orchestrator.select_agent("Monitor service metrics") == AgentRole.MONITOR

    # Model selection for roles
    reviewer_model = orchestrator.select_model_for_role(AgentRole.REVIEWER, goal="lint check")
    assert "deepseek" in reviewer_model.lower()

    diagnostician_model = orchestrator.select_model_for_role(AgentRole.DIAGNOSTICIAN, goal="diagnose crash")
    assert "nemotron" in diagnostician_model.lower()

    # Handoff 1: Reviewer detects critical issue -> Deployer
    handoff1 = orchestrator.should_handoff(
        AgentRole.REVIEWER,
        {"critical_issue_found": True, "needs_rollback": True}
    )
    assert handoff1 is not None
    assert handoff1.from_role == AgentRole.REVIEWER
    assert handoff1.to_role == AgentRole.DEPLOYER

    # Handoff 2: Deployer encounters health failure -> Diagnostician
    handoff2 = orchestrator.should_handoff(
        AgentRole.DEPLOYER,
        {"deployment_failed": True, "health_check_failed": True}
    )
    assert handoff2 is not None
    assert handoff2.from_role == AgentRole.DEPLOYER
    assert handoff2.to_role == AgentRole.DIAGNOSTICIAN

    # Handoff 3: Diagnostician diagnoses root cause -> Deployer rollback
    handoff3 = orchestrator.should_handoff(
        AgentRole.DIAGNOSTICIAN,
        {"root_cause_identified": True, "remediation_action": "rollback", "root_cause": "OOM in workers"}
    )
    assert handoff3 is not None
    assert handoff3.from_role == AgentRole.DIAGNOSTICIAN
    assert handoff3.to_role == AgentRole.DEPLOYER


# ---------------------------------------------------------------------------
# 3. End-to-End Orchestrator & Guardrails Tests
# ---------------------------------------------------------------------------

def test_orchestrator_end_to_end_with_mock_tools():
    """Verify orchestrate runs subtasks, emits metrics, and compiles results."""
    async def mock_executor(tool_name: str, parameters: dict) -> dict:
        if "github" in tool_name:
            return {"pr_id": 99, "status": "open", "files_changed": 3}
        elif "deploy" in tool_name:
            return {"deployment_id": "dep-123", "status": "SUCCESS"}
        elif "test" in tool_name:
            return {"tests_run": 45, "passed": 45, "failed": 0}
        elif "log" in tool_name:
            return {"logs": ["INFO: server started", "WARN: high latency"]}
        return {"status": "ok", "tool": tool_name}

    config = AgentConfig(
        max_tokens_budget=40_000,
        max_cost_usd_budget=0.20,
    )
    orchestrator = AgentOrchestrator(config=config, tool_executor=mock_executor)
    context = _make_test_context()

    async def _run():
        result = await orchestrator.orchestrate(
            goal="Review PR #99 and assess deployment readiness",
            context=context,
            tools=["github.get_pull_request", "code_analyzer", "test_runner"],
            permissions=["repo:read", "test:execute"],
        )

        assert isinstance(result, AgentResult)
        assert result.run_id == context.run_id
        assert result.trace_id == context.trace_id
        assert result.status in (AgentStatus.COMPLETED, AgentStatus.WAITING_FOR_APPROVAL)
        assert "subtasks_executed" in result.output
        assert "total_cost_usd" in result.metrics
        assert "total_tokens" in result.metrics
        assert "tokens_by_model" in result.metrics
        assert "tokens_by_role" in result.metrics

    asyncio.run(_run())


def test_budget_exhaustion_halts_cleanly():
    """Verify that hitting the budget limit triggers a clean early termination."""
    # Set an ultra-low budget (10 tokens or $0.00001)
    config = AgentConfig(
        max_tokens_budget=10,
        max_cost_usd_budget=0.00001,
    )
    orchestrator = AgentOrchestrator(config=config)
    # Artificially breach budget
    orchestrator.budget_manager.record_usage("deepseek-chat", prompt_tokens=100, completion_tokens=100)
    assert orchestrator.budget_manager.is_budget_exceeded()

    context = _make_test_context()

    async def _run():
        result = await orchestrator.orchestrate(
            goal="Diagnose crash loop and run full regression tests",
            context=context,
            tools=["log_viewer"],
            permissions=["repo:read"],
        )

        assert result.metrics["budget_exceeded"] is True

    asyncio.run(_run())


def test_agent_subsystem_preserves_strict_isolation_boundary():
    """Verify architectural invariant: agent package must never directly import database or cloud SDKs."""
    import ast

    agent_dir = Path(__file__).resolve().parent.parent.parent / "agent"
    forbidden_modules = [
        "sqlalchemy",
        "asyncpg",
        "psycopg2",
        "alembic",
        "requests",
        "httpx",
        "aiohttp",
        "github",
        "app.models",
        "app.db",
        "app.core.config",
    ]

    for py_file in agent_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert not alias.name.startswith(forbidden), (
                            f"Architectural Violation: '{py_file.name}' imports '{alias.name}', "
                            f"which violates the agent isolation boundary!"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_modules:
                        assert not node.module.startswith(forbidden), (
                            f"Architectural Violation: '{py_file.name}' imports from '{node.module}', "
                            f"which violates the agent isolation boundary!"
                        )
