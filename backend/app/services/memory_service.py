"""Semantic Project Memory Service adhering to contracts/memory_contract.md."""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.constants import MemoryCategory
from app.db.models.memory import ProjectMemoryItem
from app.db.repositories.memory_repository import MemoryRepository

logger = logging.getLogger(__name__)


class MemoryService:
    """Service managing persistent project memory, secret sanitization, and semantic retrieval."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = MemoryRepository(db)

    def store(
        self,
        project_id: UUID,
        key: str,
        content: str,
        category: str = MemoryCategory.POSTMORTEM.value,
        importance: int = 3,
        metadata_json: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> ProjectMemoryItem:
        """Store knowledge in project memory with automated secret redaction."""
        item = self.repo.store(
            project_id=project_id,
            key=key,
            content=content,
            category=category,
            importance=importance,
            metadata_json=metadata_json,
            embedding=embedding,
        )
        self.db.commit()
        return item

    def get_by_key(self, project_id: UUID, key: str) -> Optional[ProjectMemoryItem]:
        """Fetch memory item by unique key within project."""
        item = self.repo.get_by_key(project_id, key)
        if item:
            self.db.commit()
        return item

    def search(
        self,
        project_id: UUID,
        query: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[ProjectMemoryItem]:
        """Search relevant project memory items using text similarity and category filters."""
        items = self.repo.search(
            project_id=project_id,
            query_str=query,
            category=category,
            limit=limit,
        )
        self.db.commit()
        return items

    def list_by_project(
        self,
        project_id: UUID,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[ProjectMemoryItem]:
        """List all memory entries for a project."""
        return self.search(project_id=project_id, category=category, limit=limit)
