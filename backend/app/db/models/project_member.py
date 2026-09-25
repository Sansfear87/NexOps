import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, UniqueConstraint, CheckConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDMixin, TimestampMixin
from app.db.constants import ProjectRole

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.project import Project


class ProjectMember(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
        CheckConstraint("role IN ('OWNER', 'MAINTAINER', 'DEVELOPER', 'VIEWER')", name="ck_project_members_role"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[str] = mapped_column(String(32), default=ProjectRole.DEVELOPER.value, nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="project_memberships")
