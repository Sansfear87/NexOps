from typing import List
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectMemberCreate,
    ProjectMemberUpdate,
    ProjectMemberRead,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreated,
)
from app.schemas.auth import MessageResponse
from app.services.project_service import ProjectService
from app.api.deps import get_current_user

router = APIRouter()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new project scoped to the authenticated user."""
    project_service = ProjectService(db)
    project = project_service.create_project(
        user=current_user,
        name=data.name,
        slug=data.slug,
        description=data.description
    )
    return ProjectRead.model_validate(project)


@router.get("", response_model=List[ProjectRead])
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all projects owned by or accessible to the current user."""
    project_service = ProjectService(db)
    projects = project_service.list_projects_for_user(current_user)
    return [ProjectRead.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve details for a specific project with strict tenant isolation."""
    project_service = ProjectService(db)
    project = project_service.get_project_for_user(current_user, project_id)
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", response_model=MessageResponse)
def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete/archive a project (owner-only action)."""
    project_service = ProjectService(db)
    project_service.delete_project(current_user, project_id)
    return MessageResponse(message=f"Project '{project_id}' successfully deleted.")


# -------------------------------------------------------------
# Project Team Members & RBAC
# -------------------------------------------------------------
@router.get("/{project_id}/members", response_model=List[ProjectMemberRead])
def list_project_members(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all members and their assigned RBAC roles for a project."""
    project_service = ProjectService(db)
    members = project_service.list_members(current_user, project_id)
    return [ProjectMemberRead.model_validate(m) for m in members]


@router.post("/{project_id}/members", response_model=ProjectMemberRead, status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: uuid.UUID,
    data: ProjectMemberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a registered user to project team with specified role (MAINTAINER or OWNER required)."""
    project_service = ProjectService(db)
    member = project_service.add_member(
        current_user=current_user,
        project_id=project_id,
        email=data.email,
        role=data.role
    )
    return ProjectMemberRead.model_validate(member)


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberRead)
def update_project_member_role(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ProjectMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update member role in project (OWNER required)."""
    project_service = ProjectService(db)
    updated = project_service.update_member_role(
        current_user=current_user,
        project_id=project_id,
        target_user_id=user_id,
        new_role=data.role
    )
    return ProjectMemberRead.model_validate(updated)


@router.delete("/{project_id}/members/{user_id}", response_model=MessageResponse)
def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove member from project team (MAINTAINER/OWNER required, or self-removal)."""
    project_service = ProjectService(db)
    project_service.remove_member(
        current_user=current_user,
        project_id=project_id,
        target_user_id=user_id
    )
    return MessageResponse(message="Member removed successfully.")


# -------------------------------------------------------------
# API Key Tokens / Project Credentials
# -------------------------------------------------------------
@router.post("/{project_id}/api-keys", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
def create_project_api_key(
    project_id: uuid.UUID,
    data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new scoped API Key for automation/CI (MAINTAINER or OWNER required).

    The raw key is returned ONLY once in this response.
    """
    project_service = ProjectService(db)
    api_key, raw_key = project_service.create_api_key(
        current_user=current_user,
        project_id=project_id,
        name=data.name,
        expires_in_days=data.expires_in_days,
        scopes=data.scopes
    )
    return APIKeyCreated(
        id=api_key.id,
        project_id=api_key.project_id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        raw_key=raw_key
    )


@router.get("/{project_id}/api-keys", response_model=List[APIKeyResponse])
def list_project_api_keys(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all active API keys for project (DEVELOPER or higher required). Keys are masked with prefix."""
    project_service = ProjectService(db)
    keys = project_service.list_api_keys(current_user, project_id)
    return [APIKeyResponse.model_validate(k) for k in keys]


@router.delete("/{project_id}/api-keys/{key_id}", response_model=MessageResponse)
def revoke_project_api_key(
    project_id: uuid.UUID,
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an active project API key (MAINTAINER or OWNER required)."""
    project_service = ProjectService(db)
    project_service.revoke_api_key(current_user, project_id, key_id)
    return MessageResponse(message="API key revoked successfully.")
