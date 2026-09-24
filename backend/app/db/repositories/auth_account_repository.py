from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models.auth_account import AuthAccount
from app.db.repositories.base import BaseRepository


class AuthAccountRepository(BaseRepository[AuthAccount]):
    def __init__(self, db: Session):
        super().__init__(AuthAccount, db)

    def get_by_provider_and_user_id(self, provider: str, provider_user_id: str) -> Optional[AuthAccount]:
        stmt = select(AuthAccount).where(
            AuthAccount.provider == provider,
            AuthAccount.provider_user_id == provider_user_id
        )
        return self.db.scalars(stmt).first()

    def create_password_account(
        self,
        user_id: uuid.UUID,
        email: str,
        password_hash: str
    ) -> AuthAccount:
        account = AuthAccount(
            user_id=user_id,
            provider="password",
            provider_user_id=email.strip().lower(),
            password_hash=password_hash
        )
        return self.create(account)
