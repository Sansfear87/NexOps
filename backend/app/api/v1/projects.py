from typing import List
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead
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
