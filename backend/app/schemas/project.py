from datetime import datetime
from typing import Optional, List
import uuid
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.user import UserRead


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=1000)


class ProjectCreate(ProjectBase):
    pass


class ProjectMemberRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    created_at: datetime
    user: Optional[UserRead] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectRead(ProjectBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    owner: Optional[UserRead] = None
    members: List[ProjectMemberRead] = []

    model_config = ConfigDict(from_attributes=True)
