import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from agent.evaluation import AgentEvaluator, EvalCase, EvalResult
from agent.golden_datasets import get_all_golden_cases, get_pr_review_cases
from agent.react_agent import ReActAgent
from agent.interface import AgentContext, RepositoryContext, ActorContext, AgentStatus, AgentResult as CoreAgentResult, AgentAction

def _context_from_case(case: EvalCase) -> AgentContext:
    return AgentContext(
        trace_id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4()),
        project_id="test-project",
        repository=RepositoryContext(owner="test", name="test-repo", default_branch="main"),
        actor=ActorContext(id="test-user", type="USER"),
        environment=case.environment,
        initiated_at=datetime.now(timezone.utc).isoformat(),
        permissions=case.permissions,
        metadata=case.metadata,
    )

def test_evaluator_scores_passing_case():
    evaluator = AgentEvaluator()
    case = EvalCase(
        case_id="pass_test",
        goal="Do thing",
        environment="staging",
        available_tools=["tool_a"],
        permissions=[],
        expected_status="COMPLETED",
        expected_tools_used=["tool_a"],
        expected_min_confidence=0.8,
        expected_max_steps=5,
        expected_output_keys=["result"]
    )
    result = CoreAgentResult(
        run_id="run-1",
        trace_id="trace-1",
        status=AgentStatus.COMPLETED,
        confidence=0.9,
        actions_taken=[AgentAction(action_id="1", tool_name="tool_a", rationale="", timestamp="2023-01-01T00:00:00Z")],
        output={"result": "done"},
        metrics={"duration_ms": 100}
    )
    
    eval_result = evaluator.evaluate_result(case, result)
    assert eval_result.passed is True
    assert eval_result.score == 1.0
    assert eval_result.metrics["GOAL_ACHIEVED"] is True

def test_evaluator_scores_failing_case():
    evaluator = AgentEvaluator()
    case = EvalCase(
        case_id="fail_test",
        goal="Do thing",
        environment="staging",
        available_tools=["tool_a"],
        permissions=[],
        expected_status="COMPLETED",
        expected_tools_used=["tool_a"],
        expected_min_confidence=0.8,
        expected_max_steps=5,
    )
    # Fails goal achieved
    result = CoreAgentResult(
        run_id="run-1",
        trace_id="trace-1",
        status=AgentStatus.FAILED,
        confidence=0.9,
        actions_taken=[AgentAction(action_id="1", tool_name="tool_a", rationale="", timestamp="2023-01-01T00:00:00Z")],
        output={},
        metrics={}
    )
    
    eval_result = evaluator.evaluate_result(case, result)
    assert eval_result.passed is False
    assert eval_result.score < 1.0
    assert eval_result.metrics["GOAL_ACHIEVED"] is False

def test_evaluator_detects_forbidden_tool():
    evaluator = AgentEvaluator()
    case = EvalCase(
        case_id="forbidden_test",
        goal="Do thing",
        environment="staging",
        available_tools=["tool_a", "tool_b"],
        permissions=[],
        expected_status="COMPLETED",
        forbidden_tools=["tool_b"]
    )
    result = CoreAgentResult(
        run_id="run-1",
        trace_id="trace-1",
        status=AgentStatus.COMPLETED,
        confidence=0.9,
        actions_taken=[AgentAction(action_id="1", tool_name="tool_b", rationale="", timestamp="2023-01-01T00:00:00Z")],
        output={},
        metrics={}
    )
    
    eval_result = evaluator.evaluate_result(case, result)
    assert eval_result.passed is False
    assert eval_result.metrics["STAYED_IN_BOUNDS"] is False

def test_evaluator_checks_output_keys():
    evaluator = AgentEvaluator()
    case = EvalCase(
        case_id="output_test",
        goal="Do thing",
        environment="staging",
        available_tools=[],
        permissions=[],
        expected_status="COMPLETED",
        expected_output_keys=["summary"]
    )
    result = CoreAgentResult(
        run_id="run-1",
        trace_id="trace-1",
        status=AgentStatus.COMPLETED,
        confidence=0.9,
        actions_taken=[],
        output={"other": "data"},
        metrics={}
    )
    
    eval_result = evaluator.evaluate_result(case, result)
    assert eval_result.passed is False
    assert "OUTPUT_KEYS" in eval_result.details

def test_all_golden_cases_have_required_fields():
    for case in get_all_golden_cases():
        assert case.case_id
        assert case.goal
        assert case.environment in ("staging", "production", "development")
        assert isinstance(case.available_tools, list)
        assert isinstance(case.permissions, list)

def test_golden_case_ids_are_unique():
    cases = get_all_golden_cases()
    ids = [c.case_id for c in cases]
    assert len(ids) == len(set(ids)), "Duplicate case IDs found"

def test_agent_graceful_failure_on_all_golden_cases():
    """Verify agent doesn't crash on any golden case."""
    import asyncio
    async def _run():
        agent = ReActAgent(api_key="test-key-for-regression")
        for case in get_all_golden_cases():
            context = _context_from_case(case)
            result = await agent.run(
                goal=case.goal,
                context=context,
                tools=case.available_tools,
                permissions=case.permissions,
            )
            # Agent should never crash — always return a valid AgentResult
            assert result.run_id == context.run_id
            assert result.status in list(AgentStatus)
            assert 0.0 <= result.confidence <= 1.0
    asyncio.run(_run())
