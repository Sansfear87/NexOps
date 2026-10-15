"""Repository for PlatformEvent entity."""
from typing import Any, Dict, List, Union
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models.platform_event import PlatformEvent
from app.db.constants import EventType, ActorType
from app.db.repositories.base import BaseRepository


class PlatformEventRepository(BaseRepository[PlatformEvent]):
    """Repository managing PlatformEvent persistence and traceability queries."""

    def __init__(self, db: Session):
        super().__init__(PlatformEvent, db)

    def emit(
        self,
        event_type: Union[EventType, str],
        trace_id: uuid.UUID,
        project_id: uuid.UUID,
        actor_id: str,
        actor_type: Union[ActorType, str],
        payload: Dict[str, Any],
        version: str = "1.0",
    ) -> PlatformEvent:
        """Create and persist a platform event record."""
        ev_type_str = event_type.value if isinstance(event_type, EventType) else str(event_type)
        actor_type_str = actor_type.value if isinstance(actor_type, ActorType) else str(actor_type)

        event = PlatformEvent(
            event_type=ev_type_str,
            version=version,
            trace_id=trace_id,
            project_id=project_id,
            actor_id=str(actor_id),
            actor_type=actor_type_str,
            payload=payload,
            processed=False,
        )
        return self.create(event)

    def get_by_trace(self, trace_id: uuid.UUID) -> List[PlatformEvent]:
        """Fetch all events correlated under a specific trace ID."""
        stmt = (
            select(PlatformEvent)
            .where(PlatformEvent.trace_id == trace_id)
            .order_by(PlatformEvent.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_recent(
        self, project_id: uuid.UUID, limit: int = 50
    ) -> List[PlatformEvent]:
        """Fetch recent platform events for a given project."""
        stmt = (
            select(PlatformEvent)
            .where(PlatformEvent.project_id == project_id)
            .order_by(PlatformEvent.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
