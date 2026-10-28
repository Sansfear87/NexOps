"""Deterministic Policy Engine for Multi-Agent Workflows.

Enforces non-negotiable architectural guardrails, permission boundaries, and hard gates
that AI models (neither DeepSeek nor Nemotron) are allowed to override.
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class PolicyCheckResult(BaseModel):
    decision: PolicyDecision
    allowed: bool
    requires_human_approval: bool
    reasons: List[str] = Field(default_factory=list)
    violations: List[str] = Field(default_factory=list)


class OrchestrationPolicyEngine:
    """Evaluates deterministic conditions and gates before any deployment or tool execution."""

    DANGEROUS_TOOLS = {
        "deployment.deploy",
        "deployment.rollback",
        "kubernetes.delete_pod",
    }

    def evaluate_release_policy(
        self,
        environment: str,
        tests_passed: bool,
        critical_findings: int,
        high_findings: int,
        risk_score: float,
        has_approval: bool = False,
    ) -> PolicyCheckResult:
        """Evaluate mandatory release criteria for staging vs production environments."""
        env = environment.lower()
        violations: List[str] = []
        reasons: List[str] = []

        # 1. Mandatory Test Pass Criterion
        if not tests_passed:
            violations.append("Mandatory test suite failed. Deployment is strictly blocked.")

        # 2. Critical Security & Correctness Blocker
        if critical_findings > 0:
            violations.append(f"Blocked by {critical_findings} CRITICAL severity finding(s). Must be remediated.")

        # 3. High Finding Threshold
        if env == "production" and high_findings >= 3:
            violations.append(f"Production blocked: Accumulation of {high_findings} HIGH severity findings exceeds policy threshold (max 2).")

        # If any hard violations exist, the release is strictly BLOCKED
        if violations:
            return PolicyCheckResult(
                decision=PolicyDecision.BLOCK,
                allowed=False,
                requires_human_approval=False,
                reasons=["Policy violation detected; models cannot override hard criteria."],
                violations=violations,
            )

        # 4. Human Approval Gates
        needs_approval = False
        if env == "production":
            needs_approval = True
            reasons.append("Production release requires explicit human sign-off.")
        elif risk_score >= 0.70:
            needs_approval = True
            reasons.append(f"Risk score ({risk_score:.2f}) meets or exceeds 0.70 threshold; human confirmation required.")

        if needs_approval and not has_approval:
            return PolicyCheckResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                allowed=False,
                requires_human_approval=True,
                reasons=reasons,
                violations=[],
            )

        # Release is approved and allowed
        return PolicyCheckResult(
            decision=PolicyDecision.ALLOW,
            allowed=True,
            requires_human_approval=False,
            reasons=["All automated quality, test, and security gates passed."],
            violations=[],
        )

    def validate_tool_dispatch(
        self,
        tool_name: str,
        worker_role: str,
        granted_permissions: List[str],
        parameters: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Validate that a worker's proposed tool action is authorized and within its role boundaries."""
        # 1. Verify read-only workers cannot call mutative/dangerous tools
        if worker_role in ("code_reviewer", "security_reviewer") and tool_name in self.DANGEROUS_TOOLS:
            return PolicyCheckResult(
                decision=PolicyDecision.BLOCK,
                allowed=False,
                requires_human_approval=False,
                reasons=[f"Worker '{worker_role}' is read-only and cannot invoke mutating tool '{tool_name}'."],
                violations=["Unauthorized tool invocation attempt by reviewer agent."],
            )

        # 2. Check required permissions
        if tool_name == "deployment.deploy" and "deploy:production" not in granted_permissions and "deploy:staging" not in granted_permissions:
            return PolicyCheckResult(
                decision=PolicyDecision.BLOCK,
                allowed=False,
                requires_human_approval=False,
                reasons=["Missing required deployment permissions."],
                violations=["Permission denied for deployment.deploy"],
            )

        return PolicyCheckResult(
            decision=PolicyDecision.ALLOW,
            allowed=True,
            requires_human_approval=False,
            reasons=["Tool execution permitted."],
            violations=[],
        )
