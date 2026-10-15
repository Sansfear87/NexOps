"""Repository for PullRequest entity."""
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models.pull_request import PullRequest
from app.db.repositories.base import BaseRepository


class PullRequestRepository(BaseRepository[PullRequest]):
    """Repository managing PullRequest persistence operations."""

    def __init__(self, db: Session):
        super().__init__(PullRequest, db)

    def get_by_connection_and_number(
        self, github_connection_id: uuid.UUID, pull_number: int
    ) -> Optional[PullRequest]:
        """Retrieve pull request record by connection ID and PR number."""
        stmt = select(PullRequest).where(
            PullRequest.github_connection_id == github_connection_id,
            PullRequest.pull_number == pull_number,
        )
        return self.db.scalars(stmt).first()

    def list_by_connection(
        self, github_connection_id: uuid.UUID
    ) -> List[PullRequest]:
        """List all pull requests synchronized for a GitHub connection."""
        stmt = (
            select(PullRequest)
            .where(PullRequest.github_connection_id == github_connection_id)
            .order_by(PullRequest.pull_number.desc())
        )
        return list(self.db.scalars(stmt).all())

    def upsert(
        self, github_connection_id: uuid.UUID, pull_number: int, data_dict: Dict[str, Any]
    ) -> PullRequest:
        """Create or update a pull request record."""
        existing = self.get_by_connection_and_number(github_connection_id, pull_number)
        if existing:
            for key, val in data_dict.items():
                if hasattr(existing, key):
                    setattr(existing, key, val)
            return self.update(existing)

        new_pr = PullRequest(
            github_connection_id=github_connection_id,
            pull_number=pull_number,
            **data_dict,
        )
        return self.create(new_pr)
