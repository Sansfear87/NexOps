"""Tool Registry & Execution Boundary for AI DevOps Assistant.

Adheres strictly to contracts/tool_contract.md.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class ToolAudit(BaseModel):
    trace_id: str
    run_id: str
    invoker_id: str
    timestamp_utc: str
    duration_ms: int
    parameters_hash: Optional[str] = None


class ToolError(BaseModel):
    code: str
    message: str
    retryable: bool
    details: Optional[Dict[str, Any]] = None


class ToolExecutionEnvelope(BaseModel):
    execution_id: str
    tool_name: str
    status: str  # SUCCESS, FAILED, TIMED_OUT, PERMISSION_DENIED
    data: Optional[Dict[str, Any]] = None
    error: Optional[ToolError] = None
    audit: ToolAudit


class BaseTool(ABC):
    """Abstract base class for all platform tools."""
    name: str
    version: str = "1.0.0"
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    required_permissions: List[str]
    timeout_seconds: int = 30
    is_side_effect_free: bool = False

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the concrete platform logic for this tool."""
        pass


class ToolRegistry:
    """Central registry enforcing schemas, permissions, and audit logging."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    async def dispatch(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any],
        granted_permissions: List[str],
    ) -> ToolExecutionEnvelope:
        execution_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        now_utc = datetime.now(timezone.utc).isoformat()
        trace_id = context.get("trace_id", str(uuid.uuid4()))
        run_id = context.get("run_id", str(uuid.uuid4()))
        invoker_id = context.get("actor", {}).get("id", "anonymous")

        tool = self.get(tool_name)
        if not tool:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ToolExecutionEnvelope(
                execution_id=execution_id,
                tool_name=tool_name,
                status="FAILED",
                error=ToolError(
                    code="RESOURCE_NOT_FOUND",
                    message=f"Tool '{tool_name}' is not registered.",
                    retryable=False,
                ),
                audit=ToolAudit(
                    trace_id=trace_id,
                    run_id=run_id,
                    invoker_id=invoker_id,
                    timestamp_utc=now_utc,
                    duration_ms=duration_ms,
                ),
            )

        # Permission check
        for perm in tool.required_permissions:
            if perm not in granted_permissions:
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                return ToolExecutionEnvelope(
                    execution_id=execution_id,
                    tool_name=tool_name,
                    status="PERMISSION_DENIED",
                    error=ToolError(
                        code="PERMISSION_DENIED",
                        message=f"Missing required permission: '{perm}'.",
                        retryable=False,
                    ),
                    audit=ToolAudit(
                        trace_id=trace_id,
                        run_id=run_id,
                        invoker_id=invoker_id,
                        timestamp_utc=now_utc,
                        duration_ms=duration_ms,
                    ),
                )

        try:
            result = await tool.execute(parameters, context)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ToolExecutionEnvelope(
                execution_id=execution_id,
                tool_name=tool_name,
                status="SUCCESS",
                data=result,
                audit=ToolAudit(
                    trace_id=trace_id,
                    run_id=run_id,
                    invoker_id=invoker_id,
                    timestamp_utc=now_utc,
                    duration_ms=duration_ms,
                ),
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ToolExecutionEnvelope(
                execution_id=execution_id,
                tool_name=tool_name,
                status="FAILED",
                error=ToolError(
                    code="INTERNAL_ERROR",
                    message=str(exc),
                    retryable=True,
                ),
                audit=ToolAudit(
                    trace_id=trace_id,
                    run_id=run_id,
                    invoker_id=invoker_id,
                    timestamp_utc=now_utc,
                    duration_ms=duration_ms,
                ),
            )
