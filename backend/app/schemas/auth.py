import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.schemas.user import UserRead


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    display_name: str = Field(..., min_length=2, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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

