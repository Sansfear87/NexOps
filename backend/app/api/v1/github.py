"""FastAPI route controllers for GitHub integration and webhook ingestion."""
from __future__ import annotations

import json
import logging
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.security import decrypt_token
from app.db.constants import ProjectRole
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.github import (
    ConnectRepoRequest,
    GitHubConnectionRead,
    PullRequestRead,
    PullRequestDiffResponse,
)
from app.services.github_service import GitHubService
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# GitHub Repository Management Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/projects/{project_id}/github/connect",
    response_model=GitHubConnectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Connect a GitHub repository to a project",
)
@router.post(
    "/{project_id}/connect",
    response_model=GitHubConnectionRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def connect_repository(
    project_id: uuid.UUID,
    payload: ConnectRepoRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Link a GitHub repository to the project and initialize pull request tracking."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.MAINTAINER)

    github_service = GitHubService(db)
    repo_name = payload.get_repo_name()
    connection = github_service.connect_repository(
        project_id=project_id,
        owner=payload.owner,
        repo_name=repo_name,
        token=payload.token,
        user_id=current_user.id,
        webhook_secret=payload.webhook_secret,
        default_branch=payload.default_branch or "main",
    )
    return GitHubConnectionRead.model_validate(connection)


@router.get(
    "/projects/{project_id}/github/connections",
    response_model=List[GitHubConnectionRead],
    summary="List GitHub connections for a project",
)
@router.get(
    "/{project_id}/connections",
    response_model=List[GitHubConnectionRead],
    include_in_schema=False,
)
def list_connections(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve all active GitHub connections for a given project."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    github_service = GitHubService(db)
    connections = github_service.connection_repo.get_by_project(project_id)
    return [GitHubConnectionRead.model_validate(c) for c in connections]


@router.get(
    "/projects/{project_id}/github/pulls",
    response_model=List[PullRequestRead],
    summary="List synchronized pull requests",
)
@router.get(
    "/{project_id}/pulls",
    response_model=List[PullRequestRead],
    include_in_schema=False,
)
def list_pull_requests(
    project_id: uuid.UUID,
    connection_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List pull requests for project GitHub connections."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    github_service = GitHubService(db)
    if connection_id:
        conn = github_service.connection_repo.get_by_id(connection_id)
        if not conn or conn.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found for this project.",
            )
        prs = github_service.list_pull_requests(connection_id)
    else:
        connections = github_service.connection_repo.get_by_project(project_id)
        prs = []
        for conn in connections:
            prs.extend(github_service.list_pull_requests(conn.id))

    return [PullRequestRead.model_validate(pr) for pr in prs]


@router.get(
    "/projects/{project_id}/github/pulls/{pull_number}",
    response_model=PullRequestRead,
    summary="Get pull request details",
)
@router.get(
    "/{project_id}/pulls/{pull_number}",
    response_model=PullRequestRead,
    include_in_schema=False,
)
def get_pull_request(
    project_id: uuid.UUID,
    pull_number: int,
    connection_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve details for a specific pull request number."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    github_service = GitHubService(db)
    target_conn = None
    if connection_id:
        target_conn = github_service.connection_repo.get_by_id(connection_id)
    else:
        connections = github_service.connection_repo.get_by_project(project_id)
        if connections:
            target_conn = connections[0]

    if not target_conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active GitHub connection found for this project.",
        )

    pr = github_service.get_pull_request(target_conn.id, pull_number)
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pull request #{pull_number} not found.",
        )
    return PullRequestRead.model_validate(pr)


@router.get(
    "/projects/{project_id}/github/pulls/{pull_number}/diff",
    response_model=PullRequestDiffResponse,
    summary="Get PR diff text and changed files",
)
@router.get(
    "/{project_id}/pulls/{pull_number}/diff",
    response_model=PullRequestDiffResponse,
    include_in_schema=False,
)
def get_pull_request_diff(
    project_id: uuid.UUID,
    pull_number: int,
    connection_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Fetch cached unified diff and changed files for a pull request."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    github_service = GitHubService(db)
    target_conn = None
    if connection_id:
        target_conn = github_service.connection_repo.get_by_id(connection_id)
    else:
        connections = github_service.connection_repo.get_by_project(project_id)
        if connections:
            target_conn = connections[0]

    if not target_conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active GitHub connection found for this project.",
        )

    diff_data = github_service.get_diff(target_conn.id, pull_number)
    return PullRequestDiffResponse(
        pull_number=diff_data["pull_number"],
        diff_text=diff_data["diff_text"],
        files_changed=diff_data["files_changed"],
    )


# ---------------------------------------------------------------------------
# GitHub Ingestion Webhook Endpoint (No User Auth, HMAC Verification)
# ---------------------------------------------------------------------------

@router.post(
    "/webhooks/github/{connection_id}",
    status_code=status.HTTP_200_OK,
    summary="GitHub Webhook ingestion handler",
)
async def github_webhook(
    connection_id: uuid.UUID,
    request: Request,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    db: Session = Depends(get_db),
):
    """Ingest GitHub webhook deliveries, verify HMAC SHA-256 signature, and dispatch events."""
    raw_body = await request.body()
    github_service = GitHubService(db)

    conn = github_service.connection_repo.get_by_id(connection_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target GitHub connection does not exist.",
        )

    # HMAC SHA256 Signature Verification
    if conn.webhook_secret_hash:
        secret = decrypt_token(conn.webhook_secret_hash)
        if not x_hub_signature_256 or not github_service.verify_webhook_signature(
            raw_body, x_hub_signature_256, secret
        ):
            logger.warning(
                "Webhook HMAC verification failed for connection %s", connection_id
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing webhook signature (X-Hub-Signature-256).",
            )

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {str(exc)}",
        )

    event_type = x_github_event or "ping"
    delivery_id = x_github_delivery or str(uuid.uuid4())

    webhook_event = github_service.process_webhook(
        connection_id=connection_id,
        event_type=event_type,
        delivery_id=delivery_id,
        payload=payload,
    )

    return {
        "status": "ok",
        "delivery_id": delivery_id,
        "processed": webhook_event.processed,
    }
