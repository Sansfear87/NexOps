from typing import Optional, List
import uuid
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.models.project_member import ProjectMember
from app.db.constants import ProjectRole
from app.db.repositories.base import BaseRepository


class ProjectMemberRepository(BaseRepository[ProjectMember]):
    def __init__(self, db: Session):
        super().__init__(ProjectMember, db)

    def get_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ProjectMember]:
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        )
        return self.db.scalars(stmt).first()

    def list_members(self, project_id: uuid.UUID) -> List[ProjectMember]:
        stmt = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def add_member(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = ProjectRole.DEVELOPER.value
    ) -> ProjectMember:
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=role
        )
        return self.create(member)

    def update_role(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        new_role: str
    ) -> Optional[ProjectMember]:
        member = self.get_member(project_id, user_id)
        if member:
            member.role = new_role
            self.db.add(member)
            self.db.commit()
            self.db.refresh(member)
            return member
        return None

    def remove_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        member = self.get_member(project_id, user_id)
        if member:
            self.db.delete(member)
            self.db.commit()
            return True
        return False

    def count_owners(self, project_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(ProjectMember.id))
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.role == ProjectRole.OWNER.value
            )
        )
        return self.db.scalar(stmt) or 0
