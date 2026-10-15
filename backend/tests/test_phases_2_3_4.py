"""Comprehensive test suite for Phase 2 (GitHub Integration), Phase 3 (Context Engine), and Phase 4 (Tool Execution)."""
import asyncio
import hashlib
import hmac
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.constants import (
    PRState,
    WebhookEventType,
    EventType,
    ActorType,
)
from app.db.models.user import User
from app.db.models.project import Project
from app.db.models.github_connection import GitHubConnection
from app.db.models.pull_request import PullRequest
from app.db.models.webhook_event import WebhookEvent
from app.db.models.platform_event import PlatformEvent

from app.db.repositories.github_connection_repository import GitHubConnectionRepository
from app.db.repositories.pull_request_repository import PullRequestRepository
from app.db.repositories.webhook_event_repository import WebhookEventRepository
from app.db.repositories.platform_event_repository import PlatformEventRepository

from app.services.event_bus import EventBus
from app.services.github_service import GitHubService
from app.services.diff_parser import DiffParser, FileDiff
from app.services.context_engine import ContextEngine
from app.services.tool_execution_service import ToolExecutionService
from app.core.security import encrypt_token, decrypt_token
from app.main import app


@pytest.fixture
def db_session():
    """In-memory SQLite synchronous session fixture."""
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(test_engine)
    TestingSessionLocal = sessionmaker(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_test_project_and_user(db):
    user = User(
        email="devops@nexops.io",
        display_name="DevOps Lead",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    project = Project(
        name="NexOps Test App",
        slug="nexops-test-app",
        owner_id=user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return user, project


# ===========================================================================
# Phase 2 Tests: Constants, Models, Repositories, EventBus, GitHubService
# ===========================================================================

def test_constants_enums():
    assert PRState.OPEN.value == "OPEN"
    assert PRState.CLOSED.value == "CLOSED"
    assert PRState.MERGED.value == "MERGED"

    assert WebhookEventType.PR_OPENED.value == "PR_OPENED"
    assert WebhookEventType.PUSH.value == "PUSH"

    assert EventType.REVIEW_STARTED.value == "REVIEW_STARTED"
    assert EventType.REVIEW_COMPLETED.value == "REVIEW_COMPLETED"
    assert EventType.DEPLOYMENT_STARTED.value == "DEPLOYMENT_STARTED"
    assert EventType.RECOVERY_COMPLETED.value == "RECOVERY_COMPLETED"


def test_token_encryption_decryption():
    raw_token = "ghp_secure_github_pat_token_12345"
    encrypted = encrypt_token(raw_token)
    assert encrypted != raw_token
    decrypted = decrypt_token(encrypted)
    assert decrypted == raw_token


def test_github_connection_and_pull_request_repo(db_session):
    user, project = create_test_project_and_user(db_session)
    conn_repo = GitHubConnectionRepository(db_session)
    pr_repo = PullRequestRepository(db_session)

    # 1. Create connection
    conn = GitHubConnection(
        project_id=project.id,
        owner="nexops-org",
        repo_name="core-service",
        default_branch="main",
        personal_access_token_hash=encrypt_token("ghp_test"),
        is_active=True,
    )
    created_conn = conn_repo.create(conn)
    assert created_conn.id is not None
    assert created_conn.owner == "nexops-org"

    # Query by project
    conns = conn_repo.get_by_project(project.id)
    assert len(conns) == 1

    # Query by project and repo
    conn_found = conn_repo.get_by_project_and_repo(project.id, "nexops-org", "core-service")
    assert conn_found is not None
    assert conn_found.id == created_conn.id

    # 2. Upsert PR
    pr = pr_repo.upsert(
        github_connection_id=created_conn.id,
        pull_number=42,
        data_dict={
            "title": "Add Kubernetes readiness probes",
            "state": PRState.OPEN.value,
            "author": "octocat",
            "head_branch": "feature/probes",
            "base_branch": "main",
            "head_sha": "abc123def456",
            "body": "Implements automated liveness/readiness probes.",
            "additions": 35,
            "deletions": 5,
            "changed_files": 2,
        },
    )
    assert pr.id is not None
    assert pr.pull_number == 42
    assert pr.additions == 35

    # Update PR via upsert
    updated_pr = pr_repo.upsert(
        github_connection_id=created_conn.id,
        pull_number=42,
        data_dict={"title": "Updated probe implementation", "additions": 40},
    )
    assert updated_pr.id == pr.id
    assert updated_pr.title == "Updated probe implementation"
    assert updated_pr.additions == 40


def test_webhook_event_repository(db_session):
    user, project = create_test_project_and_user(db_session)
    conn_repo = GitHubConnectionRepository(db_session)
    webhook_repo = WebhookEventRepository(db_session)

    conn = conn_repo.create(
        GitHubConnection(
            project_id=project.id,
            owner="nexops-org",
            repo_name="infra",
            personal_access_token_hash=encrypt_token("ghp_123"),
        )
    )

    delivery_id = str(uuid.uuid4())
    event = WebhookEvent(
        github_connection_id=conn.id,
        event_type="pull_request",
        delivery_id=delivery_id,
        payload={"action": "opened", "number": 10},
        processed=False,
    )
    saved = webhook_repo.create(event)
    assert saved.id is not None
    assert saved.delivery_id == delivery_id

    # Idempotency lookup
    duplicate = webhook_repo.get_by_delivery_id(delivery_id)
    assert duplicate is not None

    # Mark processed
    webhook_repo.mark_processed(saved.id)
    db_session.refresh(saved)
    assert saved.processed is True


def test_event_bus_and_platform_event_repo(db_session):
    user, project = create_test_project_and_user(db_session)
    event_bus = EventBus(db_session)

    received_events = []

    def on_pr_opened(ev):
        received_events.append(ev)

    EventBus.subscribe(EventType.PR_OPENED, on_pr_opened)

    trace_id = uuid.uuid4()
    emitted = event_bus.emit(
        event_type=EventType.PR_OPENED,
        project_id=project.id,
        actor_id=str(user.id),
        actor_type=ActorType.USER,
        payload={"pull_number": 101, "title": "New feature"},
        trace_id=trace_id,
    )

    assert emitted.id is not None
    assert emitted.trace_id == trace_id
    assert len(received_events) >= 1
    assert received_events[-1].id == emitted.id

    recent = event_bus.get_events(project.id)
    assert len(recent) >= 1
    assert recent[0].id == emitted.id


def test_github_service_webhook_hmac_and_process(db_session):
    user, project = create_test_project_and_user(db_session)
    conn_repo = GitHubConnectionRepository(db_session)
    github_service = GitHubService(db_session)

    secret = "super-secret-webhook-key-999"
    conn = conn_repo.create(
        GitHubConnection(
            project_id=project.id,
            owner="nexops-org",
            repo_name="demo-repo",
            personal_access_token_hash=encrypt_token("ghp_test"),
            webhook_secret_hash=encrypt_token(secret),
        )
    )

    body = b'{"action": "opened", "pull_request": {"number": 5, "title": "Add CI", "head": {"ref": "ci", "sha": "111"}, "base": {"ref": "main"}, "user": {"login": "alice"}}}'
    computed_hmac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    valid_sig = f"sha256={computed_hmac}"

    # HMAC verification
    assert github_service.verify_webhook_signature(body, valid_sig, secret) is True
    assert github_service.verify_webhook_signature(body, "sha256=invalid", secret) is False

    # Process webhook delivery
    delivery_id = str(uuid.uuid4())
    webhook_ev = github_service.process_webhook(
        connection_id=conn.id,
        event_type="pull_request",
        delivery_id=delivery_id,
        payload={
            "action": "opened",
            "pull_request": {
                "number": 5,
                "title": "Add CI",
                "head": {"ref": "ci", "sha": "111"},
                "base": {"ref": "main"},
                "user": {"login": "alice"},
            },
        },
    )
    assert webhook_ev.processed is True


# ===========================================================================
# Phase 3 Tests: Diff Parser & Context Engine
# ===========================================================================

SAMPLE_DIFF = """diff --git a/app/routes.py b/app/routes.py
index 1234567..89abcdef 100644
--- a/app/routes.py
+++ b/app/routes.py
@@ -15,4 +15,9 @@ def existing_handler():
     return {"status": "ok"}
 
+def calculate_metrics(data):
+    \"\"\"Compute latency statistics.\"\"\"
+    total = sum(data)
+    return total / len(data) if data else 0
+
"""


def test_diff_parser():
    parser = DiffParser()
    file_diffs = parser.parse_unified_diff(SAMPLE_DIFF)
    assert len(file_diffs) == 1

    fd = file_diffs[0]
    assert fd.filename == "app/routes.py"
    assert fd.status == "modified"
    assert fd.language == "python"
    assert fd.additions > 0
    assert len(fd.hunks) == 1

    changed_funcs = parser.get_changed_functions(fd)
    assert "calculate_metrics" in changed_funcs

    summary = parser.summarize(file_diffs)
    assert "routes.py" in summary
    assert "calculate_metrics" in summary


def test_context_engine(db_session):
    user, project = create_test_project_and_user(db_session)
    conn_repo = GitHubConnectionRepository(db_session)
    pr_repo = PullRequestRepository(db_session)

    conn = conn_repo.create(
        GitHubConnection(
            project_id=project.id,
            owner="nexops-org",
            repo_name="backend-api",
            default_branch="main",
            personal_access_token_hash=encrypt_token("ghp_test"),
        )
    )

    pr = pr_repo.upsert(
        github_connection_id=conn.id,
        pull_number=1,
        data_dict={
            "title": "Feature: Add Redis caching",
            "state": PRState.OPEN.value,
            "author": "bob",
            "head_branch": "feature/redis",
            "base_branch": "main",
            "head_sha": "def456",
            "diff_text": SAMPLE_DIFF,
            "additions": 6,
            "deletions": 0,
            "changed_files": 1,
        },
    )

    context_engine = ContextEngine(db_session)
    pr_context = context_engine.build_pr_review_context(project.id, 1)

    assert pr_context["context_type"] == "pr_review"
    assert pr_context["pull_request"]["title"] == "Feature: Add Redis caching"
    assert "routes.py" in pr_context["diff_summary"]
    assert len(pr_context["changed_files"]) == 1

    deploy_context = context_engine.build_deployment_context(project.id, "staging")
    assert deploy_context["context_type"] == "deployment"
    assert deploy_context["target_environment"] == "staging"

    incident_context = context_engine.build_incident_context(project.id, "deploy-123")
    assert incident_context["context_type"] == "incident_diagnosis"
    assert incident_context["deployment_id"] == "deploy-123"


# ===========================================================================
# Phase 4 Tests: Tool Execution Service & Router Wiring
# ===========================================================================

def test_tool_execution_service_registry(db_session):
    tool_service = ToolExecutionService(db_session)
    tools = tool_service.list_available_tools()
    tool_names = [t["name"] for t in tools]

    assert "github.get_repository" in tool_names
    assert "github.get_pull_request" in tool_names
    assert "github.get_diff" in tool_names
    assert "deployment.deploy" in tool_names


def test_tool_executor_callback(db_session):
    import asyncio
    tool_service = ToolExecutionService(db_session)
    executor = tool_service.get_tool_executor(
        permissions=["repo:read"],
        context={"owner": "octocat", "repo": "Hello-World"},
    )

    async def _run():
        # Permission check failure for unpermitted tool
        with pytest.raises(RuntimeError) as exc_info:
            await executor("deployment.deploy", {"environment": "production", "version": "v1.0"})
        assert "Missing required permission" in str(exc_info.value)

    asyncio.run(_run())


def test_fastapi_router_wiring():
    routes = [route.path for route in app.routes]
    assert "/health" in routes
    assert "/api/v1/projects" in routes
    assert "/api/v1/projects/{project_id}/github/connect" in routes
    assert "/api/v1/projects/{project_id}/github/connections" in routes
    assert "/api/v1/projects/{project_id}/github/pulls" in routes
    assert "/api/v1/projects/{project_id}/events" in routes
    assert "/api/v1/projects/{project_id}/events/stream" in routes
    assert "/api/v1/projects/{project_id}/agent/run" in routes
    assert "/api/v1/webhooks/github/{connection_id}" in routes
