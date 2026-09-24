from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.db.base import utc_now
from app.db.models.session import Session as DBSession
from app.db.repositories.base import BaseRepository


class SessionRepository(BaseRepository[DBSession]):
    def __init__(self, db: Session):
        super().__init__(DBSession, db)

    def create_session(
        self,
        user_id: uuid.UUID,
        session_token: str,
        expires_at: datetime,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> DBSession:
        session = DBSession(
            user_id=user_id,
            session_token=session_token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )
        return self.create(session)

    def get_active_session(self, session_token: str) -> Optional[DBSession]:
        now = utc_now()
        stmt = select(DBSession).where(
            DBSession.session_token == session_token,
            DBSession.revoked_at.is_(None),
            DBSession.expires_at > now
        )
        return self.db.scalars(stmt).first()

    def revoke_session(self, session_token: str) -> bool:
        session = self.get_active_session(session_token)
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
