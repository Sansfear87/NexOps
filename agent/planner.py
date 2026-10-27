"""Task planning and decomposition engine for multi-agent workflows.

Breaks down high-level DevOps objectives into dependency-linked SubTasks,
assigning specialized agent roles, target models (DeepSeek vs Nemotron),
and credit/token budgets.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SubTask:
    task_id: str
    description: str
    required_tools: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)  # task_ids this depends on
    assigned_role: str = "PLANNER"                       # REVIEWER, DEPLOYER, DIAGNOSTICIAN, MONITOR, PLANNER
    recommended_model: str = "deepseek-chat"             # deepseek-chat vs nvidia/nemotron-4-340b-instruct
    token_budget: int = 10_000
    estimated_cost_usd: float = 0.05
    status: str = "PENDING"                              # PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED
    result: Optional[Dict[str, Any]] = None
    priority: int = 0                                    # lower = higher priority


@dataclass
class AgentPlan:
    plan_id: str
    goal: str
    sub_tasks: List[SubTask] = field(default_factory=list)
    current_task_index: int = 0
    status: str = "PLANNING"                             # PLANNING, EXECUTING, COMPLETED, FAILED
    total_token_budget: int = 50_000
    total_cost_budget_usd: float = 0.50
    budget_consumed_tokens: int = 0
    cost_consumed_usd: float = 0.0

    def get_next_task(self) -> Optional[SubTask]:
        """Return the next pending subtask sequentially."""
        if self.current_task_index < len(self.sub_tasks):
            return self.sub_tasks[self.current_task_index]
        return None

    def get_task_by_id(self, task_id: str) -> Optional[SubTask]:
        for t in self.sub_tasks:
            if t.task_id == task_id:
                return t
        return None

    def get_pending_tasks_ready(self) -> List[SubTask]:
        """Return pending tasks whose dependencies have all completed successfully."""
        completed_ids = {t.task_id for t in self.sub_tasks if t.status == "COMPLETED"}
        ready: List[SubTask] = []
        for t in self.sub_tasks:
            if t.status == "PENDING" and all(dep in completed_ids for dep in t.depends_on):
                ready.append(t)
        return ready

    def mark_current_completed(self, result: Dict[str, Any]) -> None:
        task = self.get_next_task()
        if task:
            task.status = "COMPLETED"
            task.result = result
            self.current_task_index += 1
            if self.is_complete():
                self.status = "COMPLETED"
            else:
                self.status = "EXECUTING"

    def mark_current_failed(self, error: str) -> None:
        task = self.get_next_task()
        if task:
            task.status = "FAILED"
            task.result = {"error": error}
            self.status = "FAILED"

    def record_task_spend(self, tokens: int, cost_usd: float) -> None:
        self.budget_consumed_tokens += tokens
        self.cost_consumed_usd = round(self.cost_consumed_usd + cost_usd, 6)

    def is_complete(self) -> bool:
        return self.current_task_index >= len(self.sub_tasks) and all(
            t.status in ("COMPLETED", "SKIPPED") for t in self.sub_tasks
        )

    def get_progress(self) -> Dict[str, Any]:
        total = len(self.sub_tasks)
        completed = sum(1 for t in self.sub_tasks if t.status == "COMPLETED")
        failed = sum(1 for t in self.sub_tasks if t.status == "FAILED")
        remaining = total - completed - failed
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "remaining": remaining,
            "budget_consumed_tokens": self.budget_consumed_tokens,
            "cost_consumed_usd": self.cost_consumed_usd,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "current_task_index": self.current_task_index,
            "status": self.status,
            "total_token_budget": self.total_token_budget,
            "total_cost_budget_usd": self.total_cost_budget_usd,
            "budget_consumed_tokens": self.budget_consumed_tokens,
            "cost_consumed_usd": self.cost_consumed_usd,
            "sub_tasks": [
                {
                    "task_id": t.task_id,
                    "description": t.description,
                    "assigned_role": t.assigned_role,
                    "recommended_model": t.recommended_model,
                    "token_budget": t.token_budget,
                    "estimated_cost_usd": t.estimated_cost_usd,
                    "required_tools": t.required_tools,
                    "required_permissions": t.required_permissions,
                    "depends_on": t.depends_on,
                    "status": t.status,
                    "result": t.result,
                    "priority": t.priority,
                }
                for t in self.sub_tasks
            ],
        }


class TaskDecomposer:
    """Uses LLM reasoning or intelligent heuristic decomposition to build multi-agent plans."""

    DECOMPOSITION_PROMPT = """You are a senior DevOps Architect and Multi-Agent Coordinator.
Analyze the following goal and break it down into an ordered, credit-efficient multi-agent plan.

