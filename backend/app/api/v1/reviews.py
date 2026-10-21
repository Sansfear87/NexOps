"""FastAPI route controllers for structured PR code reviews."""
from __future__ import annotations

import logging
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.constants import ProjectRole, ReviewRisk, ReviewStatus, ReviewVerdict
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.review import (
    ReviewCreateRequest,
    ReviewFindingResponse,
    ReviewResponse,
    ReviewResultSchema,
)
from app.services.project_service import ProjectService
from app.services.review_service import ReviewService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/projects/{project_id}/github/pulls/{pull_number}/review",
    response_model=ReviewResultSchema,
    status_code=status.HTTP_200_OK,
    summary="Trigger an autonomous AI code review for a pull request",
)
def run_pr_review(
    project_id: uuid.UUID,
    pull_number: int,
    payload: Optional[ReviewCreateRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Execute AI review on pull request diff, compute risk gates, and optionally post to GitHub."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.DEVELOPER)

    post_to_github = payload.post_to_github if payload else False
    focus_areas = payload.focus_areas if payload else None

    review_service = ReviewService(db)
    result = review_service.execute_review(
        project_id=project_id,
        pull_number=pull_number,
        user_id=current_user.id,
        post_to_github=post_to_github,
        focus_areas=focus_areas,
    )
    return result


@router.get(
    "/projects/{project_id}/github/pulls/{pull_number}/reviews",
    response_model=List[ReviewResponse],
    summary="List past AI reviews for a pull request",
)
def list_pr_reviews(
    project_id: uuid.UUID,
    pull_number: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve all historical reviews executed for a given pull request."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    review_service = ReviewService(db)
    connections = review_service.connection_repo.get_by_project(project_id)
    if not connections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No GitHub connection found for this project.",
        )

    pr = review_service.pr_repo.get_by_connection_and_number(connections[0].id, pull_number)
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pull request #{pull_number} not found.",
        )

    reviews = review_service.review_repo.list_by_pull_request(pr.id)
    return [
        ReviewResponse(
            id=r.id,
            pull_request_id=r.pull_request_id,
            agent_run_id=r.agent_run_id,
            head_sha=r.head_sha,
            status=ReviewStatus(r.status),
            summary=r.summary,
            overall_risk=ReviewRisk(r.overall_risk),
            risk_rationale=r.risk_rationale,
            verdict=ReviewVerdict(r.verdict),
            confidence=r.confidence,
            model_name=r.model_name,
            token_usage=r.token_usage,
            review_metadata=r.review_metadata,
            started_at=r.started_at,
            completed_at=r.completed_at,
            created_at=r.created_at,
            updated_at=r.updated_at,
            findings=[ReviewFindingResponse.model_validate(f) for f in r.findings],
        )
        for r in reviews
    ]


@router.get(
    "/projects/{project_id}/reviews",
    response_model=List[ReviewResponse],
    summary="List all reviews across project pull requests",
)
def list_project_reviews(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve recent reviews across all pull requests in the project."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    review_service = ReviewService(db)
    reviews = review_service.review_repo.list_by_project(project_id, limit=limit)
    return [
        ReviewResponse(
            id=r.id,
            pull_request_id=r.pull_request_id,
            agent_run_id=r.agent_run_id,
            head_sha=r.head_sha,
            status=ReviewStatus(r.status),
            summary=r.summary,
            overall_risk=ReviewRisk(r.overall_risk),
            risk_rationale=r.risk_rationale,
            verdict=ReviewVerdict(r.verdict),
            confidence=r.confidence,
            model_name=r.model_name,
            token_usage=r.token_usage,
            review_metadata=r.review_metadata,
            started_at=r.started_at,
            completed_at=r.completed_at,
            created_at=r.created_at,
            updated_at=r.updated_at,
            findings=[ReviewFindingResponse.model_validate(f) for f in r.findings],
        )
        for r in reviews
    ]


@router.get(
    "/projects/{project_id}/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Get details and findings for a specific review",
)
def get_review_detail(
    project_id: uuid.UUID,
    review_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve full finding breakdown and risk analysis for a review."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    review_service = ReviewService(db)
    review = review_service.review_repo.get_with_findings(review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found.",
        )

    return ReviewResponse(
        id=review.id,
        pull_request_id=review.pull_request_id,
        agent_run_id=review.agent_run_id,
        head_sha=review.head_sha,
        status=ReviewStatus(review.status),
        summary=review.summary,
        overall_risk=ReviewRisk(review.overall_risk),
        risk_rationale=review.risk_rationale,
        verdict=ReviewVerdict(review.verdict),
        confidence=review.confidence,
        model_name=review.model_name,
        token_usage=review.token_usage,
        review_metadata=review.review_metadata,
        started_at=review.started_at,
        completed_at=review.completed_at,
        created_at=review.created_at,
        updated_at=review.updated_at,
        findings=[ReviewFindingResponse.model_validate(f) for f in review.findings],
    )
