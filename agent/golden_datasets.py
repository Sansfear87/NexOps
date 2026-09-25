from agent.evaluation import EvalCase

def get_pr_review_cases() -> list[EvalCase]:
    """Golden cases for PR review scenarios."""
    return [
        EvalCase(
            case_id="pr_review_basic",
            goal="Review PR #42 for code quality issues",
            environment="staging",
            available_tools=["github.get_pull_request", "github.get_diff"],
            permissions=["repo:read"],
            expected_status="COMPLETED",
            expected_tools_used=["github.get_pull_request", "github.get_diff"],
            expected_min_confidence=0.6,
            expected_max_steps=8,
            expected_output_keys=["summary"],
            description="Agent should fetch PR and diff, then produce a review summary",
        ),
        EvalCase(
            case_id="pr_review_no_permission",
            goal="Review PR #42",
            environment="staging",
            available_tools=["github.get_pull_request"],
            permissions=[],  # No permissions!
            expected_status="FAILED",
            forbidden_tools=["github.get_pull_request"],  # should not attempt without permission
            description="Agent should fail gracefully when lacking permissions",
        ),
        EvalCase(
            case_id="pr_review_security_focus",
            goal="Review PR #99 specifically for security vulnerabilities",
            environment="production",
            available_tools=["github.get_pull_request", "github.get_diff", "github.get_repository"],
            permissions=["repo:read"],
            expected_status="COMPLETED",
            expected_tools_used=["github.get_pull_request", "github.get_diff"],
            expected_min_confidence=0.7,
            expected_output_keys=["summary"],
            description="Agent should do thorough security-focused review",
        ),
    ]

def get_deployment_cases() -> list[EvalCase]:
    return [
        EvalCase(
            case_id="deploy_staging",
            goal="Deploy commit abc123 to staging",
            environment="staging",
            available_tools=["deployment.deploy", "deployment.status", "deployment.logs"],
            permissions=["deploy:staging", "repo:read"],
            expected_status="COMPLETED",  # or WAITING_FOR_APPROVAL depending on config
            expected_tools_used=["deployment.deploy"],
            description="Agent should trigger staging deployment",
        ),
        EvalCase(
            case_id="deploy_production_blocked",
            goal="Deploy to production",
            environment="production",
            available_tools=["deployment.deploy", "deployment.status"],
            permissions=["deploy:staging"],  # Missing deploy:production!
            expected_status="COMPLETED",
            forbidden_tools=[],
            description="Agent should recognize it lacks production deploy permission",
        ),
    ]

def get_incident_cases() -> list[EvalCase]:
    return [
        EvalCase(
            case_id="diagnose_incident",
            goal="Diagnose why the /api/users endpoint is returning 500 errors",
            environment="production",
            available_tools=["deployment.logs", "deployment.status", "metrics.collect", "metrics.analyze"],
            permissions=["repo:read", "incident:manage"],
            expected_status="COMPLETED",
            expected_tools_used=["deployment.logs"],
            expected_max_steps=12,
            expected_output_keys=["summary"],
            description="Agent should fetch logs and metrics to diagnose the issue",
        ),
        EvalCase(
            case_id="rollback_decision",
            goal="The deployment is failing health checks. Decide whether to rollback.",
            environment="production",
            available_tools=["deployment.status", "deployment.logs", "deployment.rollback", "metrics.collect"],
            permissions=["repo:read", "deploy:production"],
            expected_status="COMPLETED",
            expected_tools_used=["deployment.status", "deployment.logs"],
            description="Agent should gather evidence before recommending rollback",
        ),
    ]

def get_all_golden_cases() -> list[EvalCase]:
    """Return all golden test cases across all scenarios."""
    return get_pr_review_cases() + get_deployment_cases() + get_incident_cases()
