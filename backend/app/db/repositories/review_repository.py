"""Repository for Review and ReviewFinding entities."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.pull_request import PullRequest
from app.db.models.github_connection import GitHubConnection
from app.db.models.review import Review, ReviewFinding
from app.db.repositories.base import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    """Repository managing Review and ReviewFinding persistence."""

    def __init__(self, db: Session):
        super().__init__(Review, db)

    def get_with_findings(self, review_id: uuid.UUID) -> Optional[Review]:
        """Fetch review with preloaded findings by review ID."""
        stmt = select(Review).where(Review.id == review_id)
        return self.db.scalars(stmt).first()

    def list_by_pull_request(self, pull_request_id: uuid.UUID) -> List[Review]:
        """List all reviews generated for a given pull request, newest first."""
        stmt = (
            select(Review)
            .where(Review.pull_request_id == pull_request_id)
            .order_by(Review.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_latest_by_pull_request(self, pull_request_id: uuid.UUID) -> Optional[Review]:
        """Retrieve the latest review for a given pull request."""
        stmt = (
            select(Review)
            .where(Review.pull_request_id == pull_request_id)
            .order_by(Review.created_at.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def list_by_project(self, project_id: uuid.UUID, limit: int = 50) -> List[Review]:
        """List reviews for all pull requests belonging to a specific project."""
        stmt = (
            select(Review)
            .join(PullRequest, Review.pull_request_id == PullRequest.id)
            .join(GitHubConnection, PullRequest.github_connection_id == GitHubConnection.id)
            .where(GitHubConnection.project_id == project_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def create_review_with_findings(
        self,
        review: Review,
        findings: List[ReviewFinding],
    ) -> Review:
        """Atomically persist a review and its collection of findings."""
        self.db.add(review)
        self.db.flush()  # assign review.id

        for finding in findings:
            finding.review_id = review.id
            self.db.add(finding)

        self.db.commit()
        self.db.refresh(review)
        return review