GOAL: {goal}
AVAILABLE TOOLS: {tools}
PERMISSIONS: {permissions}

Specialist Agent Roles:
- REVIEWER: Code reviews, diff analysis, security audits (Nemotron for deep risk/CVEs, DeepSeek for lints/syntax).
- DEPLOYER: Automated test runs, staging/production deployments, rollbacks.
- DIAGNOSTICIAN: Error log analysis, anomaly detection, root cause post-mortems (Nemotron).
- MONITOR: Health metrics, endpoint verification, telemetry polling (DeepSeek).
- PLANNER: Coordination, strategic synthesis, release gates.

Respond with ONLY a valid JSON object matching this schema:
{{
  "sub_tasks": [
    {{
      "task_id": "1",
      "description": "<specific sub-task>",
      "assigned_role": "<REVIEWER|DEPLOYER|DIAGNOSTICIAN|MONITOR|PLANNER>",
      "recommended_model": "<deepseek-chat|nvidia/nemotron-4-340b-instruct>",
      "required_tools": ["<tool_name>"],
      "depends_on": []
    }}
  ]
}}
"""

    def __init__(self, llm_client=None, config=None):
        self.llm_client = llm_client
        self.config = config

    async def decompose(
        self,
        goal: str,
        available_tools: List[str],
        permissions: Optional[List[str]] = None,
    ) -> AgentPlan:
        """Break a goal into sub-tasks using the LLM with seamless rule-based fallback."""
        perms = permissions or []

        # If LLM client is available, attempt dynamic decomposition
        if self.llm_client is not None:
            try:
                from .llm_client import ChatMessage
                prompt = self.DECOMPOSITION_PROMPT.format(
                    goal=goal,
                    tools=", ".join(available_tools) if available_tools else "none",
                    permissions=", ".join(perms) if perms else "none",
                )
                messages = [
                    ChatMessage(role="system", content="You decompose complex DevOps tasks into JSON plans."),
                    ChatMessage(role="user", content=prompt),
                ]

                # Determine if goal warrants Nemotron or DeepSeek
                from .credit_optimizer import SemanticComplexityRouter
                route = SemanticComplexityRouter.decide_route(goal=goal)
                
                resp = await self.llm_client.complete(
                    messages=messages,
                    model_name=route.model_name,
                    max_tokens=2048,
                )

                plan = self._parse_llm_plan(resp.content, goal)
                if plan and plan.sub_tasks:
                    logger.info("Decomposed goal '%s' into %d subtasks via %s", goal[:40], len(plan.sub_tasks), route.model_name)
                    return plan
            except Exception as e:
                logger.warning("LLM task decomposition encountered error: %s. Using heuristic fallback.", e)

        # Fallback to enhanced rule-based decomposition
        return self._rule_based_decompose(goal, available_tools)

    def _parse_llm_plan(self, text: str, goal: str) -> Optional[AgentPlan]:
        """Extract JSON plan from LLM output."""
        json_match = re.search(r"\{[\s\S]*\}", text)
        if not json_match:
            return None

        try:
            data = json.loads(json_match.group(0))
            raw_tasks = data.get("sub_tasks", [])
            if not raw_tasks:
                return None

            sub_tasks: List[SubTask] = []
            for item in raw_tasks:
                sub_tasks.append(
                    SubTask(
                        task_id=str(item.get("task_id", uuid.uuid4().hex[:4])),
                        description=item.get("description", "Execute step"),
                        assigned_role=item.get("assigned_role", "PLANNER").upper(),
                        recommended_model=item.get("recommended_model", "deepseek-chat"),
                        required_tools=item.get("required_tools", []),
                        required_permissions=item.get("required_permissions", []),
                        depends_on=[str(d) for d in item.get("depends_on", [])],
                        token_budget=item.get("token_budget", 8000),
                        estimated_cost_usd=item.get("estimated_cost_usd", 0.02),
                    )
                )

            return AgentPlan(
                plan_id=str(uuid.uuid4()),
                goal=goal,
                sub_tasks=sub_tasks,
                status="EXECUTING",
            )
        except Exception as exc:
            logger.debug("Failed parsing LLM decomposition JSON: %s", exc)
            return None

    def _rule_based_decompose(self, goal: str, available_tools: List[str]) -> AgentPlan:
        """Intelligent heuristic decomposition for common DevOps lifecycles."""
        plan = AgentPlan(
            plan_id=str(uuid.uuid4()),
            goal=goal,
            status="EXECUTING",
            total_token_budget=50_000,
            total_cost_budget_usd=0.50,
        )
        goal_lower = goal.lower()

        # 1. PR Review Lifecycle
        if any(kw in goal_lower for kw in ("review pr", "review", "pull request", "pr #")):
            plan.sub_tasks = [
                SubTask(
                    task_id="1",
                    description="Fetch PR metadata and changed files",
                    assigned_role="REVIEWER",
                    recommended_model="deepseek-chat",
                    required_tools=[t for t in available_tools if "github" in t or "pull" in t] or ["github.get_pull_request"],
                    token_budget=4000,
                    estimated_cost_usd=0.005,
                ),
                SubTask(
                    task_id="2",
                    description="Deep code analysis for security vulnerabilities and architectural impact",
                    assigned_role="REVIEWER",
                    recommended_model="nvidia/nemotron-4-340b-instruct",
                    required_tools=[t for t in available_tools if "code" in t or "security" in t or "analyze" in t] or ["code_analyzer"],
                    depends_on=["1"],
                    token_budget=12000,
                    estimated_cost_usd=0.035,
                ),
                SubTask(
                    task_id="3",
                    description="Submit structured review comments and risk assessment verdict",
                    assigned_role="REVIEWER",
                    recommended_model="deepseek-chat",
                    required_tools=[t for t in available_tools if "review" in t or "comment" in t or "github" in t] or ["github.create_review"],
                    depends_on=["2"],
                    token_budget=5000,
                    estimated_cost_usd=0.008,
                ),
            ]

        # 2. Deployment & Release Lifecycle
        elif any(kw in goal_lower for kw in ("deploy", "release", "ship", "promote")):
            plan.sub_tasks = [
                SubTask(
                    task_id="1",
                    description="Execute automated test suite & verify test coverage",
                    assigned_role="DEPLOYER",
                    recommended_model="deepseek-chat",
                    required_tools=[t for t in available_tools if "test" in t] or ["test_runner"],
                    token_budget=4000,
                    estimated_cost_usd=0.005,
                ),
                SubTask(
                    task_id="2",
                    description="Assess release risk score and evaluate deployment guardrails",
                    assigned_role="REVIEWER",
                    recommended_model="nvidia/nemotron-4-340b-instruct",
                    depends_on=["1"],
                    token_budget=8000,
                    estimated_cost_usd=0.025,
                ),
                SubTask(
                    task_id="3",
                    description="Trigger deployment rollout to target environment",
                    assigned_role="DEPLOYER",
                    recommended_model="deepseek-chat",
                    required_tools=[t for t in available_tools if "deploy" in t] or ["deployment.deploy"],
                    depends_on=["2"],
                    token_budget=4000,
                    estimated_cost_usd=0.005,
                ),
                SubTask(
                    task_id="4",
                    description="Verify service health & endpoint availability post-deployment",
                    assigned_role="MONITOR",
                    recommended_model="deepseek-chat",
                    required_tools=[t for t in available_tools if "health" in t or "metric" in t or "monitor" in t] or ["health_checker"],
                    depends_on=["3"],
                    token_budget=4000,
                    estimated_cost_usd=0.005,
                ),
            ]

        # 3. Incident Diagnosis & Rollback Lifecycle
        elif any(kw in goal_lower for kw in ("diagnose", "incident", "investigate", "outage", "debug", "crash", "rollback")):
            plan.sub_tasks = [
                SubTask(
                    task_id="1",
                    description="Fetch recent error logs and telemetry metrics",
                    assigned_role="DIAGNOSTICIAN",
                    recommended_model="deepseek-chat",
                    required_tools=[t for t in available_tools if "log" in t or "metric" in t] or ["log_viewer", "metrics_viewer"],
                    token_budget=6000,
                    estimated_cost_usd=0.008,
                ),
                SubTask(
                    task_id="2",
                    description="NVIDIA Nemotron deep causal reasoning and root cause identification",
                    assigned_role="DIAGNOSTICIAN",
                    recommended_model="nvidia/nemotron-4-340b-instruct",
                    depends_on=["1"],
                    token_budget=16000,
                    estimated_cost_usd=0.048,
                ),
                SubTask(
                    task_id="3",
                    description="Synthesize mitigation plan or execute safe automated rollback",
                    assigned_role="DEPLOYER",
                    recommended_model="deepseek-chat",
                    required_tools=[t for t in available_tools if "rollback" in t or "deploy" in t] or ["deployment.rollback"],
                    depends_on=["2"],
                    token_budget=5000,
                    estimated_cost_usd=0.007,
                ),
            ]

        # 4. Default Single SubTask
        else:
            plan.sub_tasks = [
                SubTask(
                    task_id="1",
                    description=f"Execute: {goal}",
                    assigned_role="PLANNER",
                    recommended_model="deepseek-chat",
                    required_tools=available_tools,
                    token_budget=10000,
                    estimated_cost_usd=0.015,
                )
            ]

        return plan
