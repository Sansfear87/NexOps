import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None

class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    owner_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MembershipResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class APIKeyCreate(BaseModel):
    name: str

class APIKeyResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    key_prefix: str
    name: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class APIKeyCreated(APIKeyResponse):
    raw_key: str
