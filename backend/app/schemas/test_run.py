"""Pydantic schemas for test execution and reporting."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.db.constants import TestCaseStatus, TestStatus


class TestCaseResultResponse(BaseModel):
    """API response model for an individual test case result."""
    id: uuid.UUID
    test_run_id: uuid.UUID
    test_case_name: str
    status: TestCaseStatus
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestRunCreateRequest(BaseModel):
    """Request payload to initiate a test run."""
    commit_sha: Optional[str] = Field(default=None, description="Target Git commit SHA (defaults to HEAD of default branch)")
    suite_name: str = Field(default="unit", description="Test suite identifier (e.g. unit, integration)")
    pull_number: Optional[int] = Field(default=None, description="Optional pull request number to associate with")


class TestRunResponse(BaseModel):
    """API response model for a full test run."""
    id: uuid.UUID
    project_id: uuid.UUID
    pull_request_id: Optional[uuid.UUID] = None
    agent_run_id: Optional[uuid.UUID] = None
    commit_sha: str
    suite_name: str
    status: TestStatus
    passed: bool
    total_tests: int
    failed_tests: int
    duration_seconds: float
    summary_output: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    results: List[TestCaseResultResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
