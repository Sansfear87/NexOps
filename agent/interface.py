"""Canonical Python interface and data shapes for the Agent Subsystem.

Conforms 1:1 with contracts/agent_contract.md.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class RepositoryContext(BaseModel):
    owner: str
    name: str
    default_branch: str
    current_ref: Optional[str] = None


class ActorContext(BaseModel):
    id: str
    type: str  # USER, SYSTEM, WEBHOOK, SCHEDULE


class AgentContext(BaseModel):
    """Contextual metadata passed by the Platform into agent.run()."""
    trace_id: str = Field(..., description="Distributed tracing UUID")
    run_id: str = Field(..., description="Unique ID for this agent execution attempt")
    project_id: str = Field(..., description="Target platform project identifier")
    repository: RepositoryContext
    actor: ActorContext
    environment: str = Field(..., description="development, staging, or production")
    initiated_at: str = Field(..., description="ISO-8601 UTC timestamp")
    permissions: List[str] = Field(default_factory=list, description="Explicit granted permission tokens")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary non-sensitive context")


class AgentConstraints(BaseModel):
    max_steps: int = 20
    timeout_seconds: int = 300
    require_human_approval_for: List[str] = Field(default_factory=list)


class AgentRequest(BaseModel):
    """Complete invocation envelope delivered to the agent."""
    goal: str
    context: AgentContext
    available_tools: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    constraints: AgentConstraints = Field(default_factory=AgentConstraints)


class AgentAction(BaseModel):
    """A discrete tool invocation step proposed by the agent."""
    action_id: str
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rationale: str
    timestamp: str
    status: str = "PROPOSED"  # PROPOSED, APPROVED, EXECUTING, COMPLETED, REJECTED, FAILED
    result: Optional[Dict[str, Any]] = None


class AgentResult(BaseModel):
    """The final outcome emitted upon agent completion."""
    run_id: str
    trace_id: str
    status: AgentStatus
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0 - 1.0")
    actions_taken: List[AgentAction] = Field(default_factory=list)
    output: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class ToolCallable(Protocol):
    """Protocol for tools callable by the agent through the platform registry."""
    async def __call__(self, parameters: Dict[str, Any]) -> Dict[str, Any]: ...


class AgentRuntime(Protocol):
    """Conceptual interface for the Agent Runtime."""

    async def run(
        self,
        goal: str,
        context: AgentContext,
        tools: List[str],
        permissions: List[str],
    ) -> AgentResult:
        """Execute the agent loop to accomplish the specified goal."""
        ...
