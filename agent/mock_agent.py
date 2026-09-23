"""Mock agent implementation for Phase 0 architectural validation.

Demonstrates adherence to AgentContract without making live LLM calls.
"""

from datetime import datetime, timezone
import uuid
from typing import List

from .interface import (
    AgentAction,
    AgentContext,
    AgentResult,
    AgentRuntime,
    AgentStatus,
)


class MockAgent(AgentRuntime):
    """Stub agent conforming to agent_contract.md.

    Used for contract verification, automated tests, and offline simulations.
    Real LLM routing (DeepSeek / Nemotron) is implemented in Phase 5 and Phase 12.
    """

    async def run(
        self,
        goal: str,
        context: AgentContext,
        tools: List[str],
        permissions: List[str],
    ) -> AgentResult:
        now_iso = datetime.now(timezone.utc).isoformat()

        # Simulate proposing a single safe observation action if repo:read is permitted
        actions = []
        if "repo:read" in permissions and "github.get_pull_request" in tools:
            action = AgentAction(
                action_id=str(uuid.uuid4()),
                tool_name="github.get_pull_request",
                parameters={"pull_number": context.metadata.get("pull_number", 1)},
                rationale="Fetch pull request metadata to evaluate changes.",
                timestamp=now_iso,
                status="COMPLETED",
                result={"status": "mock_success"},
            )
            actions.append(action)

        return AgentResult(
            run_id=context.run_id,
            trace_id=context.trace_id,
            status=AgentStatus.COMPLETED,
            confidence=0.95,
            actions_taken=actions,
            output={
                "message": f"Phase 0 MockAgent successfully validated contract for goal: '{goal}'",
                "environment": context.environment,
            },
            artifacts=[],
            metrics={"duration_ms": 12, "steps_count": len(actions)},
        )
