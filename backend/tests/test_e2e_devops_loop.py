"""Phase 14: Golden Path End-to-End Autonomous DevOps Loop Test.

Executes the entire autonomous lifecycle loop end-to-end:
1. Code Change / PR Opened (`PR_OPENED`)
2. AI Code Review & Static Analysis (`REVIEW_COMPLETED`)
3. Test Execution & Result Telemetry (`TEST_COMPLETED`)
4. Deployment Guardrails & Risk Gate Evaluation (`DeploymentGate`)
5. Multi-Cloud Provider Deployment (`DEPLOYMENT_STARTED` -> `DEPLOYMENT_COMPLETED`)
6. Synthetic Health Probes & Monitoring Telemetry (`HealthCheck`)
7. Incident Anomaly Triggered (`INCIDENT_CREATED`)
8. Autonomous AI Root Cause Diagnosis (`DIAGNOSIS_COMPLETED`)
9. Autonomous Remediation / Safe Rollback (`ROLLBACK_COMPLETED`)
10. Post-Mortem Preserved into Semantic Project Memory (`RECOVERY_COMPLETED`)
"""
from __future__ import annotations

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import generate_session_token
from app.db.base import Base, utc_now
from app.db.constants import (
    ActorType,
    DeploymentEnvironment,
    DeploymentProviderType,
    DeploymentState,
    EventType,
    GateStatus,
    IncidentSeverity,
    IncidentStatus,
    MemoryCategory,
    ProjectRole,
    RemediationAction,
    ReviewRisk,
    ReviewVerdict,
)
from app.db.models.deployment import Deployment
from app.db.models.deployment_gate import DeploymentGate
from app.db.models.github_connection import GitHubConnection
from app.db.models.incident import Incident
from app.db.models.memory import ProjectMemoryItem
from app.db.models.monitoring import HealthCheck
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.models.pull_request import PullRequest
from app.db.models.review import Review
from app.db.models.test_run import TestRun
from app.db.models.user import User
from app.db.repositories.deployment_repository import DeploymentRepository
from app.db.repositories.memory_repository import MemoryRepository
from app.services.deployment_service import DeploymentService
from app.services.event_bus import EventBus
from app.services.incident_service import IncidentService
from app.services.memory_service import MemoryService
from app.services.monitoring_service import MonitoringService
from app.services.review_service import ReviewService
from app.services.risk_service import RiskService
from app.services.test_service import TestService

