import os
import uuid
from datetime import timedelta
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.db.base import Base, utc_now
from app.db.models.user import User
from app.db.models.auth_account import AuthAccount
from app.db.models.session import Session as DBSession
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.models.audit_log import AuditLog
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.auth_account_repository import AuthAccountRepository
from app.db.repositories.session_repository import SessionRepository
from app.db.repositories.project_repository import ProjectRepository
from app.core.security import hash_password, verify_password


@pytest.fixture
def db_session():
    """Create isolated in-memory SQLite database for unit testing."""
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(test_engine)


def test_user_creation_and_retrieval(db_session):
    repo = UserRepository(db_session)
    user = repo.create_user(
        email="dev@example.com",
        display_name="Dev Tester"
    )
    assert user.id is not None
    assert user.email == "dev@example.com"
    assert user.display_name == "Dev Tester"
    assert user.is_active is True
    assert user.created_at is not None

    fetched = repo.get_by_email("dev@example.com")
    assert fetched is not None
    assert fetched.id == user.id


def test_duplicate_email_rejection(db_session):
    repo = UserRepository(db_session)
    repo.create_user(email="duplicate@example.com", display_name="User 1")
    
    with pytest.raises(IntegrityError):
        user2 = User(
            email="duplicate@example.com",
            display_name="User 2"
        )
        db_session.add(user2)
        db_session.commit()
    db_session.rollback()


def test_auth_account_uniqueness(db_session):
    user_repo = UserRepository(db_session)
    auth_repo = AuthAccountRepository(db_session)
    
    user1 = user_repo.create_user(email="u1@example.com", display_name="U1")
    user2 = user_repo.create_user(email="u2@example.com", display_name="U2")

    pwd_hash = hash_password("secretpassword123")
    auth_repo.create_password_account(user1.id, "u1@example.com", pwd_hash)

    # Attempt duplicate provider + provider_user_id
    with pytest.raises(IntegrityError):
        acc = AuthAccount(
            user_id=user2.id,
            provider="password",
            provider_user_id="u1@example.com",
            password_hash=pwd_hash
        )
        db_session.add(acc)
        db_session.commit()
    db_session.rollback()


def test_session_lifecycle_and_revocation(db_session):
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)

    user = user_repo.create_user(email="sess@example.com", display_name="Session User")
    token = "secure-random-token-12345"
    expires = utc_now() + timedelta(days=7)

    session = session_repo.create_session(
        user_id=user.id,
        session_token=token,
        expires_at=expires,
        user_agent="pytest/1.0"
    )
    assert session.id is not None
    assert session.revoked_at is None

    # Retrieve active session
    active = session_repo.get_active_session(token)
    assert active is not None
    assert active.user_id == user.id

    # Revoke session
    revoked = session_repo.revoke_session(token)
    assert revoked is True

    # Confirm no longer active
    active_after = session_repo.get_active_session(token)
    assert active_after is None


def test_session_expired_behavior(db_session):
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)

    user = user_repo.create_user(email="expired@example.com", display_name="Exp User")
    token = "expired-token-999"
    # Set expires_at in the past
    past_date = utc_now() - timedelta(hours=1)

    session_repo.create_session(
        user_id=user.id,
        session_token=token,
        expires_at=past_date
    )

    active = session_repo.get_active_session(token)
    assert active is None


def test_project_creation_and_membership(db_session):
    user_repo = UserRepository(db_session)
    proj_repo = ProjectRepository(db_session)

    user = user_repo.create_user(email="owner@example.com", display_name="Project Owner")
    proj = proj_repo.create_project(
        name="NexOps Control Plane",
        slug="nexops-control-plane",
        owner_id=user.id,
        description="Core DevOps pipeline"
    )

    assert proj.id is not None
    assert proj.owner_id == user.id
    assert proj.is_archived is False

    # Add project member
    dev_user = user_repo.create_user(email="dev2@example.com", display_name="Developer")
    member = ProjectMember(
        project_id=proj.id,
        user_id=dev_user.id,
        role="DEVELOPER"
    )
    db_session.add(member)
    db_session.commit()

    # List accessible projects for dev_user
    accessible = proj_repo.list_accessible_projects(dev_user.id)
    assert len(accessible) == 1
    assert accessible[0].id == proj.id


def test_project_soft_delete(db_session):
    user_repo = UserRepository(db_session)
    proj_repo = ProjectRepository(db_session)

    user = user_repo.create_user(email="del@example.com", display_name="Delete Tester")
    proj = proj_repo.create_project(name="To Delete", slug="to-delete", owner_id=user.id)

    proj_repo.soft_delete(proj)

    # Should not be returned by get_active_by_id or get_by_slug
    assert proj_repo.get_active_by_id(proj.id) is None
    assert proj_repo.get_by_slug("to-delete") is None


def test_cascading_deletes_on_user_removal(db_session):
    """Verify that removing a user cascades to their sessions and auth accounts."""
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)
    auth_repo = AuthAccountRepository(db_session)

    user = user_repo.create_user(email="cascade@example.com", display_name="Cascade User")
    auth_repo.create_password_account(user.id, user.email, "hash123")
    session_repo.create_session(user.id, "cascade-tok", utc_now() + timedelta(days=1))

    # Delete user directly
    db_session.delete(user)
    db_session.commit()

    # Verify sessions and auth_accounts were deleted
    stmt_acc = select(AuthAccount).where(AuthAccount.user_id == user.id)
    assert db_session.scalars(stmt_acc).first() is None

    stmt_sess = select(DBSession).where(DBSession.user_id == user.id)
    assert db_session.scalars(stmt_sess).first() is None
