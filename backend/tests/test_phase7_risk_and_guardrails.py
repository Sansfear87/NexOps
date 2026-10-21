"""Comprehensive test suite for Phase 7: Risk Assessment, Guardrails, and Gatekeeper Engine."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.constants import (
    ActorType,
    FindingCategory,
    FindingSeverity,
    GateAction,
    GateStatus,
    PRState,
    ProjectRole,
    ReviewRisk,
    ReviewStatus,
    ReviewVerdict,
    TestStatus,
)
from app.db.models.deployment_gate import DeploymentGate, GateAuditLog
from app.db.models.github_connection import GitHubConnection
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.models.pull_request import PullRequest
from app.db.models.review import Review, ReviewFinding
from app.db.models.session import Session as DbSession
from app.db.models.test_run import TestRun
from app.db.models.user import User
from app.db.repositories.deployment_gate_repository import DeploymentGateRepository
from app.db.session import get_db
from app.main import app
from app.services.risk_service import RiskService

# Setup In-Memory SQLite Engine for Phase 7 testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_setup(db: Session):
    """Fixture creating user, project, github connection, and PR with clean relationships."""
    from app.core.security import generate_session_token, encrypt_token
    from app.db.base import utc_now
    from datetime import timedelta
    from app.db.repositories.session_repository import SessionRepository

    user = User(
        email="gatekeeper@nexops.io",
        display_name="Gatekeeper Operator",
        is_active=True,
    )
    db.add(user)
    db.flush()

    project = Project(
        name="Guardrail Monitored App",
        slug="guardrail-monitored-app",
        owner_id=user.id,
    )
    db.add(project)
    db.flush()

    member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role=ProjectRole.OWNER.value,
    )
    db.add(member)

    session_repo = SessionRepository(db)
    raw_token = generate_session_token()
    session_repo.create_session(
        user_id=user.id,
        raw_token=raw_token,
        expires_at=utc_now() + timedelta(days=7),
    )

    encrypted_tok = encrypt_token("mock_token_for_tests_1234567890")
    conn = GitHubConnection(
        project_id=project.id,
        owner="test-org",
        repo_name="test-service",
        default_branch="main",
        personal_access_token_hash=encrypted_tok,
        is_active=True,
    )
    db.add(conn)
    db.flush()

    pr = PullRequest(
        github_connection_id=conn.id,
        pull_number=101,
        title="Payment processor overhaul and database schema migration",
        state=PRState.OPEN.value,
        author="octocat",
        base_branch="main",
        head_branch="feature/payments-v2",
        head_sha="abcdef1234567890abcdef1234567890abcdef12",
        additions=240,
        deletions=40,
        changed_files=3,
        diff_text="""diff --git a/alembic/versions/007_payment_tables.py b/alembic/versions/007_payment_tables.py
