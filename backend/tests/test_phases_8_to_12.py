"""Comprehensive test suite for Phases 8 through 12:
- Phase 8: Deployment Provider Abstraction (Vercel, Render, Nebius), DeploymentService, 10-state machine, rollback, tools
- Phase 9: Monitoring & Synthetic Probes, Health Telemetry, Anomaly Detection
- Phase 10: Incident Recovery, Autonomous Diagnosis, Automated Rollback
- Phase 11: Project Persistent Memory, Secret Sanitization, Semantic Retrieval
- Phase 12: Nebius AI Cloud & Nemotron Model Router
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Generator
import uuid
import pytest
from fastapi.testclient import TestClient
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
)
from app.db.models.deployment import Deployment, DeploymentLog
from app.db.models.deployment_gate import DeploymentGate
from app.db.models.github_connection import GitHubConnection
from app.db.models.incident import Incident
from app.db.models.memory import ProjectMemoryItem
from app.db.models.monitoring import HealthCheck, HealthMetric
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.models.pull_request import PullRequest
from app.db.models.session import Session as DbSession
from app.db.models.user import User
from app.db.repositories.deployment_repository import DeploymentRepository
from app.db.repositories.incident_repository import IncidentRepository
from app.db.repositories.memory_repository import MemoryRepository, redact_secrets_from_text
from app.db.repositories.monitoring_repository import MonitoringRepository
from app.db.repositories.session_repository import SessionRepository
from app.db.session import get_db
from app.main import app
from app.providers import NebiusAdapter, RenderAdapter, VercelAdapter
from app.providers.base import DeploymentRequest, RollbackRequest
from app.services.deployment_service import DeploymentService
from app.services.event_bus import EventBus
from app.services.incident_service import IncidentService
from app.services.memory_service import MemoryService
from app.services.model_router import ModelRouter, ModelTaskType, TaskComplexity
from app.services.monitoring_service import MonitoringService
from app.tools.deployment_tools import DeploymentDeploy, DeploymentLogs, DeploymentRollback, DeploymentStatus

# Setup In-Memory SQLite Engine
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
def setup_data(db: Session):
    """Fixture creating user, session, project, and developer membership."""
    from datetime import timedelta

    user = User(
        email="devops@nebius-cloud.io",
        display_name="Cloud Platform Lead",
        is_active=True,
    )
    db.add(user)
    db.flush()

    raw_token = generate_session_token()
    session_repo = SessionRepository(db)
    session_repo.create_session(
        user_id=user.id,
        raw_token=raw_token,
        ip_address="127.0.0.1",
        user_agent="Pytest-Phase8-12",
        expires_at=utc_now() + timedelta(days=7),
    )

    project = Project(
        name="Nebius Autonomous Platform",
        slug="nebius-auto-platform",
        description="Autonomous golden path cloud DevOps service",
        owner_id=user.id,
        is_archived=False,
    )
    db.add(project)
    db.flush()

    member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role=ProjectRole.OWNER.value,
    )
    db.add(member)

    conn = GitHubConnection(
        project_id=project.id,
        owner="test-owner",
        repo_name="test-repo",
        default_branch="main",
        personal_access_token_hash="mock_hash_for_testing",
        is_active=True,
    )
    db.add(conn)
    db.flush()

    pr = PullRequest(
        github_connection_id=conn.id,
        pull_number=101,
        title="feat: autonomous multi-cloud deployment pipeline",
        author="nebius-dev",
        base_branch="main",
        head_branch="feature/phase8-devops",
        head_sha="a1b2c3d4e5f6",
        state="OPEN",
        diff_text="diff --git a/app.py b/app.py",
        additions=10,
        deletions=2,
        changed_files=1,
    )
    db.add(pr)
    db.commit()

    return {
        "user": user,
        "raw_token": raw_token,
        "project": project,
        "pr": pr,
        "headers": {"Authorization": f"Bearer {raw_token}"},
    }


# =========================================================================
# Phase 8: Deployment Providers & Orchestration
# =========================================================================

@pytest.mark.anyio
async def test_provider_adapters_standalone():
    """Verify Vercel, Render, and Nebius adapters implement DeploymentProvider protocol."""
    vercel = VercelAdapter()
    render = RenderAdapter()
    nebius = NebiusAdapter()

    # Vercel deploy
    v_req = DeploymentRequest(
        deployment_id="v_dep_1",
        project_id="proj_1",
        environment="staging",
        commit_sha="a1b2c3d",
        branch="feature",
        provider="vercel",
    )
    v_resp = await vercel.deploy(v_req)
    assert v_resp.state == DeploymentState.DEPLOYING
    assert "vercel.app" in (v_resp.url or "")

    v_logs = await vercel.get_logs(v_resp.provider_deployment_id)
    assert len(v_logs.lines) > 0

    v_roll = await vercel.rollback(RollbackRequest(deployment_id="v_dep_1", reason="test rollback"))
    assert v_roll.state == DeploymentState.ROLLED_BACK

    # Render deploy
    r_req = DeploymentRequest(
        deployment_id="r_dep_1",
        project_id="proj_1",
        environment="production",
        commit_sha="b2c3d4e",
        provider="render",
    )
    r_resp = await render.deploy(r_req)
    assert "onrender.com" in (r_resp.url or "")

    # Nebius deploy
    n_req = DeploymentRequest(
        deployment_id="n_dep_1",
        project_id="proj_1",
        environment="production",
        commit_sha="c3d4e5f",
        provider="nebius",
    )
    n_resp = await nebius.deploy(n_req)
    assert "nebius.cloud" in (n_resp.url or "")


@pytest.mark.anyio
async def test_deployment_service_10_state_progression_and_events(db: Session, setup_data):
    """Verify deployment service transitions through 10-state finite state machine and emits events."""
    project = setup_data["project"]
    event_bus = EventBus(db)
    service = DeploymentService(db, event_bus)

    emitted_events = []
    def capture_event(event):
        emitted_events.append(event.event_type)

    event_bus.subscribe(EventType.DEPLOYMENT_STARTED, capture_event)
    event_bus.subscribe(EventType.DEPLOYMENT_COMPLETED, capture_event)

    dep = await service.trigger_deployment(
        project_id=project.id,
        provider="render",
        environment="staging",
        commit_sha="e1f2a3b4c5d6",
        branch="main",
    )

    assert dep.state == DeploymentState.SUCCESS.value
    assert dep.url is not None
    assert "onrender.com" in dep.url
    assert EventType.DEPLOYMENT_STARTED.value in emitted_events
    assert EventType.DEPLOYMENT_COMPLETED.value in emitted_events

    # Verify logs were ingested into DB
    logs = service.get_logs(dep.id)
    assert len(logs) > 0


@pytest.mark.anyio
async def test_deployment_halted_by_guardrail_gate(db: Session, setup_data):
    """Verify deployment halts with FAILED state if assigned safety gate requires approval."""
    project = setup_data["project"]
    pr = setup_data["pr"]
    
    # Create blocked gate
    gate = DeploymentGate(
        project_id=project.id,
        pull_request_id=pr.id,
        gate_status=GateStatus.REQUIRES_APPROVAL.value,
        risk_score=88,
        summary="High risk changes require manual authorization",
    )
    db.add(gate)
    db.commit()

    service = DeploymentService(db)
    dep = await service.trigger_deployment(
        project_id=project.id,
        provider="vercel",
        environment="production",
        commit_sha=pr.head_sha,
        gate_id=gate.id,
    )

    assert dep.state == DeploymentState.FAILED.value
    assert "Safety gate" in (dep.error_summary or "")


@pytest.mark.anyio
async def test_deployment_rollback_workflow(db: Session, setup_data):
    """Verify deployment rollback flow transitions ROLLING_BACK -> ROLLED_BACK and emits events."""
    project = setup_data["project"]
    event_bus = EventBus(db)
    service = DeploymentService(db, event_bus)

    emitted = []
    event_bus.subscribe(EventType.ROLLBACK_STARTED, lambda e: emitted.append(e.event_type))
    event_bus.subscribe(EventType.ROLLBACK_COMPLETED, lambda e: emitted.append(e.event_type))

    # Create active deployment
    dep = await service.trigger_deployment(
        project_id=project.id,
        provider="render",
        environment="staging",
        commit_sha="first_sha",
    )
    assert dep.state == DeploymentState.SUCCESS.value

    # Trigger rollback
    rolled_back = await service.rollback(dep.id, reason="Testing rollback")
    assert rolled_back.state == DeploymentState.ROLLED_BACK.value
    assert EventType.ROLLBACK_STARTED.value in emitted
    assert EventType.ROLLBACK_COMPLETED.value in emitted


# =========================================================================
# Phase 9: Monitoring & Synthetic Health Probes
# =========================================================================

@pytest.mark.anyio
async def test_monitoring_service_synthetic_probe_and_telemetry(db: Session, setup_data):
    """Verify monitoring service conducts probe, records metrics, and detects health status."""
    project = setup_data["project"]
    dep_service = DeploymentService(db)
    dep = await dep_service.trigger_deployment(
        project_id=project.id,
        provider="render",
        environment="staging",
        commit_sha="probe_sha_1",
    )

    monitoring = MonitoringService(db)
    probe = await monitoring.execute_probe(dep.id)

    assert probe.deployment_id == dep.id
    assert probe.latency_ms >= 0
    assert probe.status_code is not None

    summary = monitoring.get_health_summary(dep.id)
    assert summary["total_probes"] >= 1
    assert "average_latency_ms" in summary
    assert "status" in summary


# =========================================================================
# Phase 10: Incidents & Autonomous Diagnosis
# =========================================================================

@pytest.mark.anyio
async def test_incident_declaration_diagnosis_and_automated_mitigation(db: Session, setup_data):
    """Verify incident lifecycle: declaration, AI root cause diagnosis, 1-click rollback mitigation, and post-mortem creation."""
    project = setup_data["project"]
    dep_service = DeploymentService(db)
    dep = await dep_service.trigger_deployment(
        project_id=project.id,
        provider="nebius",
        environment="production",
        commit_sha="faulty_sha_v1",
    )

    inc_service = IncidentService(db, deployment_service=dep_service)

    # 1. Declare incident
    inc = inc_service.create_incident(
        project_id=project.id,
        title="High error rate on vLLM inference endpoint",
        severity=IncidentSeverity.SEV1.value,
        deployment_id=dep.id,
    )
    assert inc.status == IncidentStatus.OPEN.value
    assert inc.severity == IncidentSeverity.SEV1.value

    # 2. Autonomous Diagnosis
    diag = await inc_service.diagnose_incident(inc.id)
    assert diag.incident_id == inc.id
    assert diag.recommended_action == RemediationAction.ROLLBACK.value
    assert inc.status == IncidentStatus.MITIGATING.value

    # 3. 1-Click Autonomous Mitigation & Rollback
    resolved = await inc_service.remediate_and_resolve(inc.id, auto_rollback=True)
    assert resolved.status == IncidentStatus.RESOLVED.value

    # Verify post-mortem was stored into Project Memory (Phase 11 integration)
    mem_repo = MemoryRepository(db)
    postmortems = mem_repo.search(project.id, category=MemoryCategory.POSTMORTEM.value)
    assert len(postmortems) > 0
    assert "High error rate" in postmortems[0].content


# =========================================================================
# Phase 11: Semantic Project Memory & Secret Sanitization
# =========================================================================

def test_secret_redaction_before_persistence():
    """Verify secret credentials (tokens, passwords) are scrubbed before reaching memory."""
    prefix_stripe = "sk_" + "live_" + "9988776655443322"
    prefix_github = "ghp_" + "112233445566778899aabbccddeeff"
    dirty_text = f"User updated config with stripeKey={prefix_stripe} and token={prefix_github}."
    
    clean_text = redact_secrets_from_text(dirty_text)
    assert prefix_stripe not in clean_text
    assert prefix_github not in clean_text
    assert "[REDACTED_SECRET]" in clean_text


def test_memory_service_store_and_search(db: Session, setup_data):
    """Verify project memory store, key retrieval, and category search."""
    project = setup_data["project"]
    memory_svc = MemoryService(db)

    # Store architectural heuristic
    item = memory_svc.store(
        project_id=project.id,
        key="db_migration_rule",
        content="Always use batch alterations on SQLite in Alembic migrations.",
        category=MemoryCategory.ARCHITECTURAL_RULE.value,
        importance=5,
    )
    assert item.key == "db_migration_rule"
    assert item.importance == 5

    # Retrieve by key
    retrieved = memory_svc.get_by_key(project.id, "db_migration_rule")
    assert retrieved is not None
    assert retrieved.access_count == 1

    # Search by keyword
    results = memory_svc.search(project.id, query="Alembic")
    assert len(results) == 1
    assert results[0].key == "db_migration_rule"


# =========================================================================
# Phase 12: Nebius AI Cloud & Model Router
# =========================================================================

@pytest.mark.anyio
async def test_model_router_decision_and_execution():
    """Verify ModelRouter dispatches fast diff tasks to DeepSeek and high-risk/incident tasks to Nemotron on Nebius."""
    router = ModelRouter(nebius_api_key="mock-key-1234")

    # Fast task -> DeepSeek
    fast_decision = router.decide_route(
        task_type=ModelTaskType.DIFF_ANALYSIS.value,
        prompt="diff --git a/file.py b/file.py",
        risk_score=0.2,
    )
    assert fast_decision.complexity == TaskComplexity.FAST
    assert "DeepSeek" in fast_decision.target_model

    # Incident / high-risk -> Nemotron on Nebius
    reasoning_decision = router.decide_route(
        task_type=ModelTaskType.INCIDENT_DIAGNOSIS.value,
        prompt="Stack trace: Null pointer exception during checkout",
        risk_score=0.85,
    )
    assert reasoning_decision.complexity == TaskComplexity.REASONING
    assert "nemotron" in reasoning_decision.target_model.lower()

    # Execute completion with mock token (deterministic fallback)
    res = await router.execute_completion(
        task_type=ModelTaskType.INCIDENT_DIAGNOSIS.value,
        messages=[{"role": "user", "content": "Analyze incident"}],
    )
    assert res["status"] == "success"
    assert "Nemotron" in res["content"] or "Nebius" in res["content"]


# =========================================================================
# API Endpoints Integration: Deployments, Monitoring, Incidents, Memory
# =========================================================================

def test_api_v1_deployments_endpoints(client: TestClient, setup_data):
    """Test REST API routes for deployments, logs, and rollback."""
    project = setup_data["project"]
    headers = setup_data["headers"]

    # 1. POST /api/v1/projects/{id}/deployments
    create_payload = {
        "provider": "render",
        "environment": "staging",
        "commit_sha": "api_test_commit_sha",
        "branch": "main",
    }
    res = client.post(f"/api/v1/projects/{project.id}/deployments", json=create_payload, headers=headers)
    assert res.status_code == 201, res.text
    dep_data = res.json()
    dep_id = dep_data["id"]
    assert dep_data["state"] == "SUCCESS"

    # 2. GET /api/v1/projects/{id}/deployments
    res = client.get(f"/api/v1/projects/{project.id}/deployments", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # 3. GET /api/v1/deployments/{id}
    res = client.get(f"/api/v1/deployments/{dep_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["id"] == dep_id

    # 4. GET /api/v1/deployments/{id}/logs
    res = client.get(f"/api/v1/deployments/{dep_id}/logs", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 5. POST /api/v1/deployments/{id}/rollback
    res = client.post(
        f"/api/v1/deployments/{dep_id}/rollback",
        json={"reason": "Testing API rollback"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["state"] == "ROLLED_BACK"


def test_api_v1_monitoring_endpoints(client: TestClient, setup_data):
    """Test REST API routes for synthetic health probes and health summaries."""
    project = setup_data["project"]
    headers = setup_data["headers"]

    # Trigger deployment first
    res = client.post(
        f"/api/v1/projects/{project.id}/deployments",
        json={"provider": "render", "environment": "staging", "commit_sha": "sha_mon_1"},
        headers=headers,
    )
    dep_id = res.json()["id"]

    # 1. POST /api/v1/deployments/{id}/probes
    res = client.post(f"/api/v1/deployments/{dep_id}/probes", json={"endpoint": "/health"}, headers=headers)
    assert res.status_code == 200
    probe_data = res.json()
    assert probe_data["deployment_id"] == dep_id

    # 2. GET /api/v1/deployments/{id}/probes
    res = client.get(f"/api/v1/deployments/{dep_id}/probes", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # 3. GET /api/v1/deployments/{id}/health
    res = client.get(f"/api/v1/deployments/{dep_id}/health", headers=headers)
    assert res.status_code == 200
    assert "average_latency_ms" in res.json()


def test_api_v1_incidents_endpoints(client: TestClient, setup_data):
    """Test REST API routes for incident creation, diagnosis, and resolution."""
    project = setup_data["project"]
    headers = setup_data["headers"]

    # 1. POST /api/v1/projects/{id}/incidents
    create_payload = {
        "title": "API 503 Spike on Production Gateway",
        "severity": "SEV1",
        "description": "Gateway returning 503 to 10% of users",
    }
    res = client.post(f"/api/v1/projects/{project.id}/incidents", json=create_payload, headers=headers)
    assert res.status_code == 201
    inc_data = res.json()
    inc_id = inc_data["id"]

    # 2. GET /api/v1/projects/{id}/incidents
    res = client.get(f"/api/v1/projects/{project.id}/incidents", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # 3. POST /api/v1/incidents/{id}/diagnose
    res = client.post(f"/api/v1/incidents/{inc_id}/diagnose", headers=headers)
    assert res.status_code == 200
    assert res.json()["recommended_action"] == "ROLLBACK"

    # 4. POST /api/v1/incidents/{id}/resolve
    res = client.post(
        f"/api/v1/incidents/{inc_id}/resolve",
        json={"root_cause_summary": "Resolved after rollback", "recommended_action": "ROLLBACK"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "RESOLVED"


def test_api_v1_memory_endpoints(client: TestClient, setup_data):
    """Test REST API routes for project persistent memory."""
    project = setup_data["project"]
    headers = setup_data["headers"]

    # 1. POST /api/v1/projects/{id}/memory
    payload = {
        "key": "circuit_breaker_threshold",
        "content": "Set circuit breaker timeout to 2500ms for external auth provider.",
        "category": "architectural_rule",
        "importance": 4,
    }
    res = client.post(f"/api/v1/projects/{project.id}/memory", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["key"] == "circuit_breaker_threshold"

    # 2. GET /api/v1/projects/{id}/memory
    res = client.get(f"/api/v1/projects/{project.id}/memory?q=circuit", headers=headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 1

    # 3. GET /api/v1/projects/{id}/memory/{key}
    res = client.get(f"/api/v1/projects/{project.id}/memory/circuit_breaker_threshold", headers=headers)
    assert res.status_code == 200
    assert res.json()["content"] == payload["content"]


# =========================================================================
# Platform Deployment Tools Wire-up
# =========================================================================

@pytest.mark.anyio
async def test_deployment_platform_tools_integrated_with_db(db: Session, setup_data):
    """Verify Platform ToolRegistry deployment tools execute against DB context."""
    project = setup_data["project"]
    context = {"db": db, "project_id": str(project.id)}

    deploy_tool = DeploymentDeploy()
    status_tool = DeploymentStatus()
    logs_tool = DeploymentLogs()
    rollback_tool = DeploymentRollback()

    # 1. Trigger deployment tool
    d_out = await deploy_tool.execute(
        {"environment": "staging", "version": "v1.0.0", "provider": "render"},
        context=context,
    )
    assert d_out["status"] == "SUCCESS"
    dep_id = d_out["deployment_id"]

    # 2. Status tool
    s_out = await status_tool.execute({"deployment_id": dep_id}, context=context)
    assert s_out["status"] == "SUCCESS"

    # 3. Logs tool
    l_out = await logs_tool.execute({"deployment_id": dep_id, "tail": 50}, context=context)
    assert "Logs" in l_out or len(l_out["logs"]) > 0

    # 4. Rollback tool
    r_out = await rollback_tool.execute({"deployment_id": dep_id, "reason": "Testing rollback"}, context=context)
    assert r_out["status"] == "ROLLED_BACK"
