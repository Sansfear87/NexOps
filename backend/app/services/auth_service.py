from datetime import timedelta
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.db.base import utc_now
from app.db.models.user import User
from app.db.models.session import Session as DBSession
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.auth_account_repository import AuthAccountRepository
from app.db.repositories.session_repository import SessionRepository
from app.db.repositories.audit_log_repository import AuditLogRepository
from app.db.constants import AuthProvider, ActorType, AuditResult
from app.core.security import hash_password, verify_password, generate_session_token

DEFAULT_SESSION_DAYS = 7


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.auth_repo = AuthAccountRepository(db)
        self.session_repo = SessionRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def register(
        self,
        email: str,
        password: str,
        display_name: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[User, DBSession, str]:
        normalized_email = email.strip().lower()

        # 1. Enforce unique email check
        existing_user = self.user_repo.get_by_email(normalized_email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists."
            )

        # 2. Create User record
        user = self.user_repo.create_user(
            email=normalized_email,
            display_name=display_name
        )

        # 3. Create password AuthAccount with bcrypt hash
        hashed_pwd = hash_password(password)
        self.auth_repo.create_password_account(
            user_id=user.id,
            email=normalized_email,
            password_hash=hashed_pwd
        )

        # 4. Create initial active Session (stores token_hash, returns raw_token)
        raw_token = generate_session_token()
        expires_at = utc_now() + timedelta(days=DEFAULT_SESSION_DAYS)
        session = self.session_repo.create_session(
            user_id=user.id,
            raw_token=raw_token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )

        # 5. Record immutable audit log
        self.audit_repo.record_action(
            action="USER_REGISTER",
            resource_type="user",
            resource_id=str(user.id),
            actor_id=str(user.id),
            actor_type=ActorType.USER.value,
            ip_address=ip_address,
            metadata={"email": user.email}
        )

        return user, session, raw_token

    def login(
        self,
        email: str,
        password: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[User, DBSession, str]:
        normalized_email = email.strip().lower()
        account = self.auth_repo.get_by_provider_and_user_id(AuthProvider.PASSWORD.value, normalized_email)
        if not account or not account.password_hash:
            self.audit_repo.record_action(
                action="USER_LOGIN_FAILED",
                resource_type="auth_account",
                resource_id=normalized_email,
                result=AuditResult.DENIED.value,
                ip_address=ip_address
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        if not verify_password(password, account.password_hash):
            self.audit_repo.record_action(
                action="USER_LOGIN_FAILED",
                resource_type="auth_account",
                resource_id=normalized_email,
                result=AuditResult.DENIED.value,
                ip_address=ip_address
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        user = self.user_repo.get_by_id(account.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated."
            )

        raw_token = generate_session_token()
        expires_at = utc_now() + timedelta(days=DEFAULT_SESSION_DAYS)
        session = self.session_repo.create_session(
            user_id=user.id,
            raw_token=raw_token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )

        self.audit_repo.record_action(
            action="USER_LOGIN",
            resource_type="session",
            resource_id=str(session.id),
            actor_id=str(user.id),
            actor_type=ActorType.USER.value,
            ip_address=ip_address
        )

        return user, session, raw_token

    def logout(self, raw_token: str) -> None:
        session = self.session_repo.get_active_session(raw_token)
        if session:
            self.session_repo.revoke_session(raw_token)
            self.audit_repo.record_action(
                action="USER_LOGOUT",
                resource_type="session",
                resource_id=str(session.id),
                actor_id=str(session.user_id),
                actor_type=ActorType.USER.value
            )

    def get_user_by_session(self, raw_token: str) -> Optional[User]:
        session = self.session_repo.get_active_session(raw_token)
        if not session or not session.user or not session.user.is_active:
            return None
        return session.user
