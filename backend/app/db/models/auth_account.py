import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, UniqueConstraint, CheckConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDMixin, TimestampMixin
from app.db.constants import AuthProvider

if TYPE_CHECKING:
    from app.db.models.user import User


class AuthAccount(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "auth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_auth_accounts_provider_user_id"),
        CheckConstraint("provider IN ('password', 'github', 'google')", name="ck_auth_accounts_provider"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="auth_accounts")
