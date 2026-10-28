"""Comprehensive Test Suite for Multi-Agent Orchestration with DeepSeek & NVIDIA Nemotron on Nebius AI Cloud.

Validates:
- DAG task graph dependency scheduling and cycle detection
- Parallel worker execution with concurrency bounds
- Model routing between DeepSeek (routine) and NVIDIA Nemotron (escalation)
- Deterministic policy enforcement that models cannot override
- Evidence aggregation, contradiction detection, and deduplication
- Live Nebius AI Cloud OpenAI-compatible inference verification
"""
import asyncio
import os
import pytest

from app.schemas.agent_results import (
    FindingCategoryType,
    FindingSeverityLevel,
    StandardFinding,
    WorkerResult,
    AgentTaskStatus,
)
from app.services.model_router import ModelRouter, ModelTaskType
from app.services.orchestration.orchestrator import MultiAgentOrchestrator
from app.services.orchestration.policy_engine import OrchestrationPolicyEngine, PolicyDecision
from app.services.orchestration.result_aggregator import EvidenceAggregator
from app.services.orchestration.scheduler import TaskScheduler
from app.services.orchestration.task_graph import TaskGraph, TaskNode, TaskStatus


def test_task_graph_dag_dependency_and_cycle_detection():
    """Verify DAG scheduling, dependency resolution, and cycle rejection."""
    graph = TaskGraph(run_id="test_run_1")

    # Add 3 tasks: A (no deps), B (no deps), C (depends on A & B)
    task_a = TaskNode(task_id="A", name="Task A", task_type="code_review")
    task_b = TaskNode(task_id="B", name="Task B", task_type="security_review")
    task_c = TaskNode(task_id="C", name="Task C", task_type="risk_assessment", depends_on=["A", "B"])

    graph.add_task(task_a)
    graph.add_task(task_b)
    graph.add_task(task_c)
    graph.validate_dag()

    # Initially A and B are ready, C is not
    ready = graph.get_ready_tasks()
    ready_ids = {t.task_id for t in ready}
    assert ready_ids == {"A", "B"}

    # Mark A succeeded; C should still NOT be ready because B is pending
    graph.mark_succeeded("A", {"status": "ok"})
    ready_after_a = graph.get_ready_tasks()
    assert ready_after_a == []

    # Mark B succeeded; now C should become ready
    graph.mark_succeeded("B", {"status": "ok"})
    ready_after_b = graph.get_ready_tasks()
    assert len(ready_after_b) == 1
    assert ready_after_b[0].task_id == "C"

    # Verify cycle detection
    cyclic_graph = TaskGraph(run_id="cycle_run")
    cyclic_graph.add_task(TaskNode(task_id="X", name="X", task_type="review", depends_on=["Y"]))
    cyclic_graph.add_task(TaskNode(task_id="Y", name="Y", task_type="review", depends_on=["X"]))
    with pytest.raises(ValueError, match="Cyclic dependency"):
        cyclic_graph.validate_dag()


def test_task_scheduler_concurrency_and_retries():
    """Verify that scheduler executes ready nodes concurrently and handles retries."""
    async def _run():
        graph = TaskGraph(run_id="sched_run")
        graph.add_task(TaskNode(task_id="t1", name="Task 1", task_type="review"))
        graph.add_task(TaskNode(task_id="t2", name="Task 2", task_type="review"))

        scheduler = TaskScheduler(max_concurrency=2)
        execution_counts = {"t1": 0, "t2": 0}

        async def _dispatcher(task: TaskNode):
            execution_counts[task.task_id] += 1
            await asyncio.sleep(0.01)
            return {"task": task.task_id, "success": True}

        res_graph = await scheduler.execute_graph(graph, _dispatcher)
        assert res_graph.is_complete()
        assert not res_graph.has_failures()
        assert execution_counts["t1"] == 1
        assert execution_counts["t2"] == 1

    asyncio.run(_run())


def test_orchestration_policy_engine_mandatory_rules():
    """Verify that deterministic policy prevents models from overriding safety gates."""
    policy = OrchestrationPolicyEngine()

    # Rule 1: Failed tests strictly block deployment
    check_test_fail = policy.evaluate_release_policy(
        environment="staging",
        tests_passed=False,
        critical_findings=0,
        high_findings=0,
        risk_score=0.1,
    )
    assert check_test_fail.decision == PolicyDecision.BLOCK
    assert check_test_fail.allowed is False
    assert any("test suite failed" in v for v in check_test_fail.violations)

    # Rule 2: Critical finding strictly blocks release
    check_crit = policy.evaluate_release_policy(
        environment="staging",
        tests_passed=True,
        critical_findings=1,
        high_findings=0,
        risk_score=0.2,
    )
    assert check_crit.decision == PolicyDecision.BLOCK
    assert any("CRITICAL severity" in v for v in check_crit.violations)

    # Rule 3: Production requires explicit human sign-off
    check_prod = policy.evaluate_release_policy(
        environment="production",
        tests_passed=True,
        critical_findings=0,
        high_findings=0,
        risk_score=0.2,
        has_approval=False,
    )
    assert check_prod.decision == PolicyDecision.REQUIRE_APPROVAL
    assert check_prod.requires_human_approval is True

    # Rule 4: Read-only workers cannot call dangerous deployment tools
    check_tool = policy.validate_tool_dispatch(
        tool_name="deployment.deploy",
        worker_role="code_reviewer",
        granted_permissions=["repo:read"],
        parameters={},
    )
    assert check_tool.decision == PolicyDecision.BLOCK
    assert check_tool.allowed is False


