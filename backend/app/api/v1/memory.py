"""FastAPI route controllers for Phase 11: Project Persistent Memory."""
from __future__ import annotations

import logging
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.constants import ProjectRole
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.memory import (
    MemoryResponse,
    MemorySearchResponse,
    MemoryStoreRequest,
)
from app.services.memory_service import MemoryService
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/projects/{project_id}/memory",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store or update knowledge in project persistent memory",
)
def store_memory_item(
    project_id: uuid.UUID,
    payload: MemoryStoreRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Store knowledge item with automated secret redaction."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.DEVELOPER)

    service = MemoryService(db)
    item = service.store(
        project_id=project_id,
        key=payload.key,
        content=payload.content,
        category=payload.category,
        importance=payload.importance,
        metadata_json=payload.metadata,
    )
    return item


@router.get(
    "/projects/{project_id}/memory",
    response_model=MemorySearchResponse,
    summary="Search project memory items",
)
def search_memory(
    project_id: uuid.UUID,
    q: Optional[str] = Query(None, description="Keyword or semantic search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Search knowledge items matching query or category."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    service = MemoryService(db)
    items = service.search(project_id, query=q, category=category, limit=limit)
    return MemorySearchResponse(items=[MemoryResponse.model_validate(it) for it in items], total=len(items))


@router.get(
    "/projects/{project_id}/memory/{key}",
    response_model=MemoryResponse,
    summary="Get memory item by exact key",
)
def get_memory_item(
    project_id: uuid.UUID,
    key: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Fetch knowledge item by unique key."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    service = MemoryService(db)
    item = service.get_by_key(project_id, key)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory key '{key}' not found")
    return item
