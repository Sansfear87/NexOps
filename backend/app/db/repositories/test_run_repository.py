"""Repository for TestRun and TestResult entities."""
from __future__ import annotations

from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.test_run import TestRun, TestResult
from app.db.repositories.base import BaseRepository


class TestRunRepository(BaseRepository[TestRun]):
    """Repository managing TestRun and TestResult persistence."""

    __test__ = False

    def __init__(self, db: Session):
        super().__init__(TestRun, db)

    def get_with_results(self, test_run_id: uuid.UUID) -> Optional[TestRun]:
        """Fetch test run with preloaded case results by ID."""
        stmt = select(TestRun).where(TestRun.id == test_run_id)
        return self.db.scalars(stmt).first()

    def list_by_project(self, project_id: uuid.UUID, limit: int = 50) -> List[TestRun]:
        """List test runs for a given project, newest first."""
        stmt = (
            select(TestRun)
            .where(TestRun.project_id == project_id)
            .order_by(TestRun.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_by_pull_request(self, pull_request_id: uuid.UUID) -> List[TestRun]:
        """List test runs associated with a specific pull request."""
        stmt = (
            select(TestRun)
            .where(TestRun.pull_request_id == pull_request_id)
            .order_by(TestRun.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_latest_by_pull_request(self, pull_request_id: uuid.UUID) -> Optional[TestRun]:
        """Fetch the most recent test run for a pull request."""
        stmt = (
            select(TestRun)
            .where(TestRun.pull_request_id == pull_request_id)
            .order_by(TestRun.created_at.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def create_test_run_with_results(
        self,
        test_run: TestRun,
        results: List[TestResult],
    ) -> TestRun:
        """Atomically persist a test run and its individual test case results."""
        self.db.add(test_run)
        self.db.flush()

        for result in results:
            result.test_run_id = test_run.id
            self.db.add(result)

        self.db.commit()
        self.db.refresh(test_run)
        return test_run