# In-Memory SQLite engine for clean test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.mark.anyio
async def test_full_golden_path_devops_loop(db: Session):
    """Verify complete golden path DevOps loop executes cleanly across all subsystem contracts."""
    event_bus = EventBus(db)
    lifecycle_events = []
    
    # Event ledger subscriber
    def track_event(evt):
        lifecycle_events.append(evt.event_type)

    for et in EventType:
        event_bus.subscribe(et, track_event)

    # -------------------------------------------------------------
    # 0. Setup User, Project & Initial Stable Deployment
    # -------------------------------------------------------------
    owner = User(email="architect@goldenpath.io", display_name="Lead Architect", is_active=True)
    db.add(owner)
    db.flush()

    project = Project(name="Autonomous E2E Core", slug="auto-e2e-core", owner_id=owner.id, is_archived=False)
    db.add(project)
    db.flush()

    db.add(ProjectMember(project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER.value))
    db.commit()

    dep_repo = DeploymentRepository(db)
    # Seed prior known stable production deployment (rollback target)
    stable_dep = dep_repo.create_deployment(
        project_id=project.id,
        provider=DeploymentProviderType.RENDER.value,
        environment=DeploymentEnvironment.PRODUCTION.value,
        commit_sha="stable_v1_0_0",
        branch="main",
        initial_state=DeploymentState.SUCCESS.value,
    )
    db.commit()

    # -------------------------------------------------------------
    # 1. Developer opens PR (PullRequest created)
    # -------------------------------------------------------------
    clean_diff = """diff --git a/services/pricing.py b/services/pricing.py
new file mode 100644
index 0000000..789abc1
--- /dev/null
+++ b/services/pricing.py
@@ -0,0 +1,12 @@
+def calculate_discount(price: float, discount_pct: float) -> float:
+    if discount_pct < 0 or discount_pct > 1.0:
+        raise ValueError("Invalid discount percentage")
+    return price * (1.0 - discount_pct)
"""
    conn = GitHubConnection(
        project_id=project.id,
        owner="goldenpath",
        repo_name="autonomous-app",
        default_branch="main",
        personal_access_token_hash="mock_token_hash_for_test",
        is_active=True,
    )
    db.add(conn)
    db.flush()

    pr = PullRequest(
        github_connection_id=conn.id,
        pull_number=42,
        title="feat: add robust pricing calculation service",
        author="dev-ninja",
        base_branch="main",
        head_branch="feat/pricing",
        head_sha="head_sha_42a",
        diff_text=clean_diff,
        changed_files=1,
        additions=12,
        deletions=0,
        state="OPEN",
    )
    db.add(pr)
    db.commit()

    event_bus.emit(
        event_type=EventType.PR_OPENED,
        project_id=project.id,
        actor_id=str(owner.id),
        actor_type=ActorType.USER,
        payload={"pull_number": pr.pull_number, "title": pr.title, "head_sha": pr.head_sha},
    )
    assert EventType.PR_OPENED.value in lifecycle_events

    # -------------------------------------------------------------
    # 2. AI Code Review Service
    # -------------------------------------------------------------
    review_svc = ReviewService(db)
    review_result = review_svc.execute_review(
        project_id=project.id,
        pull_number=pr.pull_number,
        user_id=owner.id,
        post_to_github=False,
    )
    assert review_result.verdict in (ReviewVerdict.APPROVE, ReviewVerdict.COMMENT)
    assert EventType.REVIEW_COMPLETED.value in lifecycle_events

    # -------------------------------------------------------------
    # 3. Test Execution Service
    # -------------------------------------------------------------
    test_svc = TestService(db)
    test_run = test_svc.run_tests(
        project_id=project.id,
        pull_number=pr.pull_number,
        suite_name="unit",
    )
    assert test_run.passed is True
    assert EventType.TEST_COMPLETED.value in lifecycle_events

    # -------------------------------------------------------------
    # 4. Deployment Guardrails & Risk Gate Evaluation
    # -------------------------------------------------------------
    risk_svc = RiskService(db)
    gate = risk_svc.evaluate_gate(
        project_id=project.id,
        pull_request_id=pr.id,
    )
    assert gate.gate_status == GateStatus.PASSED.value

    # -------------------------------------------------------------
    # 5. Multi-Cloud Deployment Service (Phase 8)
    # -------------------------------------------------------------
    dep_svc = DeploymentService(db, event_bus)
    deployment = await dep_svc.trigger_deployment(
        project_id=project.id,
        provider="render",
        environment="production",
        commit_sha=pr.head_sha,
        branch=pr.head_branch,
        pull_request_id=pr.id,
        gate_id=gate.id,
    )
    assert deployment.state == DeploymentState.SUCCESS.value
    assert deployment.url is not None
    assert EventType.DEPLOYMENT_STARTED.value in lifecycle_events
    assert EventType.DEPLOYMENT_COMPLETED.value in lifecycle_events

    # -------------------------------------------------------------
    # 6. Synthetic Health Probes & Monitoring (Phase 9)
    # -------------------------------------------------------------
    mon_svc = MonitoringService(db, event_bus)
    probe = await mon_svc.execute_probe(deployment.id)
    assert probe.is_healthy is True
    assert probe.status_code == 200

    summary = mon_svc.get_health_summary(deployment.id)
    assert summary["status"] == "HEALTHY"
    assert summary["total_probes"] >= 1

    # -------------------------------------------------------------
    # 7. Incident Anomaly Declaration (Phase 10)
    # -------------------------------------------------------------
    inc_svc = IncidentService(db, event_bus, dep_svc)
    incident = inc_svc.create_incident(
        project_id=project.id,
        title="Unexpected Latency Spike & Memory Leak post-deploy",
        severity=IncidentSeverity.SEV1.value,
        deployment_id=deployment.id,
    )
    assert incident.status == IncidentStatus.OPEN.value
    assert EventType.INCIDENT_CREATED.value in lifecycle_events

    # -------------------------------------------------------------
    # 8. Autonomous AI Root Cause Diagnosis (Phase 10)
    # -------------------------------------------------------------
    diag = await inc_svc.diagnose_incident(incident.id)
    assert diag.incident_id == incident.id
    assert diag.recommended_action == RemediationAction.ROLLBACK.value
    assert EventType.DIAGNOSIS_STARTED.value in lifecycle_events
    assert EventType.DIAGNOSIS_COMPLETED.value in lifecycle_events

    # -------------------------------------------------------------
    # 9. Autonomous Remediation / Safe Rollback (Phase 10 & 8)
    # -------------------------------------------------------------
    resolved_inc = await inc_svc.remediate_and_resolve(incident.id, auto_rollback=True)
    assert resolved_inc.status == IncidentStatus.RESOLVED.value
    assert EventType.ROLLBACK_STARTED.value in lifecycle_events
    assert EventType.ROLLBACK_COMPLETED.value in lifecycle_events
    assert EventType.RECOVERY_COMPLETED.value in lifecycle_events

    # Verify active deployment transitioned to ROLLED_BACK
    reloaded_dep = dep_svc.get_deployment(deployment.id)
    assert reloaded_dep.state == DeploymentState.ROLLED_BACK.value

    # -------------------------------------------------------------
    # 10. Semantic Project Memory Verification (Phase 11)
    # -------------------------------------------------------------
    mem_repo = MemoryRepository(db)
    memories = mem_repo.search(project.id, category=MemoryCategory.POSTMORTEM.value)
    assert len(memories) >= 1
    postmortem = memories[0]
    assert "Post-Mortem" in postmortem.content
    assert "SEV1" in postmortem.content
    assert postmortem.importance == 5

    # Verify that the entire end-to-end lifecycle completed successfully
    assert len(lifecycle_events) >= 10
    print(f"\n[Golden Path E2E Passed] {len(lifecycle_events)} platform events recorded in PostgreSQL ledger.")
