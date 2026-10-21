"""Pydantic schemas conforming to contracts/review_contract.md."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.db.constants import (
    FindingCategory,
    FindingSeverity,
    ReviewRisk,
    ReviewStatus,
    ReviewVerdict,
)


class ReviewFindingSchema(BaseModel):
    """Granular code finding anchored to a specific file and line."""
    finding_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for finding")
    file: str = Field(..., description="Relative file path within repository")
    line: int = Field(..., ge=1, description="Target line number (1-indexed)")
    end_line: Optional[int] = Field(None, ge=1, description="Optional ending line for multi-line finding")
    category: FindingCategory = Field(..., description="Finding category taxonomy")
    severity: FindingSeverity = Field(..., description="Impact severity")
    description: str = Field(..., description="Detailed explanation of the issue")
    recommendation: str = Field(..., description="Actionable instructions to resolve")
    suggested_diff: Optional[str] = Field(None, description="Unified diff patch proposing the fix")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level (0.0 - 1.0)")

    model_config = ConfigDict(from_attributes=True)


class ReviewMetadataSchema(BaseModel):
    """Metadata regarding review execution metrics and model details."""
    files_analyzed_count: int = Field(default=0)
    lines_added_count: int = Field(default=0)
    lines_deleted_count: int = Field(default=0)
    duration_ms: int = Field(default=0)
    model_used: str = Field(default="deepseek-coder")

    model_config = ConfigDict(from_attributes=True)


class ReviewResultSchema(BaseModel):
    """Structured AI review result conforming 1:1 to contracts/review_contract.md."""
    review_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    pull_number: int
    head_sha: str
    summary: str
    overall_risk: ReviewRisk
    risk_rationale: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    verdict: ReviewVerdict
    findings: List[ReviewFindingSchema] = Field(default_factory=list)
    metadata: Optional[ReviewMetadataSchema] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewCreateRequest(BaseModel):
    """Request payload to initiate a structured code review on a pull request."""
    pull_number: int
    post_to_github: bool = Field(default=False, description="Whether to post review comments back to GitHub PR")
    focus_areas: Optional[List[str]] = Field(default=None, description="Optional list of specific areas (e.g. security, performance)")


class ReviewFindingResponse(BaseModel):
    """API response model for an individual review finding."""
    id: uuid.UUID
    review_id: uuid.UUID
    file: str
    line: int
    end_line: Optional[int] = None
    category: FindingCategory
    severity: FindingSeverity
    description: str
    recommendation: str
    suggested_diff: Optional[str] = None
    confidence: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewResponse(BaseModel):
    """API response model for a full review entity."""
    id: uuid.UUID
    pull_request_id: uuid.UUID
    agent_run_id: Optional[uuid.UUID] = None
    head_sha: str
    status: ReviewStatus
    summary: str
    overall_risk: ReviewRisk
    risk_rationale: Optional[str] = None
    verdict: ReviewVerdict
    confidence: float
    model_name: str
    token_usage: Dict[str, Any] = Field(default_factory=dict)
    review_metadata: Optional[Dict[str, Any]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    findings: List[ReviewFindingResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
