import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, Uuid, JSON, func
from sqlalchemy.dialects.postgresql import JSONB


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass


class UUIDMixin:
    """Mixin providing RFC 4122 UUID primary key without redundant secondary index."""
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )


class TimestampMixin:
    """Reusable mixin providing created_at and updated_at timezone-aware UTC timestamps with server defaults."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
        nullable=False
    )


def json_column():
    """Return JSON column compatible with PostgreSQL JSONB and SQLite JSON."""
    return JSON().with_variant(JSONB(), "postgresql")
