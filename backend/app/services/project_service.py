from typing import List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.repositories.project_repository import ProjectRepository
from app.db.repositories.audit_log_repository import AuditLogRepository
from app.db.constants import ProjectRole, AuditResult


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def create_project(
        self,
        user: User,
        name: str,
        slug: str,
        description: Optional[str] = None
    ) -> Project:
        normalized_slug = slug.strip().lower()
        existing = self.project_repo.get_by_owner_and_slug(user.id, normalized_slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project slug '{normalized_slug}' is already taken in your account."
            )

        # 1. Create project with owner_id
        project = self.project_repo.create_project(
            name=name,
            slug=normalized_slug,
            owner_id=user.id,
            description=description
        )

        # 2. Add owner to project_members with role='OWNER' (Single Authorization Source)
        membership = ProjectMember(
            project_id=project.id,
            user_id=user.id,
            role=ProjectRole.OWNER.value
        )
        self.db.add(membership)
        self.db.commit()
        self.db.refresh(project)

        # 3. Audit log
        self.audit_repo.record_action(
            action="PROJECT_CREATED",
            resource_type="project",
            resource_id=str(project.id),
            actor_id=str(user.id),
            actor_type="USER",
            project_id=project.id,
            metadata={"name": project.name, "slug": project.slug}
        )

        return project

    def list_projects_for_user(self, user: User) -> List[Project]:
        return self.project_repo.list_accessible_projects(user.id)

    def get_project_for_user(self, user: User, project_id: uuid.UUID) -> Project:
        project = self.project_repo.get_active_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found."
            )

        # Single Canonical Authorization Check: Verify membership in project_members
        user_membership = next((m for m in project.members if m.user_id == user.id), None)
        if not user_membership and not user.is_superuser:
            self.audit_repo.record_action(
                action="PROJECT_ACCESS_DENIED",
                resource_type="project",
                resource_id=str(project_id),
                actor_id=str(user.id),
                result=AuditResult.DENIED.value
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project."
            )

        return project

    def delete_project(self, user: User, project_id: uuid.UUID) -> None:
        project = self.project_repo.get_active_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found."
            )

        # Only OWNER or superuser may delete/archive project
        user_membership = next((m for m in project.members if m.user_id == user.id), None)
        is_owner = (user_membership and user_membership.role == ProjectRole.OWNER.value) or (project.owner_id == user.id)

        if not is_owner and not user.is_superuser:
            self.audit_repo.record_action(
                action="PROJECT_DELETE_DENIED",
                resource_type="project",
                resource_id=str(project_id),
                actor_id=str(user.id),
                result=AuditResult.DENIED.value
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can delete this project."
            )

        # Soft delete
        self.project_repo.soft_delete(project)

        # Audit log
        self.audit_repo.record_action(
            action="PROJECT_DELETED",
            resource_type="project",
            resource_id=str(project.id),
            actor_id=str(user.id),
            actor_type="USER",
            project_id=project.id
        )
