"""In-process PostgreSQL-backed event bus conforming to contracts/event_contract.md."""
from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Union
import uuid
from sqlalchemy.orm import Session
from app.db.constants import EventType, ActorType
from app.db.models.platform_event import PlatformEvent
from app.db.repositories.platform_event_repository import PlatformEventRepository

logger = logging.getLogger(__name__)

# Global registry of event handlers: event_type_str -> list of Callables
_GLOBAL_SUBSCRIBERS: Dict[str, List[Callable]] = {}


class EventBus:
    """In-process PostgreSQL-backed event bus matching contracts/event_contract.md."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = PlatformEventRepository(db)

    @classmethod
    def subscribe(cls, event_type: Union[EventType, str], handler: Callable) -> None:
        """Register a subscriber handler for a specific platform event type."""
        key = event_type.value if isinstance(event_type, EventType) else str(event_type)
        if key not in _GLOBAL_SUBSCRIBERS:
            _GLOBAL_SUBSCRIBERS[key] = []
        if handler not in _GLOBAL_SUBSCRIBERS[key]:
            _GLOBAL_SUBSCRIBERS[key].append(handler)

    def emit(
        self,
        event_type: Union[EventType, str],
        project_id: uuid.UUID,
        actor_id: str,
        actor_type: Union[ActorType, str],
        payload: Dict[str, Any],
        trace_id: Optional[uuid.UUID] = None,
        version: str = "1.0",
    ) -> PlatformEvent:
        """Persist an event record to the PostgreSQL ledger and dispatch to subscribers.

        Args:
            event_type: Canonical event identifier enum or string.
            project_id: Project UUID associated with this lifecycle transition.
            actor_id: ID of the invoking entity (user, agent, webhook).
            actor_type: Discriminator indicating entity category.
            payload: Typed structured data matching event schema.
            trace_id: Optional correlation UUID; generated if not provided.
            version: Schema version, defaults to '1.0'.

        Returns:
            The committed PlatformEvent model instance.
        """
        if trace_id is None:
            trace_id = uuid.uuid4()

        event = self.repo.emit(
            event_type=event_type,
            trace_id=trace_id,
            project_id=project_id,
            actor_id=str(actor_id),
            actor_type=actor_type,
            payload=payload,
            version=version,
        )

        key = event.event_type
        handlers = _GLOBAL_SUBSCRIBERS.get(key, [])
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(handler(event))
                    except RuntimeError:
                        asyncio.run(handler(event))
                else:
                    handler(event)
            except Exception as exc:
                logger.exception("Error executing subscriber for event %s: %s", key, exc)

        return event

    def get_events(
        self, project_id: uuid.UUID, limit: int = 50
    ) -> List[PlatformEvent]:
        """Fetch recent platform events for a given project."""
        return self.repo.get_recent(project_id, limit=limit)

    def get_events_by_trace(self, trace_id: uuid.UUID) -> List[PlatformEvent]:
        """Fetch all events correlated under a specific trace ID."""
        return self.repo.get_by_trace(trace_id)
