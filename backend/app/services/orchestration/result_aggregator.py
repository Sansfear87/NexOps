"""Evidence Aggregation and Contradiction Detection across Specialized Agents.

Collects worker outputs, deduplicates findings, identifies discrepancies, and synthesizes
an auditable decision report.
"""
from typing import Any, Dict, List, Optional, Set, Tuple
from app.schemas.agent_results import (
    AggregatedEvidenceReport,
    FindingSeverityLevel,
    StandardFinding,
    WorkerResult,
)


class EvidenceAggregator:
    """Combines evidence from multiple agent roles, reconciles contradictions, and computes aggregate metrics."""

    def aggregate(
        self,
        run_id: str,
        worker_results: List[WorkerResult],
        policy_blocks: Optional[List[str]] = None,
        requires_human_approval: bool = False,
    ) -> AggregatedEvidenceReport:
        """Process worker outputs into a unified decision report."""
        all_findings: List[StandardFinding] = []
        model_trail: List[Dict[str, Any]] = []
        tests_passed = True
        contradictions: List[str] = []

        code_review_approved = False
        security_alert_present = False

        for res in worker_results:
            model_trail.append({
                "task_id": res.task_id,
                "role": res.worker_role,
                "model": res.model_assigned,
                "provider": res.provider,
                "status": res.status.value,
                "confidence": res.confidence,
                "requires_escalation": res.requires_escalation,
                "escalation_reason": res.escalation_reason,
            })

            # Track test status
            if res.worker_role == "test_worker":
                if "failed" in res.summary.lower() or res.metrics.get("tests_failed", 0) > 0:
                    tests_passed = False

            # Track code review sentiment
            if res.worker_role == "code_reviewer":
                if "approved" in res.summary.lower() or "looks good" in res.summary.lower():
                    code_review_approved = True

            # Track security findings
            for finding in res.findings:
                all_findings.append(finding)
                if finding.severity in (FindingSeverityLevel.CRITICAL, FindingSeverityLevel.HIGH):
                    security_alert_present = True

        # Contradiction Detection
        if code_review_approved and security_alert_present:
            contradictions.append(
                "Contradiction detected: Code reviewer marked PR clean, but security analysis identified High/Critical vulnerabilities."
            )

        if code_review_approved and not tests_passed:
            contradictions.append(
                "Contradiction detected: Code reviewer recommended approval, but automated unit/integration tests failed."
            )

        # Deduplicate findings by (file_path, start_line, title)
        deduped_findings: List[StandardFinding] = []
        seen_keys: Set[Tuple[Optional[str], Optional[int], str]] = set()

        for f in all_findings:
            key = (f.file_path, f.start_line, f.title.strip().lower())
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_findings.append(f)

        critical_count = sum(1 for f in deduped_findings if f.severity == FindingSeverityLevel.CRITICAL)
        high_count = sum(1 for f in deduped_findings if f.severity == FindingSeverityLevel.HIGH)

        # Calculate composite risk score (0.0 to 1.0)
        risk_score = 0.1  # baseline
        if not tests_passed:
            risk_score += 0.4
        risk_score += min(0.5, critical_count * 0.35 + high_count * 0.15)
        risk_score = min(1.0, round(risk_score, 2))

        # Overall Status
        blocks = policy_blocks or []
        if blocks or critical_count > 0 or not tests_passed:
            overall_status = "BLOCKED"
            recommendation = "Reject or remediate code changes before re-evaluating."
        elif requires_human_approval:
            overall_status = "REQUIRES_APPROVAL"
            recommendation = "Automated checks passed. Awaiting authorized maintainer approval for deployment."
        else:
            overall_status = "APPROVED"
            recommendation = "All multi-agent reviews, tests, and policy guardrails passed. Safe to merge/deploy."

        return AggregatedEvidenceReport(
            run_id=run_id,
            overall_status=overall_status,
            overall_risk_score=risk_score,
            critical_findings_count=critical_count,
            high_findings_count=high_count,
            total_findings_count=len(deduped_findings),
            deduplicated_findings=deduped_findings,
            contradictions_detected=contradictions,
            tests_passed=tests_passed,
            policy_blocks=blocks,
            requires_human_approval=requires_human_approval,
            model_routing_trail=model_trail,
            final_recommendation=recommendation,
        )
