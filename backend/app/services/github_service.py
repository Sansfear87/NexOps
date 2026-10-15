"""GitHub API and Webhook Processing Service."""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import encrypt_token, decrypt_token
from app.db.constants import PRState, WebhookEventType, EventType, ActorType
from app.db.models.github_connection import GitHubConnection
from app.db.models.pull_request import PullRequest
from app.db.models.webhook_event import WebhookEvent
from app.db.repositories.github_connection_repository import GitHubConnectionRepository
from app.db.repositories.pull_request_repository import PullRequestRepository
from app.db.repositories.webhook_event_repository import WebhookEventRepository
from app.services.event_bus import EventBus

logger = logging.getLogger(__name__)


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 datetime string from GitHub into datetime object."""
    if not dt_str:
        return None
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except Exception:
        return datetime.now(timezone.utc)


class GitHubService:
    """Service orchestrating GitHub connection, pull request sync, diff caching, and webhook processing."""

    def __init__(self, db: Session):
        self.db = db
        self.connection_repo = GitHubConnectionRepository(db)
        self.pr_repo = PullRequestRepository(db)
        self.webhook_repo = WebhookEventRepository(db)
        self.event_bus = EventBus(db)

    def _get_auth_headers(self, token: Optional[str]) -> Dict[str, str]:
        """Construct standard GitHub API headers with authorization."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "NexOps-DevOps-Assistant",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def connect_repository(
        self,
        project_id: uuid.UUID,
        owner: str,
        repo_name: str,
        token: str,
        user_id: uuid.UUID,
        webhook_secret: Optional[str] = None,
        default_branch: str = "main",
    ) -> GitHubConnection:
        """Validate, encrypt credentials, link repository to project, and sync open pull requests.

        Args:
            project_id: Target project UUID.
            owner: Repository owner/org.
            repo_name: Repository name.
            token: GitHub Personal Access Token.
            user_id: Performing user UUID.
            webhook_secret: Optional shared secret for HMAC verification.
            default_branch: Default repo branch name.

        Returns:
            Created or updated GitHubConnection instance.
        """
        owner_clean = owner.strip()
        repo_clean = repo_name.strip()
        headers = self._get_auth_headers(token)

        # 1. Validate repository access with GitHub API
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.get(
                    f"https://api.github.com/repos/{owner_clean}/{repo_clean}",
                    headers=headers,
                )
                if res.status_code == 401:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid GitHub Personal Access Token.",
                    )
                if res.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"GitHub repository '{owner_clean}/{repo_clean}' not found or inaccessible.",
                    )
                res.raise_for_status()
                repo_data = res.json()
                detected_branch = repo_data.get("default_branch") or default_branch
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("GitHub repository validation failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to communicate with GitHub API: {str(exc)}",
            )

        # 2. Encrypt token and secret
        encrypted_token = encrypt_token(token)
        webhook_encrypted = encrypt_token(webhook_secret) if webhook_secret else None

        # 3. Upsert connection record
        existing = self.connection_repo.get_by_project_and_repo(
            project_id, owner_clean, repo_clean
        )
        if existing:
            existing.personal_access_token_hash = encrypted_token
            existing.default_branch = detected_branch
            existing.webhook_secret_hash = webhook_encrypted
            existing.is_active = True
            connection = self.connection_repo.update(existing)
        else:
            connection = GitHubConnection(
                project_id=project_id,
                owner=owner_clean,
                repo_name=repo_clean,
                personal_access_token_hash=encrypted_token,
                default_branch=detected_branch,
                webhook_secret_hash=webhook_encrypted,
                is_active=True,
            )
            connection = self.connection_repo.create(connection)


        # 4. Fetch open pull requests and seed records & events
        try:
            with httpx.Client(timeout=20.0) as client:
                pulls_res = client.get(
                    f"https://api.github.com/repos/{owner_clean}/{repo_clean}/pulls",
                    params={"state": "open", "per_page": 20},
                    headers=headers,
                )
                if pulls_res.is_success:
                    pulls = pulls_res.json()
                    for pr_data in pulls:
                        pr_num = pr_data["number"]
                        pr_record = self._save_pr_data(connection.id, pr_data)
                        # Emit PR_OPENED event
                        self.event_bus.emit(
                            event_type=EventType.PR_OPENED,
                            project_id=project_id,
                            actor_id=str(user_id),
                            actor_type=ActorType.USER,
                            payload={
                                "pull_number": pr_num,
                                "title": pr_record.title,
                                "author": pr_record.author,
                                "base_ref": pr_record.base_branch,
                                "head_ref": pr_record.head_branch,
                                "head_sha": pr_record.head_sha,
                            },
                        )
        except Exception as exc:
            logger.warning("Could not pre-fetch open PRs during repo connect: %s", exc)

        return connection

    def _get_connection_and_token(
        self, connection_id: uuid.UUID
    ) -> tuple[GitHubConnection, str]:
        """Fetch connection and decrypt its access token."""
        conn = self.connection_repo.get_by_id(connection_id)
        if not conn or not conn.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GitHub connection not found or inactive.",
            )
        token = decrypt_token(conn.personal_access_token_hash or "")
        return conn, token

    def _save_pr_data(
        self, connection_id: uuid.UUID, pr_data: Dict[str, Any]
    ) -> PullRequest:
        """Parse raw GitHub PR JSON and upsert into database."""
        pr_number = pr_data["number"]
        state_raw = (pr_data.get("state") or "open").upper()
        if pr_data.get("merged"):
            state = PRState.MERGED.value
        elif state_raw == "CLOSED":
            state = PRState.CLOSED.value
        else:
            state = PRState.OPEN.value

        data = {
            "title": pr_data.get("title", ""),
            "state": state,
            "author": pr_data.get("user", {}).get("login", "unknown"),
            "head_branch": pr_data.get("head", {}).get("ref", "unknown"),
            "base_branch": pr_data.get("base", {}).get("ref", "main"),
            "head_sha": pr_data.get("head", {}).get("sha", ""),
            "body": pr_data.get("body"),
            "additions": pr_data.get("additions", 0),
            "deletions": pr_data.get("deletions", 0),
            "changed_files": pr_data.get("changed_files", 0),
            "github_created_at": parse_iso_datetime(pr_data.get("created_at")),
            "github_updated_at": parse_iso_datetime(pr_data.get("updated_at")),
        }
        return self.pr_repo.upsert(connection_id, pr_number, data)

    def sync_pull_request(
        self, connection_id: uuid.UUID, pull_number: int
    ) -> PullRequest:
        """Fetch pull request from GitHub API and upsert record into database."""
        conn, token = self._get_connection_and_token(connection_id)
        headers = self._get_auth_headers(token)

        try:
            with httpx.Client(timeout=20.0) as client:
                res = client.get(
                    f"https://api.github.com/repos/{conn.owner}/{conn.repo_name}/pulls/{pull_number}",
                    headers=headers,
                )
                if res.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"PR #{pull_number} not found on GitHub.",
                    )
                res.raise_for_status()
                pr_data = res.json()
                return self._save_pr_data(conn.id, pr_data)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Failed to sync PR #%d: %s", pull_number, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API error syncing PR: {str(exc)}",
            )

    def get_pull_request(
        self, connection_id: uuid.UUID, pull_number: int
    ) -> Optional[PullRequest]:
        """Fetch pull request from database, or sync if not yet recorded."""
        pr = self.pr_repo.get_by_connection_and_number(connection_id, pull_number)
        if not pr:
            try:
                pr = self.sync_pull_request(connection_id, pull_number)
            except Exception:
                return None
        return pr

    def get_diff(
        self, connection_id: uuid.UUID, pull_number: int
    ) -> Dict[str, Any]:
        """Fetch unified diff and changed files list from GitHub, caching diff text."""
        conn, token = self._get_connection_and_token(connection_id)
        api_headers = self._get_auth_headers(token)
        diff_headers = self._get_auth_headers(token)
        diff_headers["Accept"] = "application/vnd.github.v3.diff"

        try:
            with httpx.Client(timeout=30.0) as client:
                # 1. Fetch raw unified diff
                diff_res = client.get(
                    f"https://api.github.com/repos/{conn.owner}/{conn.repo_name}/pulls/{pull_number}",
                    headers=diff_headers,
                )
                diff_res.raise_for_status()
                diff_text = diff_res.text

                # 2. Fetch changed files detail
                files_res = client.get(
                    f"https://api.github.com/repos/{conn.owner}/{conn.repo_name}/pulls/{pull_number}/files",
                    headers=api_headers,
                )
                files_res.raise_for_status()
                files_data = files_res.json()

                files_changed = [
                    {
                        "filename": f.get("filename"),
                        "status": f.get("status"),
                        "additions": f.get("additions", 0),
                        "deletions": f.get("deletions", 0),
                        "patch": f.get("patch", ""),
                    }
                    for f in files_data
                ]

                # Cache diff in PR record
                pr = self.pr_repo.get_by_connection_and_number(conn.id, pull_number)
                if pr:
                    pr.diff_text = diff_text
                    self.pr_repo.update(pr)

                return {
                    "pull_number": pull_number,
                    "diff_text": diff_text,
                    "files_changed": files_changed,
                }
        except Exception as exc:
            logger.exception("Failed to fetch diff for PR #%d: %s", pull_number, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API error fetching PR diff: {str(exc)}",
            )

    def list_pull_requests(
        self, connection_id: uuid.UUID
    ) -> List[PullRequest]:
        """List all pull requests synchronized for a connection."""
        return self.pr_repo.list_by_connection(connection_id)

    def verify_webhook_signature(
        self, payload_body: bytes, signature: str, secret: str
    ) -> bool:
        """Verify HMAC-SHA256 signature from GitHub webhook header X-Hub-Signature-256."""
        if not signature or not secret:
            return False
        computed = hmac.new(
            secret.encode("utf-8"), payload_body, hashlib.sha256
        ).hexdigest()
        expected = f"sha256={computed}"
        return hmac.compare_digest(expected, signature)

    def process_webhook(
        self,
        connection_id: uuid.UUID,
        event_type: str,
        delivery_id: str,
        payload: Dict[str, Any],
    ) -> WebhookEvent:
        """Log incoming webhook payload, handle idempotency, and dispatch platform events."""
        conn = self.connection_repo.get_by_id(connection_id)
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target GitHub connection does not exist.",
            )

        # Idempotency check
        existing = self.webhook_repo.get_by_delivery_id(delivery_id)
        if existing:
            logger.info("Skipping duplicate webhook delivery: %s", delivery_id)
            return existing

        # Log raw webhook record
        webhook_record = WebhookEvent(
            github_connection_id=connection_id,
            event_type=event_type,
            delivery_id=delivery_id,
            payload=payload,
            processed=False,
        )
        webhook_record = self.webhook_repo.create(webhook_record)

        error_message = None
        try:
            action = payload.get("action")
            if event_type == "pull_request":
                pr_data = payload.get("pull_request", {})
                pr_number = pr_data.get("number")
                if pr_number:
                    pr_record = self._save_pr_data(conn.id, pr_data)

                    if action == "opened":
                        self.event_bus.emit(
                            event_type=EventType.PR_OPENED,
                            project_id=conn.project_id,
                            actor_id=pr_record.author,
                            actor_type=ActorType.WEBHOOK,
                            payload={
                                "pull_number": pr_number,
                                "title": pr_record.title,
                                "author": pr_record.author,
                                "base_ref": pr_record.base_branch,
                                "head_ref": pr_record.head_branch,
                                "head_sha": pr_record.head_sha,
                            },
                        )
                    elif action == "synchronize":
                        self.event_bus.emit(
                            event_type=EventType.PR_UPDATED,
                            project_id=conn.project_id,
                            actor_id=pr_record.author,
                            actor_type=ActorType.WEBHOOK,
                            payload={
                                "pull_number": pr_number,
                                "previous_head_sha": payload.get("before", ""),
                                "new_head_sha": pr_record.head_sha,
                            },
                        )
                    elif action == "closed":
                        # Record merged or closed state
                        logger.info("PR #%d closed (merged=%s)", pr_number, pr_data.get("merged"))
            elif event_type == "push":
                # Push event to branch
                ref = payload.get("ref", "")
                head_commit = payload.get("head_commit", {})
                logger.info("Push event received on ref %s (%s)", ref, head_commit.get("id"))
        except Exception as exc:
            logger.exception("Failed processing webhook %s: %s", delivery_id, exc)
            error_message = str(exc)

        self.webhook_repo.mark_processed(webhook_record.id, error_message=error_message)
        return webhook_record
