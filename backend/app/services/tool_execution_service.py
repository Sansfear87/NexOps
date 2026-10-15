"""Tool Execution Service connecting Platform ToolRegistry to Agents and Services."""
from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional
from sqlalchemy.orm import Session

from app.tools.base import ToolRegistry, ToolExecutionEnvelope
from app.tools import register_all_tools

logger = logging.getLogger(__name__)


class ToolExecutionService:
    """Service mediating tool discovery, execution boundaries, and agent callbacks."""

    def __init__(self, db: Session, default_context: Optional[Dict[str, Any]] = None):
        self.db = db
        self.default_context = default_context or {}
        self._registry = ToolRegistry()
        register_all_tools(self._registry)

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any],
        permissions: List[str],
    ) -> Dict[str, Any]:
        """Dispatch a tool execution via the ToolRegistry and return envelope as dict.

        Args:
            tool_name: Identifier of the registered tool.
            parameters: Input argument dictionary.
            context: Execution context containing trace IDs, actors, and secrets.
            permissions: Explicit granted permission strings.

        Returns:
            Dictionary matching ToolExecutionEnvelope schema.
        """
        envelope: ToolExecutionEnvelope = await self._registry.dispatch(
            tool_name=tool_name,
            parameters=parameters,
            context=context,
            granted_permissions=permissions,
        )
        return envelope.model_dump()

    def list_available_tools(self) -> List[Dict[str, Any]]:
        """List metadata and schema specifications for all registered tools."""
        tools_info = []
        for name in self._registry.list_tools():
            tool = self._registry.get(name)
            if tool:
                tools_info.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "version": tool.version,
                        "input_schema": tool.input_schema,
                        "output_schema": tool.output_schema,
                        "required_permissions": tool.required_permissions,
                        "timeout_seconds": tool.timeout_seconds,
                        "is_side_effect_free": tool.is_side_effect_free,
                    }
                )
        return tools_info

    def get_tool_executor(
        self, permissions: List[str], context: Optional[Dict[str, Any]] = None
    ) -> Callable[[str, Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]]:
        """Return an async callback function suitable for passing to ReActAgent.

        Args:
            permissions: List of granted permission strings.
            context: Execution context dict passed to tool invocations.

        Returns:
            Async callable `executor(tool_name, parameters) -> dict`.
        """
        effective_context = {**self.default_context, **(context or {})}

        async def executor(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
            envelope = await self._registry.dispatch(
                tool_name=tool_name,
                parameters=parameters,
                context=effective_context,
                granted_permissions=permissions,
            )
            if envelope.status != "SUCCESS":
                error_msg = envelope.error.message if envelope.error else "Unknown tool execution failure."
                logger.error("Tool execution failed: %s - %s", tool_name, error_msg)
                raise RuntimeError(f"Tool {tool_name} failed: {error_msg}")
            return envelope.data or {}

        return executor
