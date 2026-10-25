"""Repository for ProjectMemoryItem database operations conforming to contracts/memory_contract.md."""
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.constants import MemoryCategory
from app.db.models.memory import ProjectMemoryItem
from app.db.repositories.base import BaseRepository

# Secret redaction pattern to prevent sensitive tokens from entering memory
SECRET_REDACT_PATTERNS = [
    re.compile(r"""(sk_live_[0-9a-zA-Z]{10,}|ghp_[0-9a-zA-Z]{20,}|Bearer\s+[a-zA-Z0-9_\-\.]+)""", re.I),
    re.compile(r"""(?i)(password|secret|api_key|token)\s*=\s*['"][^'"]+['"]"""),
]


def redact_secrets_from_text(text: str) -> str:
    """Sanitize secrets and credentials before storing to persistent memory."""
    sanitized = text
    for pattern in SECRET_REDACT_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


class MemoryRepository(BaseRepository[ProjectMemoryItem]):
    """Repository managing cross-session persistent project memory."""

    def __init__(self, db: Session):
        super().__init__(ProjectMemoryItem, db)

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
        """Store or update a memory item with secret redaction."""
        clean_content = redact_secrets_from_text(content)
        
        # Check if item with this key already exists for the project
        existing = (
            self.db.query(ProjectMemoryItem)
            .filter(ProjectMemoryItem.project_id == project_id, ProjectMemoryItem.key == key)
            .first()
        )
        if existing:
            existing.content = clean_content
            existing.category = category
            existing.importance = importance
            existing.metadata_json = metadata_json or {}
            if embedding:
                existing.embedding = embedding
            existing.updated_at = datetime.now(timezone.utc)
            self.db.flush()
            return existing

        item = ProjectMemoryItem(
            project_id=project_id,
            key=key,
            content=clean_content,
            category=category,
            importance=importance,
            metadata_json=metadata_json or {},
            embedding=embedding,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_by_key(self, project_id: UUID, key: str) -> Optional[ProjectMemoryItem]:
        """Fetch memory item by exact key."""
        item = (
            self.db.query(ProjectMemoryItem)
            .filter(ProjectMemoryItem.project_id == project_id, ProjectMemoryItem.key == key)
            .first()
        )
        if item:
            item.access_count += 1
            item.last_accessed_at = datetime.now(timezone.utc)
            self.db.flush()
        return item

    def search(
        self,
        project_id: UUID,
        query_str: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[ProjectMemoryItem]:
        """Search memory items by category or keyword matching."""
        query = self.db.query(ProjectMemoryItem).filter(ProjectMemoryItem.project_id == project_id)
        if category:
            query = query.filter(ProjectMemoryItem.category == category)
        if query_str:
            pattern = f"%{query_str}%"
            query = query.filter(
                (ProjectMemoryItem.key.ilike(pattern)) | (ProjectMemoryItem.content.ilike(pattern))
            )
        items = query.order_by(ProjectMemoryItem.importance.desc(), ProjectMemoryItem.updated_at.desc()).limit(limit).all()
        for it in items:
            it.access_count += 1
            it.last_accessed_at = datetime.now(timezone.utc)
        self.db.flush()
        return items
