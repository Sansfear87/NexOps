from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.db.base import utc_now
from app.db.models.session import Session as DBSession
from app.db.repositories.base import BaseRepository
from app.core.security import hash_session_token


class SessionRepository(BaseRepository[DBSession]):
    def __init__(self, db: Session):
        super().__init__(DBSession, db)

    def create_session(
        self,
        user_id: uuid.UUID,
        raw_token: str,
        expires_at: datetime,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> DBSession:
        token_hash = hash_session_token(raw_token)
        session = DBSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )
        return self.create(session)

    def get_active_session(self, raw_token: str) -> Optional[DBSession]:
        now = utc_now()
        token_hash = hash_session_token(raw_token)
        stmt = select(DBSession).where(
            DBSession.token_hash == token_hash,
            DBSession.revoked_at.is_(None),
            DBSession.expires_at > now
        )
        return self.db.scalars(stmt).first()

    def revoke_session(self, raw_token: str) -> bool:
        session = self.get_active_session(raw_token)
        if session:
            session.revoked_at = utc_now()
            self.db.add(session)
            self.db.commit()
            return True
        return False

    def revoke_all_user_sessions(self, user_id: uuid.UUID) -> int:
        now = utc_now()
        stmt = (
            update(DBSession)
            .where(
                DBSession.user_id == user_id,
                DBSession.revoked_at.is_(None)
            )
            .values(revoked_at=now)
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount
