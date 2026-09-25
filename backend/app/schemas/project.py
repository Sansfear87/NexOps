from datetime import datetime
from typing import Optional, List
import uuid
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.user import UserRead


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=1000)


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=1000)


class ProjectMemberRead(BaseModel):
    id: uuid.UUID | int
    user_id: uuid.UUID | int
    project_id: Optional[uuid.UUID | int] = None
    role: str
    created_at: datetime
    user: Optional[UserRead] = None

    model_config = ConfigDict(from_attributes=True)


MembershipResponse = ProjectMemberRead


class ProjectRead(ProjectBase):
    id: uuid.UUID | int
    owner_id: uuid.UUID | int
    slug: str
    is_archived: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    owner: Optional[UserRead] = None
    members: List[ProjectMemberRead] = []

    model_config = ConfigDict(from_attributes=True)


ProjectResponse = ProjectRead


class APIKeyCreate(BaseModel):
    name: str


class APIKeyResponse(BaseModel):
    id: uuid.UUID | int
    project_id: uuid.UUID | int
    key_prefix: str
    name: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APIKeyCreated(APIKeyResponse):
    raw_key: str

