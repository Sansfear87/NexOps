from typing import Optional, Dict, Any, List
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models.audit_log import AuditLog
from app.db.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Session):
        super().__init__(AuditLog, db)

    def record_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        result: str = "SUCCESS",
        actor_id: Optional[uuid.UUID] = None,
        actor_type: str = "USER",
        project_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        trace_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        log = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            actor_id=actor_id,
            actor_type=actor_type,
            project_id=project_id,
            ip_address=ip_address,
            trace_id=trace_id,
            metadata_json=metadata or {}
        )
        return self.create(log)

    def list_by_project(self, project_id: uuid.UUID, limit: int = 50) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.project_id == project_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
