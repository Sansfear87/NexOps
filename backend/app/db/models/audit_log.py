import uuid
from typing import Optional, Dict, Any
from sqlalchemy import String, ForeignKey, CheckConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin, json_column
from app.db.constants import ActorType, AuditResult


class AuditLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint("actor_type IN ('USER', 'AGENT', 'SYSTEM', 'WEBHOOK')", name="ck_audit_logs_actor_type"),
        CheckConstraint("result IN ('SUCCESS', 'DENIED', 'ERROR')", name="ck_audit_logs_result"),
    )

    # actor_id intentionally has NO foreign key to users.id to support AGENT/SYSTEM actors
    # and guarantee audit immutability if a user record is purged.
    actor_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(32), default=ActorType.USER.value, nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
    result: Mapped[str] = mapped_column(String(32), default=AuditResult.SUCCESS.value, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    # OpenTelemetry trace_id: 32-hex character W3C string or UUID string
    trace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(json_column(), default=dict, nullable=False)
