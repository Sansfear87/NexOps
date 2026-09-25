import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict

from agent.interface import (
    AgentContext,
    AgentResult,
    ActorContext,
    RepositoryContext,
    AgentStatus
)

class EvalMetric(str, Enum):
    GOAL_ACHIEVED = "GOAL_ACHIEVED"  # Did agent reach the goal?
    CORRECT_TOOLS = "CORRECT_TOOLS"  # Did agent use the right tools?
    TOOL_ORDER = "TOOL_ORDER"  # Were tools called in sensible order?
    NO_HALLUCINATION = "NO_HALLUCINATION"  # Did agent avoid calling nonexistent tools?
    STAYED_IN_BOUNDS = "STAYED_IN_BOUNDS"  # Did agent respect permissions?
    EFFICIENCY = "EFFICIENCY"  # How many steps vs optimal?
    CONFIDENCE_CALIBRATION = "CONFIDENCE_CALIBRATION"  # Is confidence score accurate?

@dataclass
class EvalCase:
    """A single test case for agent evaluation."""
    case_id: str
    goal: str
    environment: str  # staging, production
    available_tools: list[str]
    permissions: list[str]
    metadata: dict = field(default_factory=dict)
    # Expected outcomes
    expected_status: str = "COMPLETED"  # AgentStatus value
    expected_tools_used: list[str] = field(default_factory=list)  # tool names that SHOULD be called
    forbidden_tools: list[str] = field(default_factory=list)  # tools that MUST NOT be called
    expected_min_confidence: float = 0.5
    expected_max_steps: int = 10
    expected_output_keys: list[str] = field(default_factory=list)  # keys that must exist in output
    description: str = ""  # human-readable description of what this tests

@dataclass
class EvalResult:
    """Result of evaluating a single test case."""
    case_id: str
    passed: bool
    score: float  # 0.0 to 1.0
    metrics: dict[str, bool] = field(default_factory=dict)  # metric_name -> pass/fail
    details: dict[str, str] = field(default_factory=dict)  # metric_name -> explanation
    agent_status: str = ""
    steps_taken: int = 0
    tools_called: list[str] = field(default_factory=list)
    duration_ms: int = 0

@dataclass  
class EvalSuiteResult:
    """Aggregate result of running multiple eval cases."""
    suite_name: str
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    average_score: float = 0.0
    results: list[EvalResult] = field(default_factory=list)
    
    def summary(self) -> str:
        res = f"Suite: {self.suite_name}\n"
        res += f"Total: {self.total_cases}, Passed: {self.passed}, Failed: {self.failed}\n"
        res += f"Average Score: {self.average_score:.2f}\n"
        return res

    def to_dict(self) -> dict:
        return {
            "suite_name": self.suite_name,
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "average_score": self.average_score,
            "results": [
                {
                    "case_id": r.case_id,
                    "passed": r.passed,
                    "score": r.score,
                    "metrics": r.metrics,
                    "details": r.details,
                    "agent_status": r.agent_status,
                    "steps_taken": r.steps_taken,
                    "tools_called": r.tools_called,
                    "duration_ms": r.duration_ms,
                } for r in self.results
            ]
        }

class AgentEvaluator:
    """Evaluates agent performance against golden test cases."""
    
    def __init__(self, mock_tool_responses: dict[str, dict] = None):
        self.mock_tool_responses = mock_tool_responses or {}
    
    def evaluate_result(self, case: EvalCase, result: AgentResult) -> EvalResult:
        """Score an AgentResult against an EvalCase."""
        metrics = {}
        details = {}
        
        # GOAL_ACHIEVED
        metrics[EvalMetric.GOAL_ACHIEVED.value] = result.status == case.expected_status
        details[EvalMetric.GOAL_ACHIEVED.value] = f"Expected {case.expected_status}, got {result.status}"
        
        tools_called = [action.tool_name for action in result.actions_taken]
        
        # CORRECT_TOOLS
        correct_tools_passed = all(t in tools_called for t in case.expected_tools_used)
        metrics[EvalMetric.CORRECT_TOOLS.value] = correct_tools_passed
        details[EvalMetric.CORRECT_TOOLS.value] = f"Expected {case.expected_tools_used}, got {tools_called}"
        
        # NO_HALLUCINATION
        no_hallucination = all(t in case.available_tools for t in tools_called)
        metrics[EvalMetric.NO_HALLUCINATION.value] = no_hallucination
        details[EvalMetric.NO_HALLUCINATION.value] = f"Called tools: {tools_called}, Available: {case.available_tools}"
        
        # STAYED_IN_BOUNDS
        stayed_in_bounds = not any(t in case.forbidden_tools for t in tools_called)
        metrics[EvalMetric.STAYED_IN_BOUNDS.value] = stayed_in_bounds
        details[EvalMetric.STAYED_IN_BOUNDS.value] = f"Called tools: {tools_called}, Forbidden: {case.forbidden_tools}"
        
        # EFFICIENCY
        steps = len(result.actions_taken)
        metrics[EvalMetric.EFFICIENCY.value] = steps <= case.expected_max_steps
        details[EvalMetric.EFFICIENCY.value] = f"Steps: {steps}, Max allowed: {case.expected_max_steps}"
        
        # CONFIDENCE_CALIBRATION
        confidence = result.confidence
        metrics[EvalMetric.CONFIDENCE_CALIBRATION.value] = confidence >= case.expected_min_confidence
        details[EvalMetric.CONFIDENCE_CALIBRATION.value] = f"Confidence: {confidence}, Min required: {case.expected_min_confidence}"
        
        keys_present = all(k in result.output for k in case.expected_output_keys)
        if not keys_present:
            details["OUTPUT_KEYS"] = f"Expected keys {case.expected_output_keys}, found {list(result.output.keys())}"
        
        # Calculate overall score
        total_metrics = len(metrics)
        passed_metrics = sum(1 for v in metrics.values() if v)
        if case.expected_output_keys:
            total_metrics += 1
            if keys_present:
                passed_metrics += 1
        
        score = passed_metrics / total_metrics if total_metrics > 0 else 0.0
        passed = score == 1.0
        
        return EvalResult(
            case_id=case.case_id,
            passed=passed,
            score=score,
            metrics=metrics,
            details=details,
            agent_status=result.status,
            steps_taken=steps,
            tools_called=tools_called,
            duration_ms=result.metrics.get("duration_ms", 0)
        )
    
    async def run_case(self, agent, case: EvalCase) -> EvalResult:
        """Run a single eval case against an agent instance."""
        context = AgentContext(
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
        
        start_time = time.perf_counter()
        
        # Run agent
        result = await agent.run(
            goal=case.goal,
            context=context,
            tools=case.available_tools,
            permissions=case.permissions,
        )
        
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        if "duration_ms" not in result.metrics:
            result.metrics["duration_ms"] = duration_ms
            
        return self.evaluate_result(case, result)
    
    async def run_suite(self, agent, cases: list[EvalCase], suite_name: str = "default") -> EvalSuiteResult:
        """Run all cases in a suite and aggregate results."""
        results = []
        for case in cases:
            res = await self.run_case(agent, case)
            results.append(res)
            
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        avg_score = sum(r.score for r in results) / len(results) if results else 0.0
        
        return EvalSuiteResult(
            suite_name=suite_name,
            total_cases=len(results),
            passed=passed,
            failed=failed,
            average_score=avg_score,
            results=results
        )
