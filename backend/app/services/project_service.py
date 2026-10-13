from typing import List, Optional
from datetime import timedelta
import uuid
import re
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.db.base import utc_now
from app.db.models.user import User
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.models.api_key import APIKey
from app.db.repositories.project_repository import ProjectRepository
from app.db.repositories.project_member_repository import ProjectMemberRepository
from app.db.repositories.api_key_repository import APIKeyRepository
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.audit_log_repository import AuditLogRepository
from app.db.constants import ProjectRole, AuditResult


ROLE_LEVELS = {
    ProjectRole.VIEWER.value: 1,
    ProjectRole.DEVELOPER.value: 2,
    ProjectRole.MAINTAINER.value: 3,
    ProjectRole.OWNER.value: 4,
}


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.member_repo = ProjectMemberRepository(db)
        self.api_key_repo = APIKeyRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def _require_role(
        self,
        user: User,
        project_id: uuid.UUID,
        min_role: ProjectRole
    ) -> ProjectMember:
        """Verify user has at least min_role in project."""
        if user.is_superuser:
            # Return active membership or mock superuser access
            mem = self.member_repo.get_member(project_id, user.id)
            if mem:
                return mem
            # Synthesize owner membership for superuser
            return ProjectMember(
                project_id=project_id,
                user_id=user.id,
                role=ProjectRole.OWNER.value
            )

        membership = self.member_repo.get_member(project_id, user.id)
        if not membership:
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

        user_level = ROLE_LEVELS.get(membership.role, 0)
        required_level = ROLE_LEVELS.get(min_role.value, 0)
        if user_level < required_level:
            self.audit_repo.record_action(
                action="PROJECT_PERMISSION_DENIED",
                resource_type="project",
                resource_id=str(project_id),
                actor_id=str(user.id),
                result=AuditResult.DENIED.value,
                metadata={"required_role": min_role.value, "user_role": membership.role}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Requires '{min_role.value}' role."
            )

        return membership

    def create_project(
        self,
        user: User,
        name: str,
        slug: Optional[str] = None,
        description: Optional[str] = None
    ) -> Project:
        if not slug or not slug.strip():
            slug = slugify(name)
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
        self.member_repo.add_member(
            project_id=project.id,
            user_id=user.id,
            role=ProjectRole.OWNER.value
        )
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

        # Canonical Authorization Check
        self._require_role(user, project_id, ProjectRole.VIEWER)
        return project

    def delete_project(self, user: User, project_id: uuid.UUID) -> None:
        project = self.project_repo.get_active_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found."
            )

        # Only OWNER or superuser may delete/archive project
        self._require_role(user, project_id, ProjectRole.OWNER)

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

    # -------------------------------------------------------------
    # Team Member Management & RBAC
    # -------------------------------------------------------------
    def list_members(self, user: User, project_id: uuid.UUID) -> List[ProjectMember]:
        self.get_project_for_user(user, project_id)
        return self.member_repo.list_members(project_id)

    def add_member(
        self,
        current_user: User,
        project_id: uuid.UUID,
        email: str,
        role: str
    ) -> ProjectMember:
        project = self.get_project_for_user(current_user, project_id)

        # Require MAINTAINER to add members
        actor_membership = self._require_role(current_user, project_id, ProjectRole.MAINTAINER)

        # Only OWNER can add another OWNER
        if role == ProjectRole.OWNER.value and actor_membership.role != ProjectRole.OWNER.value and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project owners can grant the OWNER role."
            )

        # Find target user
        target_user = self.user_repo.get_by_email(email.strip().lower())
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No registered user found with email '{email}'."
            )

        # Check existing membership
        existing = self.member_repo.get_member(project_id, target_user.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{email}' is already a member of this project."
            )

        member = self.member_repo.add_member(project_id, target_user.id, role)

        # Audit
        self.audit_repo.record_action(
            action="PROJECT_MEMBER_ADDED",
            resource_type="project_member",
            resource_id=str(member.id),
            actor_id=str(current_user.id),
            project_id=project.id,
            metadata={"user_id": str(target_user.id), "email": email, "role": role}
        )
        return member

    def update_member_role(
        self,
        current_user: User,
        project_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: str
    ) -> ProjectMember:
        project = self.get_project_for_user(current_user, project_id)

        # Only OWNER can change member roles
        self._require_role(current_user, project_id, ProjectRole.OWNER)

        target_member = self.member_repo.get_member(project_id, target_user_id)
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this project."
            )

        # Guard: Cannot demote the last OWNER
        if target_member.role == ProjectRole.OWNER.value and new_role != ProjectRole.OWNER.value:
            if self.member_repo.count_owners(project_id) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the last project owner."
                )

        updated = self.member_repo.update_role(project_id, target_user_id, new_role)
        if not updated:
            raise HTTPException(status_code=404, detail="Member could not be updated.")

        self.audit_repo.record_action(
            action="PROJECT_MEMBER_ROLE_UPDATED",
            resource_type="project_member",
            resource_id=str(updated.id),
            actor_id=str(current_user.id),
            project_id=project.id,
            metadata={"user_id": str(target_user_id), "new_role": new_role}
        )
        return updated

    def remove_member(
        self,
        current_user: User,
        project_id: uuid.UUID,
        target_user_id: uuid.UUID
    ) -> None:
        project = self.get_project_for_user(current_user, project_id)

        target_member = self.member_repo.get_member(project_id, target_user_id)
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this project."
            )

        # Self-removal
        if current_user.id == target_user_id:
            if target_member.role == ProjectRole.OWNER.value and self.member_repo.count_owners(project_id) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot leave project as the sole owner. Assign another owner first."
                )
        else:
            # Removing other users requires MAINTAINER or OWNER
            actor_mem = self._require_role(current_user, project_id, ProjectRole.MAINTAINER)
            if target_member.role == ProjectRole.OWNER.value:
                if actor_mem.role != ProjectRole.OWNER.value and not current_user.is_superuser:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only project owners can remove an owner."
                    )
                if self.member_repo.count_owners(project_id) <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot remove the sole project owner."
                    )

        self.member_repo.remove_member(project_id, target_user_id)

        self.audit_repo.record_action(
            action="PROJECT_MEMBER_REMOVED",
            resource_type="project_member",
            resource_id=str(target_member.id),
            actor_id=str(current_user.id),
            project_id=project.id,
            metadata={"removed_user_id": str(target_user_id)}
        )

    # -------------------------------------------------------------
    # API Key Token Management
    # -------------------------------------------------------------
    def create_api_key(
        self,
        current_user: User,
        project_id: uuid.UUID,
        name: str,
        expires_in_days: Optional[int] = None,
        scopes: Optional[List[str]] = None
    ) -> tuple[APIKey, str]:
        project = self.get_project_for_user(current_user, project_id)
        self._require_role(current_user, project_id, ProjectRole.MAINTAINER)

        expires_at = None
        if expires_in_days:
            expires_at = utc_now() + timedelta(days=expires_in_days)

        api_key, raw_key = self.api_key_repo.create_api_key(
            project_id=project.id,
            name=name.strip(),
            created_by_user_id=current_user.id,
            expires_at=expires_at,
            scopes=scopes
        )

        self.audit_repo.record_action(
            action="PROJECT_API_KEY_CREATED",
            resource_type="api_key",
            resource_id=str(api_key.id),
            actor_id=str(current_user.id),
            project_id=project.id,
            metadata={"name": name, "prefix": api_key.key_prefix}
        )

        return api_key, raw_key

    def list_api_keys(self, current_user: User, project_id: uuid.UUID) -> List[APIKey]:
        project = self.get_project_for_user(current_user, project_id)
        self._require_role(current_user, project_id, ProjectRole.DEVELOPER)
        return self.api_key_repo.list_active_by_project(project.id)

    def revoke_api_key(self, current_user: User, project_id: uuid.UUID, key_id: uuid.UUID) -> None:
        project = self.get_project_for_user(current_user, project_id)
        self._require_role(current_user, project_id, ProjectRole.MAINTAINER)

        success = self.api_key_repo.revoke_key(key_id, project.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found or already revoked."
            )

        self.audit_repo.record_action(
            action="PROJECT_API_KEY_REVOKED",
            resource_type="api_key",
            resource_id=str(key_id),
            actor_id=str(current_user.id),
            project_id=project.id
        )
