"""Canonical enums and domain constants for database entities."""
from enum import Enum


class AuthProvider(str, Enum):
    PASSWORD = "password"
    GITHUB = "github"
    GOOGLE = "google"


class ProjectRole(str, Enum):
    OWNER = "OWNER"
    MAINTAINER = "MAINTAINER"
    DEVELOPER = "DEVELOPER"
    VIEWER = "VIEWER"


class ActorType(str, Enum):
    USER = "USER"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"
    WEBHOOK = "WEBHOOK"
    HEALTH_MONITOR = "HEALTH_MONITOR"


class AuditResult(str, Enum):
    SUCCESS = "SUCCESS"
    DENIED = "DENIED"
    ERROR = "ERROR"


class PRState(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    MERGED = "MERGED"


class WebhookEventType(str, Enum):
    PR_OPENED = "PR_OPENED"
    PR_UPDATED = "PR_UPDATED"
    PR_CLOSED = "PR_CLOSED"
    PR_MERGED = "PR_MERGED"
    PUSH = "PUSH"


class EventType(str, Enum):
    PR_OPENED = "PR_OPENED"
    PR_UPDATED = "PR_UPDATED"
    REVIEW_STARTED = "REVIEW_STARTED"
    REVIEW_COMPLETED = "REVIEW_COMPLETED"
    TEST_STARTED = "TEST_STARTED"
    TEST_COMPLETED = "TEST_COMPLETED"
    DEPLOYMENT_STARTED = "DEPLOYMENT_STARTED"
    DEPLOYMENT_COMPLETED = "DEPLOYMENT_COMPLETED"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
    HEALTH_CHECK_FAILED = "HEALTH_CHECK_FAILED"
    INCIDENT_CREATED = "INCIDENT_CREATED"
    DIAGNOSIS_STARTED = "DIAGNOSIS_STARTED"
    DIAGNOSIS_COMPLETED = "DIAGNOSIS_COMPLETED"
    ROLLBACK_STARTED = "ROLLBACK_STARTED"
    ROLLBACK_COMPLETED = "ROLLBACK_COMPLETED"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReviewRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReviewVerdict(str, Enum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT = "COMMENT"


class FindingCategory(str, Enum):
    SECURITY = "SECURITY"
    BUG = "BUG"
    PERFORMANCE = "PERFORMANCE"
    ARCHITECTURE = "ARCHITECTURE"
    STYLE = "STYLE"
    TESTING = "TESTING"
    DEVOPS = "DEVOPS"


class FindingSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    BLOCKER = "BLOCKER"


class TestStatus(str, Enum):
    __test__ = False
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class TestCaseStatus(str, Enum):
    __test__ = False
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


# Phase 7: Risk Assessment and Deployment Guardrails
RiskLevel = ReviewRisk


class GateStatus(str, Enum):
    PASSED = "PASSED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    BYPASSED = "BYPASSED"


class GateAction(str, Enum):
    EVALUATED = "EVALUATED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BYPASSED = "BYPASSED"
    POLICY_OVERRIDDEN = "POLICY_OVERRIDDEN"


# Phase 8: Deployment States and Providers
class DeploymentState(str, Enum):
    PENDING = "PENDING"
    BUILDING = "BUILDING"
    TESTING = "TESTING"
    APPROVED = "APPROVED"
    DEPLOYING = "DEPLOYING"
    HEALTH_CHECK = "HEALTH_CHECK"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"


class DeploymentProviderType(str, Enum):
    VERCEL = "vercel"
    RENDER = "render"
    NEBIUS = "nebius"


class DeploymentEnvironment(str, Enum):
    STAGING = "staging"
    PRODUCTION = "production"


# Phase 9: Monitoring & Synthetic Health Probes
class HealthProbeStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


# Phase 10: Incident Recovery & Autonomous Diagnosis
class IncidentSeverity(str, Enum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    MITIGATING = "MITIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class RemediationAction(str, Enum):
    ROLLBACK = "ROLLBACK"
    PATCH = "PATCH"
    CONFIG_FIX = "CONFIG_FIX"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"


# Phase 11: Semantic Project Memory
class MemoryCategory(str, Enum):
    POSTMORTEM = "incident_postmortem"
    ARCHITECTURAL_RULE = "architectural_rule"
    REVIEW_HEURISTIC = "review_heuristic"
    RUNBOOK = "runbook"


