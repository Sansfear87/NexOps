import uuid
from datetime import datetime
from typing import Optional
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
from app.schemas.user import UserRead


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Minimum 6 characters")
    display_name: Optional[str] = Field(None, max_length=120)
    username: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("display_name"):
                data["display_name"] = data.get("username") or data.get("name") or data.get("email", "").split("@")[0] or "Developer"
        return data


class LoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: str

    @model_validator(mode="before")
    @classmethod
    def resolve_email(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("email") and data.get("username"):
                data["email"] = data.get("username")
        return data


class GitHubLoginRequest(BaseModel):
    token: str = Field(..., description="GitHub Personal Access Token or OAuth token")


class SessionRead(BaseModel):
    id: uuid.UUID
    session_token: str
    expires_at: datetime
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserRead
    session_token: str
    token_type: str = "bearer"
    expires_at: datetime


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


# Compatibility schemas for JWT/OAuth2 flows
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID | int
    email: EmailStr
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

