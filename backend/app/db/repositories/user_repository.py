from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        normalized_email = email.strip().lower()
        stmt = select(User).where(User.email == normalized_email)
        return self.db.scalars(stmt).first()

    def create_user(
        self,
        email: str,
        display_name: str,
        avatar_url: Optional[str] = None,
        is_superuser: bool = False
    ) -> User:
        user = User(
            email=email.strip().lower(),
            display_name=display_name.strip(),
            avatar_url=avatar_url,
            is_superuser=is_superuser,
            is_active=True
        )
        return self.create(user)