new file mode 100644
--- /dev/null
+++ b/alembic/versions/007_payment_tables.py
@@ -0,0 +1,5 @@
+def upgrade():
+    pass
diff --git a/app/security/auth.py b/app/security/auth.py
--- a/app/security/auth.py
+++ b/app/security/auth.py
@@ -1,5 +1,10 @@
+def secure_eval(data):
+    return eval(data)
diff --git a/app/core/settings.py b/app/core/settings.py
--- a/app/core/settings.py
+++ b/app/core/settings.py
@@ -1,2 +1,3 @@
+STRIPE_WEBHOOK_SECRET = "test"
""",
    )
    db.add(pr)
    db.flush()

    return {
        "user": user,
        "project": project,
        "connection": conn,
        "pr": pr,
        "session_token": raw_token,
    }


def test_risk_service_critical_file_path_detection(db: Session, test_setup):
    """Test that critical path patterns (migrations, auth, config) are correctly detected and scored."""
    service = RiskService(db)
    pr = test_setup["pr"]
    project = test_setup["project"]

    gate = service.evaluate_gate(
        project_id=project.id,
        pull_request_id=pr.id,
    )

    assert gate is not None
    assert gate.project_id == project.id
    assert gate.pull_request_id == pr.id

    # Should detect migration and auth files
    assert any("alembic/versions" in cf for cf in gate.critical_files)
    assert any("app/security/auth.py" in cf for cf in gate.critical_files)
    assert gate.gate_status in (GateStatus.REQUIRES_APPROVAL.value, GateStatus.BLOCKED.value)
    assert gate.risk_score > 30

    # Policy evaluations must contain diff_blast_radius and critical_file_modifications
    rules = [p["rule"] for p in gate.policy_evaluations]
    assert "diff_blast_radius" in rules
    assert "critical_file_modifications" in rules
    assert "automated_tests" in rules
    assert "ai_code_review" in rules


def test_risk_service_test_suite_failure_blocks_gate(db: Session, test_setup):
    """Test that any failing test suite execution immediately sets gate status to BLOCKED."""
    pr = test_setup["pr"]
    project = test_setup["project"]

    # Create a failing TestRun
    failing_test_run = TestRun(
        project_id=project.id,
        pull_request_id=pr.id,
        commit_sha=pr.head_sha,
        suite_name="unit-integration",
        status=TestStatus.FAILED.value,
        passed=False,
        total_tests=25,
        failed_tests=2,
        duration_seconds=12.5,
    )
    db.add(failing_test_run)
    db.flush()

    service = RiskService(db)
    gate = service.evaluate_gate(
        project_id=project.id,
        pull_request_id=pr.id,
        test_run_id=failing_test_run.id,
    )

    assert gate.gate_status == GateStatus.BLOCKED.value
    assert "test suite" in gate.summary.lower()
    assert "failed" in gate.summary.lower()
    assert any("automated test suite failed" in r.lower() for r in gate.reasons)


def test_risk_service_review_blocker_finding_blocks_gate(db: Session, test_setup):
    """Test that a review with BLOCKER severity marks risk as CRITICAL and BLOCKS gate."""
    pr = test_setup["pr"]
    project = test_setup["project"]

    review = Review(
        pull_request_id=pr.id,
        head_sha=pr.head_sha,
        status=ReviewStatus.COMPLETED.value,
        summary="Security flaw detected in auth handler.",
        overall_risk=ReviewRisk.CRITICAL.value,
        verdict=ReviewVerdict.REQUEST_CHANGES.value,
        confidence=0.98,
    )
    db.add(review)
    db.flush()

    finding = ReviewFinding(
        review_id=review.id,
        file="app/security/auth.py",
        line=2,
        category=FindingCategory.SECURITY.value,
        severity=FindingSeverity.BLOCKER.value,
        description="Remote code execution via unsafe eval call.",
        recommendation="Replace eval with strict parser.",
        confidence=1.0,
    )
    db.add(finding)
    db.flush()

    service = RiskService(db)
    gate = service.evaluate_gate(
        project_id=project.id,
        pull_request_id=pr.id,
        review_id=review.id,
    )

    assert gate.gate_status == GateStatus.BLOCKED.value
    assert gate.risk_level == ReviewRisk.CRITICAL.value
    assert any("BLOCKER" in r for r in gate.reasons)


def test_risk_service_clean_pr_passes_gate(db: Session, test_setup):
    """Test that a compact diff touching non-critical files with passing tests passes gate."""
    conn = test_setup["connection"]
    project = test_setup["project"]

    clean_pr = PullRequest(
        github_connection_id=conn.id,
        pull_number=102,
        title="Update README documentation",
        state=PRState.OPEN.value,
        author="octocat",
        base_branch="main",
        head_branch="docs/update",
        head_sha="0000000000000000000000000000000000000001",
        additions=2,
        deletions=0,
        changed_files=1,
        diff_text="""diff --git a/docs/guide.md b/docs/guide.md