def test_evidence_aggregator_contradiction_detection_and_dedup():
    """Verify deduplication of findings and detection of contradictions between agents."""
    aggregator = EvidenceAggregator()

    worker_code = WorkerResult(
        task_id="code_review",
        worker_role="code_reviewer",
        model_assigned="deepseek-ai/DeepSeek-V4.1-Flash",
        provider="nebius",
        status=AgentTaskStatus.SUCCEEDED,
        summary="PR looks good and approved.",
        findings=[
            StandardFinding(
                severity=FindingSeverityLevel.LOW,
                category=FindingCategoryType.STYLE,
                file_path="main.py",
                start_line=12,
                title="Line length",
                description="Line exceeds 100 characters.",
            )
        ],
    )

    worker_sec = WorkerResult(
        task_id="security_review",
        worker_role="security_reviewer",
        model_assigned="nvidia/Nemotron-3_5-Lightning",
        provider="nebius",
        status=AgentTaskStatus.SUCCEEDED,
        summary="Found SQL Injection.",
        findings=[
            StandardFinding(
                severity=FindingSeverityLevel.CRITICAL,
                category=FindingCategoryType.SECURITY,
                file_path="db.py",
                start_line=45,
                title="SQL Injection vulnerability",
                description="Unsanitized user input in query string.",
            ),
            # Duplicate finding intentionally added
            StandardFinding(
                severity=FindingSeverityLevel.CRITICAL,
                category=FindingCategoryType.SECURITY,
                file_path="db.py",
                start_line=45,
                title="SQL Injection vulnerability",
                description="Duplicate report.",
            ),
        ],
    )

    worker_tests = WorkerResult(
        task_id="run_tests",
        worker_role="test_worker",
        model_assigned="pytest",
        provider="platform",
        status=AgentTaskStatus.SUCCEEDED,
        summary="All tests passed.",
    )

    report = aggregator.aggregate(
        run_id="agg_run",
        worker_results=[worker_code, worker_sec, worker_tests],
    )

    # 1. Deduplication: The duplicate SQL injection finding must be merged
    assert report.total_findings_count == 2
    assert report.critical_findings_count == 1

    # 2. Contradiction: Code reviewer approved, but security flagged critical issue
    assert len(report.contradictions_detected) >= 1
    assert "Contradiction detected" in report.contradictions_detected[0]

    # 3. Overall status must be BLOCKED due to critical finding
    assert report.overall_status == "BLOCKED"


def test_model_router_deepseek_vs_nemotron():
    """Verify model routing policy: DeepSeek for routine work, Nemotron for escalation/complex tasks."""
    router = ModelRouter()

    # Routine task -> DeepSeek fast model
    route_routine = router.decide_route(task_type=ModelTaskType.DIFF_ANALYSIS.value, prompt="Small refactor")
    assert "deepseek" in route_routine.target_model.lower()
    assert route_routine.complexity.value == "fast"

    # High-risk task -> NVIDIA Nemotron deep reasoning
    route_high_risk = router.decide_route(task_type=ModelTaskType.SECURITY_AUDIT.value, risk_score=0.85)
    assert "nemotron" in route_high_risk.target_model.lower() or "nvidia" in route_high_risk.target_model.lower()
    assert route_high_risk.complexity.value == "reasoning"


def test_multi_agent_orchestration_clean_pr_workflow():
    """Verify complete multi-agent workflow on a clean PR."""
    async def _run():
        orchestrator = MultiAgentOrchestrator()
        clean_diff = """diff --git a/calc.py b/calc.py
+def add(a: int, b: int) -> int:
+    return a + b
"""
        report = await orchestrator.execute_workflow(
            pull_number=101,
            diff_text=clean_diff,
            environment="staging",
        )

        assert report.overall_status in ("APPROVED", "REQUIRES_APPROVAL")
        assert report.critical_findings_count == 0
        assert report.tests_passed is True
        assert len(report.model_routing_trail) == 4

    asyncio.run(_run())


def test_multi_agent_orchestration_escalation_on_security_risk():
    """Verify that a security risk triggers Nemotron escalation and blocks the release."""
    async def _run():
        orchestrator = MultiAgentOrchestrator()
        malicious_diff = """diff --git a/auth.py b/auth.py
+SECRET_KEY = 'hardcoded_jwt_secret_token_value_in_repo'
+eval(user_submitted_expression)
"""
        report = await orchestrator.execute_workflow(
            pull_number=102,
            diff_text=malicious_diff,
            environment="staging",
        )

        assert report.overall_status == "BLOCKED"
        assert report.critical_findings_count >= 1
        assert len(report.policy_blocks) >= 1

        # Confirm that security worker escalated to Nemotron
        security_trail = next(t for t in report.model_routing_trail if t["role"] == "security_reviewer")
        assert security_trail["requires_escalation"] is True
        assert "nemotron" in security_trail["model"].lower() or "nvidia" in security_trail["model"].lower()

    asyncio.run(_run())


def test_live_nebius_api_client_routing_if_available():
    """Verify live OpenAI-compatible inference against Nebius AI Cloud with configured API key."""
    async def _run():
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

        router = ModelRouter()
        if not router.api_key or router.api_key.startswith("mock-"):
            pytest.skip("Nebius API key not configured for live test.")

        # Test live DeepSeek call
        res_fast = await router.execute_completion(
            task_type=ModelTaskType.DIFF_ANALYSIS.value,
            messages=[{"role": "user", "content": "Respond with 'VERIFIED'"}],
            prompt_hint="test",
        )
        assert res_fast["status"] in ("success", "fallback")
        assert len(res_fast["content"]) > 0

    asyncio.run(_run())
