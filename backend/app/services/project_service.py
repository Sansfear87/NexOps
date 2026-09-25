import uuid
import secrets
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.project import Project, Membership
from app.models.api_key import APIKey
from app.core.security import hash_password

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

async def create_project(db: AsyncSession, name: str, description: str | None, owner_id: uuid.UUID) -> Project:
    slug = slugify(name)
    stmt = select(Project).where(Project.slug == slug)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        slug = f"{slug}-{secrets.token_hex(4)}"

    project = Project(
        name=name,
        slug=slug,
        description=description,
        owner_id=owner_id
    )
    db.add(project)
    await db.flush()
    
    membership = Membership(
        user_id=owner_id,
        project_id=project.id,
        role="owner"
    )
    db.add(membership)
    await db.commit()
    await db.refresh(project)
    return project

async def list_user_projects(db: AsyncSession, user_id: uuid.UUID):
    stmt = select(Project).join(Membership, Project.id == Membership.project_id).where(Membership.user_id == user_id)
    res = await db.execute(stmt)
    return res.scalars().all()

async def get_project(db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID) -> Project:
    stmt = select(Project).join(Membership, Project.id == Membership.project_id).where(
        Project.id == project_id, Membership.user_id == user_id
    )
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    return project

async def create_api_key(db: AsyncSession, project_id: uuid.UUID, name: str, user_id: uuid.UUID):
    stmt = select(Membership).where(Membership.project_id == project_id, Membership.user_id == user_id)
    res = await db.execute(stmt)
    membership = res.scalar_one_or_none()
    if not membership or membership.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    raw_key = secrets.token_urlsafe(32)
    key_hash = hash_password(raw_key)
    key_prefix = raw_key[:8]

    api_key = APIKey(
        project_id=project_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    return api_key, raw_key

async def list_api_keys(db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID):
    await get_project(db, project_id, user_id)
    stmt = select(APIKey).where(APIKey.project_id == project_id)
    res = await db.execute(stmt)
    return res.scalars().all()
