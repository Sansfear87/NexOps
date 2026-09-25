from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
from enum import Enum
import re

class AgentRole(str, Enum):
    REVIEWER = "REVIEWER"  # Code review specialist
    DEPLOYER = "DEPLOYER"  # Deployment specialist
    DIAGNOSTICIAN = "DIAGNOSTICIAN"  # Incident diagnosis specialist
    MONITOR = "MONITOR"  # Health monitoring specialist
    PLANNER = "PLANNER"  # Task planning/coordination

@dataclass
class AgentCapability:
    role: AgentRole
    description: str
    supported_tools: list[str]  # tools this agent can use
    supported_goals: list[str]  # regex patterns of goals this agent handles

@dataclass
class HandoffRequest:
    from_role: AgentRole
    to_role: AgentRole
    reason: str
    context: dict  # state to pass to the next agent
    goal: str  # the sub-goal for the target agent

class AgentOrchestrator:
    """Routes goals to specialized agents and manages handoffs."""
    
    def __init__(self):
        self.capabilities: dict[AgentRole, AgentCapability] = {}
        self._register_defaults()
        
    def _register_defaults(self):
        self.register_capability(AgentCapability(
            role=AgentRole.REVIEWER,
            description="Specializes in code reviews and static analysis",
            supported_tools=["github_api", "code_analyzer"],
            supported_goals=["review.*", "analyze code.*", "pr.*"]
        ))
        self.register_capability(AgentCapability(
            role=AgentRole.DEPLOYER,
            description="Specializes in deployment and rollback",
            supported_tools=["deploy_tool", "test_runner"],
            supported_goals=["deploy.*", "rollback.*", "release.*"]
        ))
        self.register_capability(AgentCapability(
            role=AgentRole.DIAGNOSTICIAN,
            description="Specializes in incident analysis and debugging",
            supported_tools=["log_viewer", "metrics_viewer"],
            supported_goals=["diagnose.*", "investigate.*", "incident.*", "fix.*"]
        ))
        
    def register_capability(self, capability: AgentCapability) -> None:
        self.capabilities[capability.role] = capability
        
    def select_agent(self, goal: str, available_tools: list[str]) -> AgentRole:
        """Determine which specialized agent should handle this goal."""
        goal_lower = goal.lower()
        
        for capability in self.capabilities.values():
            for pattern in capability.supported_goals:
                if re.search(pattern, goal_lower):
                    return capability.role
                    
        return AgentRole.PLANNER
        
    def should_handoff(self, current_role: AgentRole, observation: dict) -> HandoffRequest | None:
        """Check if current agent should hand off to another."""
        if current_role == AgentRole.REVIEWER:
            if observation.get("critical_issue_found") and observation.get("needs_rollback"):
                return self.create_handoff(
                    from_role=current_role,
                    to_role=AgentRole.DEPLOYER,
                    reason="Critical issue found in review, initiating rollback",
                    context=observation,
                    goal="Rollback recent deployment"
                )
        return None
        
    def create_handoff(self, from_role: AgentRole, to_role: AgentRole, reason: str, context: dict, goal: str) -> HandoffRequest:
        return HandoffRequest(
            from_role=from_role,
            to_role=to_role,
            reason=reason,
            context=context,
            goal=goal
        )
        
    def get_system_prompt_for_role(self, role: AgentRole) -> str:
        """Return specialized system prompt for each agent role."""
        prompts = {
            AgentRole.REVIEWER: "You are a code review specialist. Your goal is to identify bugs, security issues, and style violations.",
            AgentRole.DEPLOYER: "You are a deployment specialist. Your goal is to ensure safe deployments and quick rollbacks if needed.",
            AgentRole.DIAGNOSTICIAN: "You are an incident diagnostician. Your goal is to analyze logs and metrics to find root causes.",
            AgentRole.MONITOR: "You are a health monitoring specialist. Your goal is to watch system metrics and alert on anomalies.",
            AgentRole.PLANNER: "You are a task planner. Your goal is to coordinate work and break down complex tasks."
        }
        return prompts.get(role, "You are a helpful AI assistant.")
