"""Repository for GitHubConnection entity."""
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models.github_connection import GitHubConnection
from app.db.repositories.base import BaseRepository


class GitHubConnectionRepository(BaseRepository[GitHubConnection]):
    """Repository managing GitHubConnection persistence operations."""

    def __init__(self, db: Session):
        super().__init__(GitHubConnection, db)

    def get_by_project(self, project_id: uuid.UUID) -> List[GitHubConnection]:
        """Fetch all active GitHub connections for a project."""
        stmt = (
            select(GitHubConnection)
            .where(
                GitHubConnection.project_id == project_id,
                GitHubConnection.is_active.is_(True),
            )
            .order_by(GitHubConnection.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_project_and_repo(
        self, project_id: uuid.UUID, owner: str, repo_name: str
    ) -> Optional[GitHubConnection]:
        """Fetch a specific connection by project, owner, and repository name."""
        stmt = select(GitHubConnection).where(
            GitHubConnection.project_id == project_id,
            GitHubConnection.owner == owner.strip(),
            GitHubConnection.repo_name == repo_name.strip(),
        )
        return self.db.scalars(stmt).first()
