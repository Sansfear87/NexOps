"""Pydantic schemas for Platform Events."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict


class PlatformEventRead(BaseModel):
    """Canonical platform event payload."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    version: str
    trace_id: uuid.UUID
    project_id: uuid.UUID
    actor_id: str
    actor_type: str
    payload: Dict[str, Any]
    processed: bool
    created_at: datetime
    updated_at: datetime
