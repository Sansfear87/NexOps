"""Pydantic schemas for Phase 11: Project Persistent Memory."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MemoryStoreRequest(BaseModel):
    """Request payload to store or update a persistent memory item."""
    key: str = Field(..., min_length=1, max_length=255, description="Unique semantic key for this knowledge item")
    content: str = Field(..., min_length=1, description="Knowledge text or post-mortem Markdown summary")
    category: str = Field(default="incident_postmortem", description="Category of knowledge")
    importance: int = Field(default=3, ge=1, le=5, description="Significance rank (1-5)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata tags, author, trace correlation")


class MemoryResponse(BaseModel):
    """Serialized project memory response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    category: str
    key: str
    content: str
    importance: int
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MemorySearchRequest(BaseModel):
    """Request payload to search project memory."""
    query: Optional[str] = Field(None, description="Search query or keyword")
    category: Optional[str] = Field(None, description="Filter by category")
    limit: int = Field(default=10, ge=1, le=100)


class MemorySearchResponse(BaseModel):
    """List response for memory query."""
    items: List[MemoryResponse]
    total: int
