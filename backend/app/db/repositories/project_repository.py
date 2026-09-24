from typing import Optional, List
import uuid
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: Session):
        super().__init__(Project, db)

    def get_by_slug(self, slug: str) -> Optional[Project]:
        stmt = select(Project).where(
            Project.slug == slug.strip().lower(),
            Project.is_archived.is_(False)
        )
        return self.db.scalars(stmt).first()

    def get_active_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        stmt = select(Project).where(
            Project.id == project_id,
            Project.is_archived.is_(False)
        )
        return self.db.scalars(stmt).first()

    def create_project(
        self,
        name: str,
        slug: str,
        owner_id: uuid.UUID,
        description: Optional[str] = None
    ) -> Project:
        project = Project(
            name=name.strip(),
            slug=slug.strip().lower(),
            owner_id=owner_id,
            description=description.strip() if description else None,
            is_archived=False
        )
        return self.create(project)

    def list_accessible_projects(self, user_id: uuid.UUID) -> List[Project]:
        """List active projects where user is owner or explicit project member."""
        stmt = (
            select(Project)
            .outerjoin(ProjectMember, Project.id == ProjectMember.project_id)
            .where(
                Project.is_archived.is_(False),
                or_(
                    Project.owner_id == user_id,
                    ProjectMember.user_id == user_id
                )
            )
            .distinct()
            .order_by(Project.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def soft_delete(self, project: Project) -> Project:
        project.is_archived = True
        return self.update(project)
