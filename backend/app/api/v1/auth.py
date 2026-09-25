from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, MessageResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService
from app.api.deps import get_current_user, security_bearer

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new developer account and return session token."""
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None

    auth_service = AuthService(db)
    user, session, raw_token = auth_service.register(
        email=data.email,
        password=data.password,
        display_name=data.display_name,
        user_agent=user_agent,
        ip_address=client_ip
    )
    return AuthResponse(
        user=UserRead.model_validate(user),
        session_token=raw_token,
        expires_at=session.expires_at
    )


@router.post("/login", response_model=AuthResponse)
def login(
    data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate with email and password to receive a new session token."""
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None

    auth_service = AuthService(db)
    user, session, raw_token = auth_service.login(
        email=data.email,
        password=data.password,
        user_agent=user_agent,
        ip_address=client_ip
    )
    return AuthResponse(
        user=UserRead.model_validate(user),
        session_token=raw_token,
        expires_at=session.expires_at
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
):
    """Revoke the current session token."""
    if credentials and credentials.credentials:
        auth_service = AuthService(db)
        auth_service.logout(credentials.credentials)
    return MessageResponse(message="Successfully logged out.")


@router.get("/me", response_model=UserRead)
def get_me(
    current_user: User = Depends(get_current_user)
):
    """Retrieve profile of the currently authenticated developer."""
    return UserRead.model_validate(current_user)

