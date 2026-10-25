"""SQLAlchemy models for Phase 11: Project Persistent Memory adhering to contracts/memory_contract.md."""
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.db.constants import MemoryCategory


class ProjectMemoryItem(Base):
    """Persistent cross-session project knowledge, post-mortems, and architectural heuristics."""
    __tablename__ = "project_memory"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = Column(String(32), default=MemoryCategory.POSTMORTEM.value, nullable=False, index=True)
    key = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    importance = Column(Integer, default=3, nullable=False)  # 1 to 5 scale
    
    # Semantic embedding vector or tokens (stored as JSON for universal PG/SQLite portability)
    embedding = Column(
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        nullable=True,
    )
    metadata_json = Column(
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        default=dict,
        nullable=False,
    )

    access_count = Column(Integer, default=0, nullable=False)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", backref="memory_items")
