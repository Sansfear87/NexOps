"""Standardized JSON Schemas for Multi-Agent Results and Evidence Aggregation.

Adheres strictly to contracts/review_contract.md and multi-agent coordination specifications.
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentTaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


class FindingSeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FindingCategoryType(str, Enum):
    SECURITY = "SECURITY"
    CORRECTNESS = "CORRECTNESS"
    PERFORMANCE = "PERFORMANCE"
    STYLE = "STYLE"
    ARCHITECTURE = "ARCHITECTURE"
    DOCUMENTATION = "DOCUMENTATION"


class StandardFinding(BaseModel):
    """Normalized finding structure produced by review and security worker agents."""
    severity: FindingSeverityLevel
    category: FindingCategoryType
    file_path: Optional[str] = Field(None, description="Path of the affected file")
    start_line: Optional[int] = Field(None, description="Start line of affected code")
    end_line: Optional[int] = Field(None, description="End line of affected code")
    title: str = Field(..., description="Short summary of the issue")
    description: str = Field(..., description="Detailed explanation of the problem")
    evidence: Optional[str] = Field(None, description="Concrete code or log proof")
    suggestion: Optional[str] = Field(None, description="Remediation guidance or code patch")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Model self-assessed confidence")
    rule_id: Optional[str] = Field(None, description="Linter or security rule ID")


class WorkerResult(BaseModel):
    """Structured output returned by each specialized worker agent."""
    task_id: str
    worker_role: str = Field(..., description="code_reviewer, security_reviewer, test_worker, risk_assessor")
    model_assigned: str = Field(..., description="Model ID executing this task (DeepSeek or Nemotron)")
    provider: str = Field(default="nebius", description="Serving platform (e.g. Nebius AI Cloud)")
    status: AgentTaskStatus
    summary: str
    findings: List[StandardFinding] = Field(default_factory=list)
    requires_escalation: bool = Field(default=False)
    escalation_reason: Optional[str] = None
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Latency, token counts, tool calls")
    error_message: Optional[str] = None


class AggregatedEvidenceReport(BaseModel):
    """Comprehensive decision report aggregating evidence from all worker agents."""
    run_id: str
    overall_status: str  # APPROVED, BLOCKED, REQUIRES_APPROVAL
    overall_risk_score: float  # 0.0 to 1.0
    critical_findings_count: int
    high_findings_count: int
    total_findings_count: int
    deduplicated_findings: List[StandardFinding]
    contradictions_detected: List[str]
    tests_passed: bool
    policy_blocks: List[str]
    requires_human_approval: bool
    model_routing_trail: List[Dict[str, Any]]
    final_recommendation: str
