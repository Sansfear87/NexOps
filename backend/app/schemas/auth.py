from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, EmailStr, Field
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
