"""Event stream and listing API endpoints."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator, List
import uuid
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.constants import ProjectRole
from app.db.models.user import User
from app.db.session import get_db, SessionLocal
from app.schemas.event import PlatformEventRead
from app.services.event_bus import EventBus
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/projects/{project_id}/events",
    response_model=List[PlatformEventRead],
    summary="List recent platform events for a project",
)
@router.get(
    "/{project_id}",
    response_model=List[PlatformEventRead],
    include_in_schema=False,
)
def list_events(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve recent platform events associated with a project."""
    project_service = ProjectService(db)
    project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    event_bus = EventBus(db)
    events = event_bus.get_events(project_id, limit=limit)
    return [PlatformEventRead.model_validate(e) for e in events]


@router.get(
    "/projects/{project_id}/events/stream",
    summary="Server-Sent Events (SSE) stream of real-time events",
)
@router.get(
    "/{project_id}/stream",
    include_in_schema=False,
)
async def event_stream(
    project_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Server-Sent Events (SSE) endpoint streaming real-time platform events."""
    # Check permissions with a scoped session
    with SessionLocal() as db:
        project_service = ProjectService(db)
        project_service._require_role(current_user, project_id, ProjectRole.VIEWER)

    async def sse_generator() -> AsyncGenerator[str, None]:
        last_event_time = None
        # Send initial connected ping
        yield f"event: ping\ndata: {json.dumps({'message': 'connected', 'project_id': str(project_id)})}\n\n"

        while True:
            if await request.is_disconnected():
                break

            try:
                # Query recent events with a fresh short-lived session
                with SessionLocal() as db:
                    event_bus = EventBus(db)
                    recent_events = event_bus.get_events(project_id, limit=10)

                for ev in reversed(recent_events):
                    if last_event_time is None or ev.created_at > last_event_time:
                        last_event_time = ev.created_at
                        event_data = {
                            "id": str(ev.id),
                            "event_type": ev.event_type,
                            "version": ev.version,
                            "trace_id": str(ev.trace_id),
                            "project_id": str(ev.project_id),
                            "actor_id": ev.actor_id,
                            "actor_type": ev.actor_type,
                            "payload": ev.payload,
                            "created_at": ev.created_at.isoformat(),
                        }
                        yield f"event: {ev.event_type}\ndata: {json.dumps(event_data)}\n\n"

            except Exception as exc:
                logger.error("Error in SSE event stream: %s", exc)

            # Send heartbeat keep-alive comment every 3 seconds
            yield ": heartbeat\n\n"
            await asyncio.sleep(3.0)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
