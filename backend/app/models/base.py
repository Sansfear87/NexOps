"""Base declarative definitions re-exported for backwards-compatibility."""
from app.db.base import Base, TimestampMixin, UUIDMixin, utc_now, json_column

__all__ = ["Base", "TimestampMixin", "UUIDMixin", "utc_now", "json_column"]
