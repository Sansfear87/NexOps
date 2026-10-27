"""Multi-agent orchestrator coordinating specialized agents with dual-model routing.

Orchestrates specialized personas:
- REVIEWER: Code reviews, diff analysis, security audits (Nemotron + DeepSeek)
- DEPLOYER: Deployments, verification gates, rollbacks (DeepSeek)
- DIAGNOSTICIAN: Telemetry analysis, log diagnostics, root cause (Nemotron)
- MONITOR: Health metrics, anomaly detection (DeepSeek)
- PLANNER: High-level task decomposition, execution coordination (Nemotron)

Credit Efficiency Features:
- Token and cost tracking across all agents (DeepSeek vs Nemotron on Nebius).
- Inter-agent state handoffs minimizing repeated prompt context.
- Cross-agent observation caching and prompt pruning.
- Hard budget enforcement with early termination on credit exhaustion.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from .config import AgentConfig
from .credit_optimizer import (
    ComplexityTier,
    PromptPruner,
    ResponseCache,
    SemanticComplexityRouter,
    TokenBudgetManager,
)
from .interface import (
    AgentAction,
    AgentContext,
    AgentResult,
    AgentStatus,
)
from .llm_client import ChatMessage, MultiModelLLMClient
from .planner import AgentPlan, SubTask, TaskDecomposer

logger = logging.getLogger(__name__)

ToolExecutor = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]


class AgentRole(str, Enum):
    REVIEWER = "REVIEWER"          # Code review & security specialist
    DEPLOYER = "DEPLOYER"          # Deployment & rollback specialist
    DIAGNOSTICIAN = "DIAGNOSTICIAN"# Incident diagnosis & causal reasoning specialist
    MONITOR = "MONITOR"            # Health monitoring specialist
    PLANNER = "PLANNER"            # Task planning & coordination specialist


@dataclass
class AgentCapability:
    role: AgentRole
    description: str
    default_model: str             # e.g. "deepseek-chat" or "nvidia/nemotron-4-340b-instruct"
    supported_tools: List[str]     # Tools this agent can execute
    supported_goals: List[str]     # Regex patterns of goals this agent handles


@dataclass
class HandoffRequest:
    from_role: AgentRole
    to_role: AgentRole
    reason: str
    context: Dict[str, Any]        # State passed to target agent
    goal: str                      # Sub-goal for target agent
    recommended_model: Optional[str] = None


class AgentOrchestrator:
    """Enterprise multi-agent orchestrator managing roles, model routing, and credit efficiency."""

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        llm_client: Optional[MultiModelLLMClient] = None,
        tool_executor: Optional[ToolExecutor] = None,
    ) -> None:
        self.config = config or AgentConfig()
        self.budget_manager = TokenBudgetManager(
            max_tokens_budget=self.config.max_tokens_budget,
            max_cost_usd_budget=self.config.max_cost_usd_budget,
            warning_threshold_pct=self.config.warning_budget_threshold_pct,
        )
        self.cache = (
            ResponseCache(max_entries=self.config.cache_max_entries)
            if self.config.enable_response_cache
            else None
        )
        self.pruner = (
            PromptPruner(
                max_observation_chars=self.config.max_observation_chars,
                max_history_turns=self.config.max_history_turns,
            )
            if self.config.enable_prompt_pruning
            else None
        )

        self.llm_client = llm_client or MultiModelLLMClient(
            config=self.config,
            budget_manager=self.budget_manager,
            cache=self.cache,
        )
        self.tool_executor = tool_executor

        self.capabilities: Dict[AgentRole, AgentCapability] = {}
        self._register_defaults()

        self.decomposer = TaskDecomposer(llm_client=self.llm_client, config=self.config)

    def _register_defaults(self) -> None:
        """Register canonical specialized agent capabilities and their model affinities."""
        self.register_capability(
            AgentCapability(
                role=AgentRole.REVIEWER,
                description="Specializes in static analysis, PR reviews, and security vulnerability detection",
                default_model=self.config.preferred_fast_model,
                supported_tools=["github_api", "code_analyzer", "security_scanner", "github.get_pull_request"],
                supported_goals=[r"\breview\b.*", r"\banalyze code\b.*", r"\bpr\b.*", r"\bpull request\b.*", r"\bsecurity\b.*", r"\bcve\b.*"],
            )
        )
        self.register_capability(
            AgentCapability(
                role=AgentRole.DEPLOYER,
                description="Specializes in test execution, stage/prod deployment rollouts, and rollback operations",
                default_model=self.config.preferred_fast_model,
                supported_tools=["deploy_tool", "test_runner", "deployment.deploy", "deployment.rollback"],
                supported_goals=[r"\bdeploy\b.*", r"\brollback\b.*", r"\brelease\b.*", r"\bpromote\b.*", r"\btest\b.*"],
            )
        )
        self.register_capability(
            AgentCapability(
                role=AgentRole.DIAGNOSTICIAN,
                description="Specializes in incident investigation, log parsing, and deep root cause reasoning",
                default_model=self.config.preferred_reasoning_model,
                supported_tools=["log_viewer", "metrics_viewer", "incident_reporter"],
                supported_goals=[r"\bdiagnose\b.*", r"\binvestigate\b.*", r"\bincident\b.*", r"\bfix\b.*", r"\broot cause\b.*", r"\bcrash\b.*"],
            )
        )
        self.register_capability(
            AgentCapability(
                role=AgentRole.MONITOR,
                description="Specializes in telemetry tracking, uptime health checks, and anomaly detection",
                default_model=self.config.preferred_fast_model,
                supported_tools=["health_checker", "metrics_viewer", "monitor_poller"],
                supported_goals=[r"\bmonitor\b.*", r"\bhealth\b.*", r"\bmetric\b.*", r"\bstatus\b.*", r"\btelemetry\b.*"],
            )
        )
        self.register_capability(
            AgentCapability(
                role=AgentRole.PLANNER,
                description="Specializes in high-level plan decomposition, release gates, and cross-agent synthesis",
                default_model=self.config.preferred_reasoning_model,
                supported_tools=["planner_tool", "audit_logger"],
                supported_goals=[r"plan.*", r"coordinate.*", r"orchestrate.*"],
            )
        )

    def register_capability(self, capability: AgentCapability) -> None:
        self.capabilities[capability.role] = capability

    def select_agent(self, goal: str, available_tools: Optional[List[str]] = None) -> AgentRole:
        """Determine which specialized agent role should handle this goal."""
        goal_lower = goal.lower()
        for capability in self.capabilities.values():
            for pattern in capability.supported_goals:
                if re.search(pattern, goal_lower):
                    return capability.role
        return AgentRole.PLANNER

    def select_model_for_role(self, role: AgentRole, goal: str = "", risk_score: float = 0.0) -> str:
        """Select either DeepSeek or Nemotron based on role and task complexity."""
        if risk_score >= 0.65 or role == AgentRole.DIAGNOSTICIAN:
            return self.config.preferred_reasoning_model

        route = SemanticComplexityRouter.decide_route(goal=goal, role=role.value, risk_score=risk_score)
        if route.complexity == ComplexityTier.REASONING:
            return self.config.preferred_reasoning_model
        return self.config.preferred_fast_model

    def should_handoff(self, current_role: AgentRole, observation: Dict[str, Any]) -> Optional[HandoffRequest]:
        """Detect when an agent must dynamically transfer control to another specialist."""
        # 1. Reviewer detects critical flaw requiring deployment block or rollback
        if current_role == AgentRole.REVIEWER:
            if observation.get("critical_issue_found") or observation.get("needs_rollback") or observation.get("security_breach"):
                return self.create_handoff(
                    from_role=current_role,
                    to_role=AgentRole.DEPLOYER,
                    reason="Critical vulnerability/issue found in review, initiating deployment block/rollback",
                    context=observation,
                    goal="Execute emergency rollback or halt deployment pipeline",
                    recommended_model=self.config.preferred_fast_model,
                )

        # 2. Deployer encounters health check crash or post-deploy failure -> hands off to Diagnostician
        if current_role == AgentRole.DEPLOYER:
            if observation.get("deployment_failed") or observation.get("health_check_failed") or observation.get("status") == "CRASH_LOOP":
                return self.create_handoff(
                    from_role=current_role,
                    to_role=AgentRole.DIAGNOSTICIAN,
                    reason="Deployment failed health checks, requesting deep incident root-cause diagnosis",
                    context=observation,
                    goal="Investigate error logs and determine root cause of deployment failure",
                    recommended_model=self.config.preferred_reasoning_model,
                )

        # 3. Diagnostician completes diagnosis -> hands off to Deployer for targeted rollback/mitigation
        if current_role == AgentRole.DIAGNOSTICIAN:
            if observation.get("root_cause_identified") and observation.get("remediation_action") == "rollback":
                return self.create_handoff(
                    from_role=current_role,
                    to_role=AgentRole.DEPLOYER,
                    reason=f"Root cause confirmed ({observation.get('root_cause', 'unknown')}), triggering rollback",
                    context=observation,
                    goal="Execute rollback to previous stable commit",
                    recommended_model=self.config.preferred_fast_model,
                )

        return None

    def create_handoff(
        self,
        from_role: AgentRole,
        to_role: AgentRole,
        reason: str,
        context: Dict[str, Any],
        goal: str,
        recommended_model: Optional[str] = None,
    ) -> HandoffRequest:
        return HandoffRequest(
            from_role=from_role,
            to_role=to_role,
            reason=reason,
            context=context,
            goal=goal,
            recommended_model=recommended_model,
        )

    def get_system_prompt_for_role(self, role: AgentRole) -> str:
        """Return specialized system prompt for each agent role."""
        prompts = {
            AgentRole.REVIEWER: (
                "You are the REVIEWER specialist for the NexOps AI DevOps platform.\n"
                "Your objective is to perform rigorous code reviews, diff inspections, and security vulnerability scans.\n"
                "For routine diff checks, be fast and concise. For security-critical findings, detail the vulnerability.\n"
                "Use the ReAct pattern: THOUGHT, then ACTION (or FINAL_ANSWER)."
            ),
            AgentRole.DEPLOYER: (
                "You are the DEPLOYER specialist for the NexOps AI DevOps platform.\n"
                "Your objective is to ensure deterministic, safe deployments, verify pre-flight gates, and trigger rollbacks.\n"
                "Adhere to safety guardrails. If a deploy/rollback requires human approval, state it clearly.\n"
                "Use the ReAct pattern: THOUGHT, then ACTION (or FINAL_ANSWER)."
            ),
            AgentRole.DIAGNOSTICIAN: (
                "You are the DIAGNOSTICIAN specialist powered by deep causal reasoning (NVIDIA Nemotron).\n"
                "Your objective is to investigate incidents, correlate errors across logs/metrics, and diagnose root causes.\n"
                "Form clear hypotheses, gather evidence through tools, and formulate actionable remediation steps.\n"
                "Use the ReAct pattern: THOUGHT, then ACTION (or FINAL_ANSWER)."
            ),
            AgentRole.MONITOR: (
                "You are the MONITOR specialist for the NexOps AI DevOps platform.\n"
                "Your objective is to poll health endpoints, inspect system telemetry, and alert on anomaly spikes.\n"
                "Operate with high throughput and low overhead.\n"
                "Use the ReAct pattern: THOUGHT, then ACTION (or FINAL_ANSWER)."
            ),
            AgentRole.PLANNER: (
                "You are the PLANNER specialist for the NexOps AI DevOps platform.\n"
                "Your objective is to coordinate multi-agent tasks, evaluate high-level objectives, and synthesize findings.\n"
                "Use the ReAct pattern: THOUGHT, then ACTION (or FINAL_ANSWER)."
            ),
        }
        return prompts.get(role, "You are a specialized DevOps AI assistant.")

    async def orchestrate(
        self,
        goal: str,
        context: AgentContext,
        tools: List[str],
        permissions: List[str],
        tool_executor: Optional[ToolExecutor] = None,
    ) -> AgentResult:
        """Execute the full multi-agent orchestration lifecycle across specialized agents."""
        start_time = time.perf_counter()
        actions_taken: List[AgentAction] = []
        artifacts: List[Dict[str, Any]] = []
        handoffs_record: List[Dict[str, Any]] = []

        active_executor = tool_executor or self.tool_executor

        # 1. Break down goal into an optimized multi-agent plan
        plan: AgentPlan = await self.decomposer.decompose(
            goal=goal,
            available_tools=tools,
            permissions=permissions,
        )

        logger.info(
            "[Orchestrator %s] Decomposed into %d subtasks with budget=$%.2f / %d tokens",
            context.run_id[:8], len(plan.sub_tasks), plan.total_cost_budget_usd, plan.total_token_budget
        )

        subtask_results: Dict[str, Any] = {}
        subtask_idx = 0

        # 2. Iterate through subtasks with specialized agents
        while subtask_idx < len(plan.sub_tasks):
            subtask = plan.sub_tasks[subtask_idx]
            role = AgentRole(subtask.assigned_role) if subtask.assigned_role in AgentRole.__members__ else AgentRole.PLANNER
            target_model = subtask.recommended_model or self.select_model_for_role(role, goal=subtask.description)

            # Check credit/budget guardrail before dispatching
            if self.budget_manager.is_budget_exceeded():
                logger.warning(
                    "[Orchestrator %s] Budget exceeded ($%.4f spent, %d tokens). Halting early.",
                    context.run_id[:8], self.budget_manager.cumulative_cost_usd, self.budget_manager.total_tokens
                )
                break

            logger.info(
                "[Orchestrator %s] Executing SubTask %s ('%s') using %s on %s",
                context.run_id[:8], subtask.task_id, subtask.description[:35], role.value, target_model
            )

            # Execute subtask with specialized ReAct runner
            step_result, step_actions, handoff = await self._execute_subtask(
                subtask=subtask,
                role=role,
                model_name=target_model,
                context=context,
                available_tools=tools,
                permissions=permissions,
                prior_results=subtask_results,
                tool_executor=active_executor,
            )

            actions_taken.extend(step_actions)
            subtask_results[subtask.task_id] = step_result

            # Check if this subtask proposes an action requiring human approval
            for act in step_actions:
                if act.status == "PROPOSED" and act.tool_name in self.config.require_human_approval_for:
                    duration_ms = int((time.perf_counter() - start_time) * 1000)
                    return AgentResult(
                        run_id=context.run_id,
                        trace_id=context.trace_id,
                        status=AgentStatus.WAITING_FOR_APPROVAL,
                        confidence=0.5,
                        actions_taken=actions_taken,
                        output={
                            "pending_action": act.model_dump(),
                            "message": f"Multi-Agent execution paused: tool '{act.tool_name}' requires human approval.",
                            "subtask_id": subtask.task_id,
                        },
                        metrics=self._compile_metrics(duration_ms, actions_taken, handoffs_record),
                    )

            # Check for dynamic handoffs
            if handoff:
                handoffs_record.append({
                    "from_role": handoff.from_role.value,
                    "to_role": handoff.to_role.value,
                    "reason": handoff.reason,
                    "goal": handoff.goal,
                    "at_subtask": subtask.task_id,
                })
                logger.info(
                    "[Orchestrator %s] Dynamic Handoff triggered: %s -> %s (Reason: %s)",
                    context.run_id[:8], handoff.from_role.value, handoff.to_role.value, handoff.reason
                )

                # Dynamically insert reactive subtask into the plan
                reactive_subtask = SubTask(
                    task_id=f"handoff-{len(handoffs_record)}",
                    description=handoff.goal,
                    assigned_role=handoff.to_role.value,
                    recommended_model=handoff.recommended_model or self.select_model_for_role(handoff.to_role, goal=handoff.goal),
                    required_tools=tools,
                    token_budget=subtask.token_budget,
                    estimated_cost_usd=subtask.estimated_cost_usd,
                    priority=-1,
                )
                plan.sub_tasks.insert(subtask_idx + 1, reactive_subtask)

            subtask_idx += 1

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # 3. Compile aggregated synthesis output
        final_status = (
            AgentStatus.COMPLETED
            if not self.budget_manager.is_budget_exceeded()
            else AgentStatus.TIMED_OUT
        )

        compiled_output = {
            "summary": f"Orchestrated multi-agent pipeline for: {goal}",
            "subtasks_executed": len(subtask_results),
            "subtask_outcomes": subtask_results,
            "roles_involved": list({t.assigned_role for t in plan.sub_tasks[:subtask_idx]}),
            "handoffs": handoffs_record,
            "plan_progress": plan.get_progress(),
        }

        return AgentResult(
            run_id=context.run_id,
            trace_id=context.trace_id,
            status=final_status,
            confidence=0.9 if final_status == AgentStatus.COMPLETED else 0.5,
            actions_taken=actions_taken,
            output=compiled_output,
            artifacts=artifacts,
            metrics=self._compile_metrics(duration_ms, actions_taken, handoffs_record),
        )

    async def _execute_subtask(
        self,
        subtask: SubTask,
        role: AgentRole,
        model_name: str,
        context: AgentContext,
        available_tools: List[str],
        permissions: List[str],
        prior_results: Dict[str, Any],
        tool_executor: Optional[ToolExecutor],
    ) -> Tuple[Dict[str, Any], List[AgentAction], Optional[HandoffRequest]]:
        """Run an isolated ReAct loop for a single subtask with role-specific prompting."""
        actions: List[AgentAction] = []
        system_prompt = self.get_system_prompt_for_role(role)

        prior_context_str = json.dumps(prior_results, indent=2) if prior_results else "None"
        user_prompt = (
            f"## SUB-TASK OBJECTIVE\n"
            f"{subtask.description}\n\n"
            f"## ROLE: {role.value}\n"
            f"## PRIOR FINDINGS FROM TEAM:\n{prior_context_str}\n\n"
            f"## AVAILABLE TOOLS:\n" + "\n".join(f"- {t}" for t in available_tools) + "\n\n"
            f"Begin reasoning now. Use THOUGHT, then ACTION or FINAL_ANSWER."
        )

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]

        step = 0
        max_subtask_steps = 4
        handoff_request: Optional[HandoffRequest] = None
        subtask_output: Dict[str, Any] = {"status": "completed"}

        while step < max_subtask_steps:
            step += 1

            # Prune prompt history if enabled
            if self.pruner is not None and len(messages) > 6:
                messages = self.pruner.compress_history(messages)

            try:
                llm_resp = await self.llm_client.complete(
                    messages=messages,
                    model_name=model_name,
                    role=role.value,
                    max_tokens=2048,
                )
                messages.append(ChatMessage(role="assistant", content=llm_resp.content))

                # Parse response
                parsed = self._parse_llm_step(llm_resp.content)

                if parsed["type"] == "final_answer":
                    subtask_output = parsed["data"]
                    break

                if parsed["type"] == "action":
                    tool_name = parsed["tool_name"]
                    parameters = parsed["parameters"]
                    thought = parsed.get("thought", "")

                    action = AgentAction(
                        action_id=str(uuid.uuid4()),
                        tool_name=tool_name,
                        parameters=parameters,
                        rationale=f"[{role.value}] {thought}",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        status="PROPOSED" if tool_name in self.config.require_human_approval_for else "EXECUTING",
                    )
                    actions.append(action)

                    if action.status == "PROPOSED":
                        # High-risk action, return immediately for approval gate
                        return subtask_output, actions, None

                    # Execute tool or use cache
                    obs_dict: Dict[str, Any] = {}
                    if tool_executor:
                        try:
                            # Check observation cache if enabled
                            cache_key = None
                            if self.cache is not None:
                                cache_key = ResponseCache.hash_key(f"tool:{tool_name}", parameters)
                                cached_obs = self.cache.get(cache_key)
                                if cached_obs is not None:
                                    obs_dict = cached_obs

                            if not obs_dict:
                                obs_dict = await tool_executor(tool_name, parameters)
                                if self.cache is not None and cache_key is not None:
                                    self.cache.set(cache_key, obs_dict, tokens_estimate=len(str(obs_dict)) // 4)

                            action.status = "COMPLETED"
                            action.result = obs_dict
                        except Exception as e:
                            action.status = "FAILED"
                            action.result = {"error": str(e)}
                            obs_dict = {"error": str(e)}
                    else:
                        action.status = "COMPLETED"
                        action.result = {"status": "mock_success", "tool": tool_name}
                        obs_dict = action.result

                    # Check for dynamic handoffs based on observation
                    handoff_request = self.should_handoff(role, obs_dict)

                    # Feed observation back with pruning
                    obs_str = json.dumps(obs_dict)
                    if self.pruner is not None and len(obs_str) > self.config.max_observation_chars:
                        obs_str, _ = self.pruner.prune_observation(obs_str)

                    messages.append(ChatMessage(role="user", content=f"OBSERVATION: {obs_str}"))

                    if handoff_request:
                        break

            except Exception as e:
                logger.warning("[Orchestrator %s] Subtask step error: %s", context.run_id[:8], e)
                subtask_output = {"error": str(e)}
                break

        return subtask_output, actions, handoff_request

    def _parse_llm_step(self, text: str) -> Dict[str, Any]:
        """Extract tool invocation or final answer from LLM output."""
        # Check for FINAL_ANSWER
        final_match = re.search(r"FINAL_ANSWER:\s*(.+)", text, re.DOTALL)
        if final_match:
            raw = final_match.group(1).strip()
            try:
                data = json.loads(raw)
                return {"type": "final_answer", "data": data}
            except Exception:
                json_match = re.search(r"\{[\s\S]*\}", raw)
                if json_match:
                    try:
                        return {"type": "final_answer", "data": json.loads(json_match.group(0))}
                    except Exception:
                        pass
                return {"type": "final_answer", "data": {"summary": raw}}

        # Check for ACTION + ACTION_INPUT
        action_match = re.search(r"ACTION:\s*(\S+)", text)
        input_match = re.search(r"ACTION_INPUT:\s*(.+?)(?:\n\n|\Z)", text, re.DOTALL)
        if action_match:
            tool_name = action_match.group(1).strip()
            parameters = {}
            if input_match:
                try:
                    parameters = json.loads(input_match.group(1).strip())
                except Exception:
                    pass
            return {
                "type": "action",
                "tool_name": tool_name,
                "parameters": parameters,
                "thought": text[:text.find("ACTION:")].replace("THOUGHT:", "").strip(),
            }

        return {"type": "error", "raw": text}

    def _compile_metrics(
        self,
        duration_ms: int,
        actions: List[AgentAction],
        handoffs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Produce comprehensive execution & credit metrics."""
        budget_metrics = self.budget_manager.get_metrics()
        cache_metrics = self.cache.get_stats() if self.cache else {}
        pruning_saved = self.pruner.total_tokens_saved_estimate if self.pruner else 0

        return {
            "duration_ms": duration_ms,
            "actions_count": len(actions),
            "handoffs_count": len(handoffs),
            "total_tokens": budget_metrics["total_tokens"],
            "prompt_tokens": budget_metrics["prompt_tokens"],
            "completion_tokens": budget_metrics["completion_tokens"],
            "total_cost_usd": budget_metrics["total_cost_usd"],
            "remaining_budget_usd": budget_metrics["remaining_budget_usd"],
            "tokens_by_model": budget_metrics["tokens_by_model"],
            "tokens_by_role": budget_metrics["tokens_by_role"],
            "cost_by_model": budget_metrics["cost_by_model"],
            "cache_hits": cache_metrics.get("hits", 0),
            "cache_misses": cache_metrics.get("misses", 0),
            "tokens_saved_by_cache": cache_metrics.get("tokens_saved", 0),
            "tokens_saved_by_pruning": pruning_saved,
            "budget_exceeded": budget_metrics["budget_exceeded"],
        }
