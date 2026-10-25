"""Repository for HealthCheck and HealthMetric database operations."""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.monitoring import HealthCheck, HealthMetric
from app.db.repositories.base import BaseRepository


class MonitoringRepository(BaseRepository[HealthCheck]):
    """Repository managing synthetic health probe checks and runtime metrics."""

    def __init__(self, db: Session):
        super().__init__(HealthCheck, db)

    def record_probe(
        self,
        deployment_id: UUID,
        project_id: UUID,
        endpoint: str,
        status_code: Optional[int],
        latency_ms: float,
        is_healthy: bool,
        error_message: Optional[str] = None,
    ) -> HealthCheck:
        """Record a single synthetic health check result."""
        check = HealthCheck(
            deployment_id=deployment_id,
            project_id=project_id,
            endpoint=endpoint,
            status_code=status_code,
            latency_ms=latency_ms,
            is_healthy=is_healthy,
            error_message=error_message,
        )
        self.db.add(check)
        self.db.flush()
        return check

    def list_probes_by_deployment(self, deployment_id: UUID, limit: int = 50) -> List[HealthCheck]:
        """Fetch recent synthetic health checks for a deployment."""
        return (
            self.db.query(HealthCheck)
            .filter(HealthCheck.deployment_id == deployment_id)
            .order_by(HealthCheck.created_at.desc())
            .limit(limit)
            .all()
        )

    def record_metric(
        self,
        deployment_id: UUID,
        project_id: UUID,
        metric_name: str,
        value: float,
        unit: str = "ms",
    ) -> HealthMetric:
        """Record a runtime or latency performance metric."""
        metric = HealthMetric(
            deployment_id=deployment_id,
            project_id=project_id,
            metric_name=metric_name,
            value=value,
            unit=unit,
        )
        self.db.add(metric)
        self.db.flush()
        return metric

    def get_metrics_by_deployment(self, deployment_id: UUID, metric_name: Optional[str] = None) -> List[HealthMetric]:
        """Fetch time-series metrics for a deployment."""
        query = self.db.query(HealthMetric).filter(HealthMetric.deployment_id == deployment_id)
        if metric_name:
            query = query.filter(HealthMetric.metric_name == metric_name)
        return query.order_by(HealthMetric.created_at.desc()).limit(100).all()
