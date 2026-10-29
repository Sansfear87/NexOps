from typing import Dict, List, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str
    phase: str
    active_phases: Optional[List[str]] = None
    ai_engine: Optional[str] = None
    models: Optional[Dict[str, str]] = None
