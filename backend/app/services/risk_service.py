"""Phase 7: Risk Assessment, Guardrails, and Deployment Gatekeeper Engine.

Deterministic safety evaluation enforcing pre-deployment gates based on:
1. Diff size and blast radius
2. Critical path modifications (database migrations, security/auth, infra configs)
3. Automated test suite execution results
4. AI code review findings and severity scores
5. Human-in-the-loop approvals and bypass audit trails
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.constants import (
    ActorType,
    FindingSeverity,
    GateAction,
    GateStatus,
    ReviewRisk,
    TestStatus,
)
from app.db.models.deployment_gate import DeploymentGate, GateAuditLog
from app.db.models.pull_request import PullRequest
from app.db.models.review import Review
from app.db.models.test_run import TestRun
from app.db.repositories.deployment_gate_repository import DeploymentGateRepository
from app.db.repositories.pull_request_repository import PullRequestRepository
from app.db.repositories.review_repository import ReviewRepository
from app.db.repositories.test_run_repository import TestRunRepository
from app.schemas.deployment_gate import PolicyRuleResultSchema
from app.services.diff_parser import DiffParser
from app.services.event_bus import EventBus

logger = logging.getLogger(__name__)


# Critical path regex patterns that indicate high architectural or operational blast radius
CRITICAL_PATH_PATTERNS = [
    (
        re.compile(r"(alembic/versions/|migrations?/|schema\.sql)", re.IGNORECASE),
        "Database Migration",
        35,
        "Database schema alteration detected; requires verification of rollback compatibility.",
    ),
    (
        re.compile(r"(auth|security|jwt|oauth|password|credential|crypto|session|permission)", re.IGNORECASE),
        "Security & Authentication",
        30,
        "Authentication, authorization, or cryptographic module modified.",
    ),
    (
        re.compile(r"(\.github/workflows/|Dockerfile|docker-compose|k8s/|kubernetes/|render\.yaml|vercel\.json)", re.IGNORECASE),
        "CI/CD & Infrastructure",
        25,
        "Deployment manifest, container configuration, or CI pipeline modified.",
    ),
    (
        re.compile(r"(\.env|settings\.py|config\.py|requirements\.txt|poetry\.lock|package\.json|pyproject\.toml)", re.IGNORECASE),
        "Core Configuration & Dependencies",
        15,
        "Project dependencies or application settings changed.",
    ),
]


class RiskService:
    """Service evaluating deployment guardrails and managing human-in-the-loop gates."""

    def __init__(self, db: Session, event_bus: Optional[EventBus] = None):
        self.db = db
        self.event_bus = event_bus or EventBus(db)
        self.gate_repo = DeploymentGateRepository(db)
        self.pr_repo = PullRequestRepository(db)
        self.review_repo = ReviewRepository(db)
        self.test_repo = TestRunRepository(db)

    def evaluate_gate(
        self,
        project_id: UUID,
        pull_request_id: UUID,
        review_id: Optional[UUID] = None,
        test_run_id: Optional[UUID] = None,
        actor_id: Optional[UUID] = None,
        actor_type: ActorType = ActorType.SYSTEM,
    ) -> DeploymentGate:
        """Run deterministic guardrail policies against a PR, its review findings, and test runs."""
        pr = self.pr_repo.get_by_id(pull_request_id)
        if not pr:
            raise ValueError(f"Pull request with ID '{pull_request_id}' not found.")

        # Resolve latest review if not explicitly provided
        review: Optional[Review] = None
        if review_id:
            review = self.review_repo.get_with_findings(review_id)
        else:
            review = self.review_repo.get_latest_by_pull_request(pull_request_id)

        # Resolve latest test run if not explicitly provided
        test_run: Optional[TestRun] = None
        if test_run_id:
            test_run = self.test_repo.get_with_results(test_run_id)
        else:
            test_run = self.test_repo.get_latest_by_pull_request(pull_request_id)

        # 1. Evaluate individual guardrail policies
        policies: List[PolicyRuleResultSchema] = []
        critical_files: List[str] = []
        reasons: List[str] = []
        accumulated_score = 0
        has_test_failure = False
        has_blocker_finding = False

        # Rule 1: Diff size / Blast radius
        diff_text = pr.diff_text or ""
        parsed_files = DiffParser().parse_unified_diff(diff_text) if diff_text else []

        total_lines_added = pr.additions if (pr.additions or 0) > 0 else sum(f.additions for f in parsed_files)
        total_lines_deleted = pr.deletions if (pr.deletions or 0) > 0 else sum(f.deletions for f in parsed_files)
        lines_changed = total_lines_added + total_lines_deleted
        if lines_changed == 0 and diff_text:
            lines_changed = len([l for l in diff_text.splitlines() if l.startswith("+") or l.startswith("-")])

        if lines_changed > 500:
            diff_score = 30
            passed = False
            detail = f"Diff size is large ({lines_changed} lines changed > 500 threshold)."
            reasons.append(detail)
        elif lines_changed > 150:
            diff_score = 15
            passed = True
            detail = f"Diff size is moderate ({lines_changed} lines changed)."
        else:
            diff_score = 0
            passed = True
            detail = f"Diff size is compact ({lines_changed} lines changed)."

        policies.append(PolicyRuleResultSchema(
            rule="diff_blast_radius",
            passed=passed,
            score=diff_score,
            detail=detail,
        ))
        accumulated_score += diff_score

        # Rule 2: Critical file paths
        file_names = [f.filename for f in parsed_files]
        if not file_names and diff_text:
            for line in diff_text.splitlines():
                if line.startswith("+++ b/"):
                    file_names.append(line.replace("+++ b/", "").strip())

        crit_score = 0
        matched_categories = set()
        for filename in file_names:
            for pattern, category, score, note in CRITICAL_PATH_PATTERNS:
                if pattern.search(filename):
                    if filename not in critical_files:
                        critical_files.append(filename)
                    if category not in matched_categories:
                        matched_categories.add(category)
                        crit_score += score
                        reasons.append(f"{category} modified: `{filename}` ({note})")

        crit_score = min(40, crit_score)
        policies.append(PolicyRuleResultSchema(
            rule="critical_file_modifications",
            passed=(len(critical_files) == 0),
            score=crit_score,
            detail=f"{len(critical_files)} critical path file(s) modified across {len(matched_categories)} categories.",
        ))
        accumulated_score += crit_score

        # Rule 3: Automated Test Runner Results
        if test_run:
            if test_run.status == TestStatus.FAILED.value or test_run.failed_tests > 0:
                has_test_failure = True
                test_score = 50
                test_passed = False
                detail = f"Automated test suite failed ({test_run.failed_tests}/{test_run.total_tests} failed)."
                reasons.append(detail)
            elif test_run.status == TestStatus.PASSED.value:
                test_score = 0
                test_passed = True
                detail = f"Automated test suite passed ({test_run.total_tests}/{test_run.total_tests} passing)."
            else:
                test_score = 25
                test_passed = False
                detail = f"Automated test run status is '{test_run.status}' (incomplete)."
                reasons.append(detail)
        else:
            test_score = 20
            test_passed = False
            detail = "No automated test run recorded for this pull request."
            reasons.append(detail)

        policies.append(PolicyRuleResultSchema(
            rule="automated_tests",
            passed=test_passed,
            score=test_score,
            detail=detail,
        ))
        accumulated_score += test_score

        # Rule 4: AI Code Review Findings
        if review:
            review_score = 0
            blockers = [f for f in review.findings if f.severity == FindingSeverity.BLOCKER.value]
            errors = [f for f in review.findings if f.severity == FindingSeverity.ERROR.value]
            warnings = [f for f in review.findings if f.severity == FindingSeverity.WARNING.value]

            if blockers:
                has_blocker_finding = True
                review_score += 50
                detail = f"AI review flagged {len(blockers)} BLOCKER security/correctness finding(s)."
                reasons.append(detail)
            elif errors:
                review_score += 30
                detail = f"AI review flagged {len(errors)} ERROR finding(s)."
                reasons.append(detail)
            elif warnings:
                review_score += 10
                detail = f"AI review flagged {len(warnings)} WARNING finding(s)."
            else:
                detail = "AI review passed with zero blockers or errors."

            review_passed = (len(blockers) == 0 and len(errors) == 0)
        else:
            review_score = 20
            review_passed = False
            detail = "No AI code review completed for this pull request."
            reasons.append(detail)

        policies.append(PolicyRuleResultSchema(
            rule="ai_code_review",
            passed=review_passed,
            score=review_score,
            detail=detail,
        ))
        accumulated_score += review_score

        # 2. Derive overall risk level and gate status
        final_risk_score = min(100, accumulated_score)

        if has_blocker_finding or final_risk_score >= 75:
            overall_risk = ReviewRisk.CRITICAL
        elif final_risk_score >= 50 or (review and any(f.severity == FindingSeverity.ERROR.value for f in review.findings)):
            overall_risk = ReviewRisk.HIGH
        elif final_risk_score >= 25 or len(critical_files) > 0:
            overall_risk = ReviewRisk.MEDIUM
        else:
            overall_risk = ReviewRisk.LOW

        # Gate status determination:
        # - Any test failure or review BLOCKER -> BLOCKED
        # - HIGH or CRITICAL risk -> REQUIRES_APPROVAL
        # - Otherwise -> PASSED
        if has_test_failure:
            gate_status = GateStatus.BLOCKED
            summary = "Deployment BLOCKED: Automated test suite execution failed."
        elif has_blocker_finding:
            gate_status = GateStatus.BLOCKED
            summary = "Deployment BLOCKED: Critical security or architectural blocker detected."
        elif overall_risk in (ReviewRisk.HIGH, ReviewRisk.CRITICAL) or len(critical_files) > 0:
            gate_status = GateStatus.REQUIRES_APPROVAL
            summary = f"Deployment REQUIRES APPROVAL: Evaluated as {overall_risk.value} risk (score: {final_risk_score}/100)."
        else:
            gate_status = GateStatus.PASSED
            summary = f"Deployment PASSED safety gates: Evaluated as {overall_risk.value} risk (score: {final_risk_score}/100)."

        # 3. Persist gate record and audit log
        gate = self.gate_repo.create_gate(
            project_id=project_id,
            pull_request_id=pull_request_id,
            review_id=review.id if review else None,
            test_run_id=test_run.id if test_run else None,
            risk_level=overall_risk,
            gate_status=gate_status,
            risk_score=final_risk_score,
            summary=summary,
            reasons=reasons,
            critical_files=critical_files,
            policy_evaluations=[p.model_dump() for p in policies],
            actor_id=actor_id,
            actor_type=actor_type,
        )

        return gate

    def approve_gate(
        self,
        gate_id: UUID,
        approver_id: UUID,
        notes: Optional[str] = None,
    ) -> DeploymentGate:
        """Human-in-the-loop approval allowing a gated deployment to proceed."""
        gate = self.gate_repo.get_by_id(gate_id)
        if not gate:
            raise ValueError(f"Deployment gate with ID '{gate_id}' not found.")

        if gate.gate_status in (GateStatus.APPROVED.value, GateStatus.PASSED.value):
            return gate  # Already approved or passed

        updated_gate = self.gate_repo.update_gate_status(
            gate_id=gate_id,
            action=GateAction.APPROVED,
            new_status=GateStatus.APPROVED,
            actor_id=approver_id,
            actor_type=ActorType.USER,
            reason=notes or "Operator approved deployment gate.",
            approval_notes=notes,
            metadata={"previous_gate_status": gate.gate_status, "risk_score": gate.risk_score},
        )
        return updated_gate

    def reject_gate(
        self,
        gate_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> DeploymentGate:
        """Human operator rejects deployment progression."""
        gate = self.gate_repo.get_by_id(gate_id)
        if not gate:
            raise ValueError(f"Deployment gate with ID '{gate_id}' not found.")

        updated_gate = self.gate_repo.update_gate_status(
            gate_id=gate_id,
            action=GateAction.REJECTED,
            new_status=GateStatus.REJECTED,
            actor_id=actor_id,
            actor_type=ActorType.USER,
            reason=reason,
            metadata={"previous_gate_status": gate.gate_status},
        )
        return updated_gate

    def bypass_gate(
        self,
        gate_id: UUID,
        actor_id: UUID,
        bypass_reason: str,
    ) -> DeploymentGate:
        """Admin overrides and bypasses a blocked or approval-required gate with mandatory audit justification."""
        if not bypass_reason or len(bypass_reason.strip()) < 5:
            raise ValueError("A non-empty, detailed justification is required to bypass deployment guardrails.")

        gate = self.gate_repo.get_by_id(gate_id)
        if not gate:
            raise ValueError(f"Deployment gate with ID '{gate_id}' not found.")

        updated_gate = self.gate_repo.update_gate_status(
            gate_id=gate_id,
            action=GateAction.BYPASSED,
            new_status=GateStatus.BYPASSED,
            actor_id=actor_id,
            actor_type=ActorType.USER,
            reason=bypass_reason,
            bypass_reason=bypass_reason,
            metadata={
                "previous_gate_status": gate.gate_status,
                "risk_score": gate.risk_score,
                "risk_level": gate.risk_level,
            },
        )
        return updated_gate

    def get_gate_with_audit(self, gate_id: UUID) -> Optional[DeploymentGate]:
        """Fetch deployment gate with loaded audit logs."""
        return self.gate_repo.get_by_id(gate_id)
