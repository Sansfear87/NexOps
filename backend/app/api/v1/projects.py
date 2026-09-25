import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse, APIKeyCreate, APIKeyResponse, APIKeyCreated
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.project_service import create_project, list_user_projects, get_project, create_api_key, list_api_keys

router = APIRouter()

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await create_project(db, project_in.name, project_in.description, current_user.id)
    return project

@router.get("", response_model=List[ProjectResponse])
async def get_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    projects = await list_user_projects(db, current_user.id)
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_detail(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await get_project(db, project_id, current_user.id)
    return project

@router.post("/{project_id}/api-keys", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_new_api_key(
    project_id: uuid.UUID,
    key_in: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    api_key, raw_key = await create_api_key(db, project_id, key_in.name, current_user.id)
    response = APIKeyCreated.model_validate(api_key)
    response.raw_key = raw_key
    return response

@router.get("/{project_id}/api-keys", response_model=List[APIKeyResponse])
async def get_api_keys(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    keys = await list_api_keys(db, project_id, current_user.id)
    return keys
