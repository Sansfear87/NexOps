from typing import Optional, List
from datetime import datetime
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.base import utc_now
from app.db.models.api_key import APIKey
from app.db.repositories.base import BaseRepository
from app.core.security import generate_api_key, hash_api_key


class APIKeyRepository(BaseRepository[APIKey]):
    def __init__(self, db: Session):
        super().__init__(APIKey, db)

    def create_api_key(
        self,
        project_id: uuid.UUID,
        name: str,
        created_by_user_id: Optional[uuid.UUID] = None,
        expires_at: Optional[datetime] = None,
        scopes: Optional[List[str]] = None
    ) -> tuple[APIKey, str]:
        raw_key, key_prefix, key_hash = generate_api_key()
        api_key = APIKey(
            project_id=project_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=scopes or ["*"],
            created_by_user_id=created_by_user_id,
            expires_at=expires_at
        )
        saved = self.create(api_key)
        return saved, raw_key

    def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        stmt = select(APIKey).where(APIKey.key_hash == key_hash)
        return self.db.scalars(stmt).first()

    def get_active_by_raw_key(self, raw_key: str) -> Optional[APIKey]:
        now = utc_now()
        key_hash = hash_api_key(raw_key)
        stmt = select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.revoked_at.is_(None)
        )
        key = self.db.scalars(stmt).first()
        if key and key.expires_at is not None:
            from datetime import timezone
            exp = key.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < now:
                return None
        return key

    def list_active_by_project(self, project_id: uuid.UUID) -> List[APIKey]:
        stmt = (
            select(APIKey)
            .where(
                APIKey.project_id == project_id,
                APIKey.revoked_at.is_(None)
            )
            .order_by(APIKey.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_id_and_project(self, key_id: uuid.UUID, project_id: uuid.UUID) -> Optional[APIKey]:
        stmt = select(APIKey).where(
            APIKey.id == key_id,
            APIKey.project_id == project_id
        )
        return self.db.scalars(stmt).first()

    def revoke_key(self, key_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        key = self.get_by_id_and_project(key_id, project_id)
        if key and key.revoked_at is None:
            key.revoked_at = utc_now()
            self.db.add(key)
            self.db.commit()
            return True
        return False
