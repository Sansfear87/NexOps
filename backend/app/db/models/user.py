from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.auth_account import AuthAccount
    from app.db.models.session import Session
    from app.db.models.project import Project
    from app.db.models.project_member import ProjectMember


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    auth_accounts: Mapped[List["AuthAccount"]] = relationship(
        "AuthAccount",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    sessions: Mapped[List["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    owned_projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="owner",
        cascade="save-update, merge",
        lazy="selectin"
    )
    project_memberships: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
