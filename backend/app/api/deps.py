from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.db.repositories.api_key_repository import APIKeyRepository
from app.services.auth_service import AuthService

security_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> User:
    """Dependency that authenticates the user from:
    1. Bearer session token
    2. Bearer API key (nxp_live_...)
    3. X-API-Key header
    """
    token: Optional[str] = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    elif x_api_key:
        token = x_api_key

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 1. Check if token is an API Key (starts with nxp_)
    if token.startswith("nxp_"):
        api_key_repo = APIKeyRepository(db)
        api_key = api_key_repo.get_active_by_raw_key(token)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        if api_key.created_by and api_key.created_by.is_active:
            return api_key.created_by
        # Fallback to project owner if created_by is null or inactive
        if api_key.project and api_key.project.owner:
            return api_key.project.owner

    # 2. Check session token
    auth_service = AuthService(db)
    user = auth_service.get_user_by_session(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account."
        )
    return current_user