--- a/docs/guide.md
+++ b/docs/guide.md
@@ -1 +1,2 @@
+# Guide
+Updated instructions.
""",
    )
    db.add(clean_pr)
    db.flush()

    passing_test_run = TestRun(
        project_id=project.id,
        pull_request_id=clean_pr.id,
        commit_sha=clean_pr.head_sha,
        suite_name="unit",
        status=TestStatus.PASSED.value,
        passed=True,
        total_tests=10,
        failed_tests=0,
        duration_seconds=3.2,
    )
    db.add(passing_test_run)

    clean_review = Review(
        pull_request_id=clean_pr.id,
        head_sha=clean_pr.head_sha,
        status=ReviewStatus.COMPLETED.value,
        summary="Clean documentation update.",
        overall_risk=ReviewRisk.LOW.value,
        verdict=ReviewVerdict.APPROVE.value,
        confidence=1.0,
    )
    db.add(clean_review)
    db.flush()

    service = RiskService(db)
    gate = service.evaluate_gate(
        project_id=project.id,
        pull_request_id=clean_pr.id,
        review_id=clean_review.id,
        test_run_id=passing_test_run.id,
    )

    assert gate.gate_status == GateStatus.PASSED.value
    assert gate.risk_level == ReviewRisk.LOW.value
    assert len(gate.critical_files) == 0
    assert gate.risk_score < 25


def test_gate_approval_rejection_and_bypass_workflows(db: Session, test_setup):
    """Test human approval, rejection, and admin bypass workflows with audit log immutability."""
    user = test_setup["user"]
    project = test_setup["project"]
    pr = test_setup["pr"]

    service = RiskService(db)
    gate = service.evaluate_gate(
        project_id=project.id,
        pull_request_id=pr.id,
    )

    assert gate.gate_status in (GateStatus.REQUIRES_APPROVAL.value, GateStatus.BLOCKED.value)

    # 1. Approval workflow
    approved_gate = service.approve_gate(
        gate_id=gate.id,
        approver_id=user.id,
        notes="Security team verified changes and approved staging rollout.",
    )
    assert approved_gate.gate_status == GateStatus.APPROVED.value
    assert approved_gate.approved_by == user.id
    assert approved_gate.approved_at is not None
    assert "Security team" in approved_gate.approval_notes

    # 2. Check audit logs
    audit_logs = service.gate_repo.get_audit_logs(gate.id)
    actions = [a.action for a in audit_logs]
    assert GateAction.APPROVED.value in actions

    # 3. Rejection workflow
    rejected_gate = service.reject_gate(
        gate_id=gate.id,
        actor_id=user.id,
        reason="Rollback script is missing for Alembic migration.",
    )
    assert rejected_gate.gate_status == GateStatus.REJECTED.value

    # 4. Bypass workflow with mandatory justification
    with pytest.raises(ValueError, match="justification is required"):
        service.bypass_gate(gate_id=gate.id, actor_id=user.id, bypass_reason="")

    bypassed_gate = service.bypass_gate(
        gate_id=gate.id,
        actor_id=user.id,
        bypass_reason="Emergency hotfix approved by VP of Engineering.",
    )
    assert bypassed_gate.gate_status == GateStatus.BYPASSED.value
    assert bypassed_gate.bypass_reason == "Emergency hotfix approved by VP of Engineering."

    # Verify audit logs captured all transitions
    final_logs = service.gate_repo.get_audit_logs(gate.id)
    final_actions = [a.action for a in final_logs]
    assert GateAction.APPROVED.value in final_actions
    assert GateAction.REJECTED.value in final_actions
    assert GateAction.BYPASSED.value in final_actions


def test_api_v1_gates_endpoints(client: TestClient, db: Session, test_setup):
    """Test FastAPI REST endpoints for gate evaluation, listing, approval, and audit trails."""
    session_token = test_setup["session_token"]
    project = test_setup["project"]
    pr = test_setup["pr"]

    headers = {"Authorization": f"Bearer {session_token}"}

    # 1. Evaluate gate via API
    eval_resp = client.post(
        f"/api/v1/projects/{project.id}/gates/evaluate",
        headers=headers,
        json={"pull_request_id": str(pr.id)},
    )
    assert eval_resp.status_code == 200, eval_resp.text
    gate_data = eval_resp.json()
    gate_id = gate_data["id"]
    assert gate_data["project_id"] == str(project.id)
    assert "risk_score" in gate_data
    assert "policy_evaluations" in gate_data

    # 2. List gates for project
    list_resp = client.get(f"/api/v1/projects/{project.id}/gates", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 3. Get single gate by ID
    get_resp = client.get(f"/api/v1/gates/{gate_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == gate_id

    # 4. Approve gate via API
    approve_resp = client.post(
        f"/api/v1/gates/{gate_id}/approve",
        headers=headers,
        json={"notes": "All checks manually verified."},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["gate_status"] == GateStatus.APPROVED.value

    # 5. Get audit logs for gate
    logs_resp = client.get(f"/api/v1/gates/{gate_id}/audit-logs", headers=headers)
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) >= 2
    actions = [l["action"] for l in logs]
    assert GateAction.APPROVED.value in actions

    # 6. Bypass gate via API
    bypass_resp = client.post(
        f"/api/v1/gates/{gate_id}/bypass",
        headers=headers,
        json={"reason": "Emergency production maintenance override."},
    )
    assert bypass_resp.status_code == 200
    assert bypass_resp.json()["gate_status"] == GateStatus.BYPASSED.value
