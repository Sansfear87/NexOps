"""ReAct Agent — the real reasoning engine for NexOps with Credit Efficiency.

Implements the AgentRuntime protocol from contracts/agent_contract.md.
Uses the ReAct (Reasoning + Acting) pattern:
  1. THOUGHT -> reason about what to do next
  2. ACTION  -> call a tool via the platform
  3. OBSERVATION -> receive the tool result
  4. Repeat until FINAL_ANSWER

Credit Efficiency Features:
- Real-time token accounting and cost tracking in USD.
- Budget enforcement guardrails preventing runaway spending.
- Prompt pruning & sliding window compression for scratchpad observations.
- Tool observation caching.

The agent NEVER touches databases, secrets, or cloud APIs directly.
All external interaction is mediated through tool callbacks.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable, Dict, List, Optional

from .config import AgentConfig
from .credit_optimizer import (
    PromptPruner,
    ResponseCache,
    TokenBudgetManager,
)
from .interface import (
    AgentAction,
    AgentContext,
    AgentResult,
    AgentRuntime,
    AgentStatus,
)
from .llm_client import ChatMessage, DeepSeekClient, MultiModelLLMClient
from .prompts import SYSTEM_PROMPT, build_goal_prompt

logger = logging.getLogger(__name__)

# Type alias for the tool execution callback provided by the platform
ToolExecutor = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]


class ReActAgent:
    """Production agent using DeepSeek/Nemotron with a ReAct reasoning loop.

    Conforms to the AgentRuntime protocol defined in agent/interface.py
    and contracts/agent_contract.md.

    Usage by the platform:
        agent = ReActAgent(api_key="sk-...", tool_executor=registry.dispatch)
        result = await agent.run(goal, context, tools, permissions)
    """

    def __init__(
        self,
        api_key: str,
        tool_executor: Optional[ToolExecutor] = None,
        config: Optional[AgentConfig] = None,
        llm_client: Optional[MultiModelLLMClient] = None,
    ) -> None:
        self._config = config or AgentConfig()
        self.budget_manager = TokenBudgetManager(
            max_tokens_budget=self._config.max_tokens_budget,
            max_cost_usd_budget=self._config.max_cost_usd_budget,
            warning_threshold_pct=self._config.warning_budget_threshold_pct,
        )
        self.cache = (
            ResponseCache(max_entries=self._config.cache_max_entries)
            if self._config.enable_response_cache
            else None
        )
        self.pruner = (
            PromptPruner(
                max_observation_chars=self._config.max_observation_chars,
                max_history_turns=self._config.max_history_turns,
            )
            if self._config.enable_prompt_pruning
            else None
        )

        self._llm = llm_client or MultiModelLLMClient(
            api_key=api_key,
            config=self._config,
            budget_manager=self.budget_manager,
            cache=self.cache,
        )
        self._tool_executor = tool_executor

    async def run(
        self,
        goal: str,
        context: AgentContext,
        tools: List[str],
        permissions: List[str],
    ) -> AgentResult:
        """Execute the ReAct loop to accomplish the specified goal.

        1. Builds a conversation with the system prompt + goal
        2. Checks credit and token budget limits
        3. Loops: asks LLM to think -> parse tool call or final answer
        4. Executes tools via the platform callback (with observation pruning and caching)
        5. Feeds results back to LLM
        6. Returns a structured AgentResult with rich telemetry
        """
        start_time = time.perf_counter()
        actions_taken: List[AgentAction] = []
        max_steps = context.metadata.get(
            "max_steps", self._config.default_max_steps
        )

        # Build conversation history
        messages: List[ChatMessage] = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=build_goal_prompt(
                    goal=goal,
                    environment=context.environment,
                    project_id=context.project_id,
                    available_tools=tools,
                    permissions=permissions,
                    metadata=context.metadata,
                ),
            ),
        ]

        step = 0
        final_output: Optional[Dict[str, Any]] = None

        try:
            while step < max_steps:
                # Credit and token budget guardrail
                if self.budget_manager.is_budget_exceeded():
                    logger.warning(
                        "[Agent %s] Budget limit exceeded ($%.4f spent, %d tokens). Terminating loop.",
                        context.run_id[:8],
                        self.budget_manager.cumulative_cost_usd,
                        self.budget_manager.total_tokens,
                    )
                    duration_ms = int((time.perf_counter() - start_time) * 1000)
                    return AgentResult(
                        run_id=context.run_id,
                        trace_id=context.trace_id,
                        status=AgentStatus.TIMED_OUT,
                        confidence=0.4,
                        actions_taken=actions_taken,
                        output={
                            "message": f"Execution halted: Token/Cost budget exceeded ({self.budget_manager.total_tokens} tokens, ${self.budget_manager.cumulative_cost_usd:.4f}).",
                        },
                        error={
                            "code": "BUDGET_EXCEEDED",
                            "message": "Token or cost budget threshold reached.",
                        },
                        metrics=self._compile_metrics(duration_ms, step),
                    )

                step += 1
                logger.info(
                    "[Agent %s] Step %d/%d", context.run_id[:8], step, max_steps
                )

                # Compress conversation history with sliding window to save tokens
                if self.pruner is not None and len(messages) > 6:
                    messages = self.pruner.compress_history(messages)

                # Ask LLM to think
                llm_response = await self._llm.chat_completion(messages)
                messages.append(
                    ChatMessage(role="assistant", content=llm_response)
                )

                # Parse the response
                parsed = self._parse_response(llm_response)

                if parsed["type"] == "final_answer":
                    # Agent is done
                    final_output = parsed["data"]
                    logger.info(
                        "[Agent %s] Reached FINAL_ANSWER at step %d",
                        context.run_id[:8],
                        step,
                    )
                    break

                if parsed["type"] == "action":
                    tool_name = parsed["tool_name"]
                    parameters = parsed["parameters"]
                    rationale = parsed.get("thought", "")

                    # Check if tool requires human approval
                    if tool_name in self._config.require_human_approval_for:
                        action = AgentAction(
                            action_id=str(uuid.uuid4()),
                            tool_name=tool_name,
                            parameters=parameters,
                            rationale=rationale,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            status="PROPOSED",
                        )
                        actions_taken.append(action)

                        duration_ms = int(
                            (time.perf_counter() - start_time) * 1000
                        )
                        return AgentResult(
                            run_id=context.run_id,
                            trace_id=context.trace_id,
                            status=AgentStatus.WAITING_FOR_APPROVAL,
                            confidence=0.5,
                            actions_taken=actions_taken,
                            output={
                                "pending_action": action.model_dump(),
                                "message": f"Tool '{tool_name}' requires human approval.",
                            },
                            metrics=self._compile_metrics(duration_ms, step),
                        )

                    # Check if tool is in available tools
                    if tool_name not in tools:
                        observation = (
                            f"ERROR: Tool '{tool_name}' is not available. "
                            f"Available tools: {', '.join(tools)}"
                        )
                        messages.append(
                            ChatMessage(role="user", content=f"OBSERVATION: {observation}")
                        )
                        continue

                    # Execute the tool via platform callback
                    action = AgentAction(
                        action_id=str(uuid.uuid4()),
                        tool_name=tool_name,
                        parameters=parameters,
                        rationale=rationale,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        status="EXECUTING",
                    )

                    if self._tool_executor:
                        try:
                            # Check observation cache if enabled
                            cache_key = None
                            cached_res = None
                            if self.cache is not None:
                                cache_key = ResponseCache.hash_key(f"tool:{tool_name}", parameters)
                                cached_res = self.cache.get(cache_key)

                            if cached_res is not None:
                                tool_result = cached_res
                            else:
                                tool_result = await self._tool_executor(
                                    tool_name, parameters
                                )
                                if self.cache is not None and cache_key is not None:
                                    self.cache.set(cache_key, tool_result, tokens_estimate=len(str(tool_result)) // 4)

                            action.status = "COMPLETED"
                            action.result = tool_result
                            observation = json.dumps(tool_result, indent=2)
                        except Exception as e:
                            action.status = "FAILED"
                            action.result = {"error": str(e)}
                            observation = f"TOOL ERROR: {str(e)}"
                    else:
                        # No tool executor provided — return mock result
                        action.status = "COMPLETED"
                        action.result = {"mock": True, "message": "No tool executor configured"}
                        observation = json.dumps(action.result)

                    actions_taken.append(action)

                    # Prune large observations to conserve prompt tokens
                    if self.pruner is not None and len(observation) > self._config.max_observation_chars:
                        observation, _ = self.pruner.prune_observation(observation)

                    # Feed observation back to the LLM
                    messages.append(
                        ChatMessage(
                            role="user",
                            content=f"OBSERVATION: {observation}",
                        )
                    )

                elif parsed["type"] == "error":
                    # LLM produced something unparseable — ask it to try again
                    messages.append(
                        ChatMessage(
                            role="user",
                            content=(
                                "OBSERVATION: Your response could not be parsed. "
                                "Please use the exact format:\n"
                                "THOUGHT: <reasoning>\n"
                                "ACTION: <tool_name>\n"
                                "ACTION_INPUT: <json>\n\n"
                                "Or if you are done:\n"
                                "THOUGHT: <reasoning>\n"
                                "FINAL_ANSWER: <json>"
                            ),
                        )
                    )

            # Build final result
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            if final_output is not None:
                return AgentResult(
                    run_id=context.run_id,
                    trace_id=context.trace_id,
                    status=AgentStatus.COMPLETED,
                    confidence=final_output.get("confidence", 0.8),
                    actions_taken=actions_taken,
                    output=final_output,
                    metrics=self._compile_metrics(duration_ms, step),
                )
            else:
                # Ran out of steps without reaching FINAL_ANSWER
                return AgentResult(
                    run_id=context.run_id,
                    trace_id=context.trace_id,
                    status=AgentStatus.TIMED_OUT,
                    confidence=0.3,
                    actions_taken=actions_taken,
                    output={
                        "message": f"Agent exhausted max steps ({max_steps}) without reaching a conclusion."
                    },
                    error={
                        "code": "MAX_STEPS_EXCEEDED",
                        "message": f"Agent did not complete within {max_steps} steps.",
                    },
                    metrics=self._compile_metrics(duration_ms, step),
                )

        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.exception(
                "[Agent %s] Unhandled exception", context.run_id[:8]
            )
            return AgentResult(
                run_id=context.run_id,
                trace_id=context.trace_id,
                status=AgentStatus.FAILED,
                confidence=0.0,
                actions_taken=actions_taken,
                output={},
                error={
                    "code": "AGENT_RUNTIME_ERROR",
                    "message": str(exc),
                },
                metrics=self._compile_metrics(duration_ms, step),
            )

    def _compile_metrics(self, duration_ms: int, steps_count: int) -> Dict[str, Any]:
        """Aggregate execution and credit efficiency metrics."""
        budget_metrics = self.budget_manager.get_metrics()
        cache_metrics = self.cache.get_stats() if self.cache else {}
        pruned_tokens = self.pruner.total_tokens_saved_estimate if self.pruner else 0

        return {
            "duration_ms": duration_ms,
            "steps_count": steps_count,
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
            "tokens_saved_by_pruning": pruned_tokens,
            "budget_exceeded": budget_metrics["budget_exceeded"],
        }

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse the LLM's response into a structured action or final answer."""
        # Try to extract FINAL_ANSWER
        final_match = re.search(
            r"FINAL_ANSWER:\s*(.+)", text, re.DOTALL
        )
        if final_match:
            raw = final_match.group(1).strip()
            thought = self._extract_thought(text)
            try:
                data = json.loads(raw)
                return {"type": "final_answer", "data": data, "thought": thought}
            except json.JSONDecodeError:
                # Try to find JSON within the text
                json_match = re.search(r"\{.*\}", raw, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        return {"type": "final_answer", "data": data, "thought": thought}
                    except json.JSONDecodeError:
                        pass
                # Return as plain text
                return {
                    "type": "final_answer",
                    "data": {"summary": raw},
                    "thought": thought,
                }

        # Try to extract ACTION + ACTION_INPUT
        action_match = re.search(r"ACTION:\s*(\S+)", text)
        input_match = re.search(r"ACTION_INPUT:\s*(.+?)(?:\n\n|\Z)", text, re.DOTALL)

        if action_match:
            tool_name = action_match.group(1).strip()
            thought = self._extract_thought(text)
            parameters: Dict[str, Any] = {}

            if input_match:
                raw_input = input_match.group(1).strip()
                try:
                    parameters = json.loads(raw_input)
                except json.JSONDecodeError:
                    # Try to find JSON
                    json_match = re.search(r"\{.*\}", raw_input, re.DOTALL)
                    if json_match:
                        try:
                            parameters = json.loads(json_match.group())
                        except json.JSONDecodeError:
                            pass

            return {
                "type": "action",
                "tool_name": tool_name,
                "parameters": parameters,
                "thought": thought,
            }

        return {"type": "error", "raw": text}

    @staticmethod
    def _extract_thought(text: str) -> str:
        """Extract the THOUGHT section from the response."""
        match = re.search(r"THOUGHT:\s*(.+?)(?=ACTION:|FINAL_ANSWER:|\Z)", text, re.DOTALL)
        return match.group(1).strip() if match else ""
