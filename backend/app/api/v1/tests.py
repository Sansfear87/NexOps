"""FastAPI route controllers for test execution and reporting."""
from __future__ import annotations

import logging
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.constants import ProjectRole, TestCaseStatus, TestStatus
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.test_run import (
    TestCaseResultResponse,
    TestRunCreateRequest,
    TestRunResponse,
)
from app.services.project_service import ProjectService
from app.services.test_service import TestService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/projects/{project_id}/tests/run",
    response_model=TestRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger automated test suite execution",
)
def trigger_test_run(
    project_id: uuid.UUID,
    payload: Optional[TestRunCreateRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Execute tests against a commit or PR, record results, and emit lifecycle events."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.DEVELOPER)

    commit_sha = payload.commit_sha if payload else None
    suite_name = payload.suite_name if payload else "unit"
    pull_number = payload.pull_number if payload else None

    test_service = TestService(db)
    return test_service.run_tests(
        project_id=project_id,
        commit_sha=commit_sha,
        suite_name=suite_name,
        pull_number=pull_number,
        user_id=current_user.id,
    )


@router.get(
    "/projects/{project_id}/tests/runs",
    response_model=List[TestRunResponse],
    summary="List past test suite executions for a project",
)
def list_test_runs(
    project_id: uuid.UUID,
    pull_number: Optional[int] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve historical test runs for a project or specific pull request."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    test_service = TestService(db)
    if pull_number:
        connections = test_service.connection_repo.get_by_project(project_id)
        if connections:
            pr = test_service.pr_repo.get_by_connection_and_number(connections[0].id, pull_number)
            if pr:
                runs = test_service.test_repo.list_by_pull_request(pr.id)
            else:
                runs = []
        else:
            runs = []
    else:
        runs = test_service.test_repo.list_by_project(project_id, limit=limit)

    return [
        TestRunResponse(
            id=t.id,
            project_id=t.project_id,
            pull_request_id=t.pull_request_id,
            agent_run_id=t.agent_run_id,
            commit_sha=t.commit_sha,
            suite_name=t.suite_name,
            status=TestStatus(t.status),
            passed=t.passed,
            total_tests=t.total_tests,
            failed_tests=t.failed_tests,
            duration_seconds=t.duration_seconds,
            summary_output=t.summary_output,
            started_at=t.started_at,
            completed_at=t.completed_at,
            created_at=t.created_at,
            updated_at=t.updated_at,
            results=[
                TestCaseResultResponse(
                    id=r.id,
                    test_run_id=r.test_run_id,
                    test_case_name=r.test_case_name,
                    status=TestCaseStatus(r.status),
                    duration_ms=r.duration_ms,
                    error_message=r.error_message,
                    created_at=r.created_at,
                )
                for r in t.results
            ],
        )
        for t in runs
    ]


@router.get(
    "/projects/{project_id}/tests/runs/{run_id}",
    response_model=TestRunResponse,
    summary="Get details and test case results for a test run",
)
def get_test_run(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve full test case breakdown for an execution."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    test_service = TestService(db)
    test_run = test_service.test_repo.get_with_results(run_id)
    if not test_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test run not found.",
        )

    return TestRunResponse(
        id=test_run.id,
        project_id=test_run.project_id,
        pull_request_id=test_run.pull_request_id,
        agent_run_id=test_run.agent_run_id,
        commit_sha=test_run.commit_sha,
        suite_name=test_run.suite_name,
        status=TestStatus(test_run.status),
        passed=test_run.passed,
        total_tests=test_run.total_tests,
        failed_tests=test_run.failed_tests,
        duration_seconds=test_run.duration_seconds,
        summary_output=test_run.summary_output,
        started_at=test_run.started_at,
        completed_at=test_run.completed_at,
        created_at=test_run.created_at,
        updated_at=test_run.updated_at,
        results=[
            TestCaseResultResponse(
                id=r.id,
                test_run_id=r.test_run_id,
                test_case_name=r.test_case_name,
                status=TestCaseStatus(r.status),
                duration_ms=r.duration_ms,
                error_message=r.error_message,
                created_at=r.created_at,
            )
            for r in test_run.results
        ],
    )
