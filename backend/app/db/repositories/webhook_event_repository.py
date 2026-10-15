"""Repository for WebhookEvent entity."""
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models.webhook_event import WebhookEvent
from app.db.repositories.base import BaseRepository


class WebhookEventRepository(BaseRepository[WebhookEvent]):
    """Repository managing WebhookEvent logging and processing status."""

    def __init__(self, db: Session):
        super().__init__(WebhookEvent, db)

    def get_by_delivery_id(self, delivery_id: str) -> Optional[WebhookEvent]:
        """Fetch event by GitHub delivery UUID for deduplication."""
        stmt = select(WebhookEvent).where(WebhookEvent.delivery_id == delivery_id)
        return self.db.scalars(stmt).first()

    def get_unprocessed(self, limit: int = 50) -> List[WebhookEvent]:
        """Fetch oldest unprocessed webhook events."""
        stmt = (
            select(WebhookEvent)
            .where(WebhookEvent.processed.is_(False))
            .order_by(WebhookEvent.created_at.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def mark_processed(
        self, event_id: uuid.UUID, error_message: Optional[str] = None
    ) -> None:
        """Mark event as processed with optional error record."""
        event = self.get_by_id(event_id)
        if event:
            event.processed = True
            event.error_message = error_message
            self.update(event)
