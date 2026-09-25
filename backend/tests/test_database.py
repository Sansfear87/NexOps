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
from app.core.security import hash_password, verify_password, hash_session_token


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


def test_session_token_hashing_security(db_session):
    """Verify that raw session tokens are hashed with SHA-256 and never stored in plaintext."""
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)

    user = user_repo.create_user(email="sess_hash@example.com", display_name="Hash User")
    raw_token = "high-entropy-client-token-xyz-12345"
    expected_hash = hash_session_token(raw_token)

    session = session_repo.create_session(
        user_id=user.id,
        raw_token=raw_token,
        expires_at=utc_now() + timedelta(days=7),
        user_agent="pytest/1.0"
    )

    # Verify database holds the hash, NOT the raw token
    assert session.token_hash == expected_hash
    assert raw_token not in session.token_hash

    # Direct DB query verifies token_hash column
    stmt = select(DBSession).where(DBSession.token_hash == expected_hash)
    db_record = db_session.scalars(stmt).first()
    assert db_record is not None
    assert db_record.token_hash == expected_hash

    # Verification via raw token through repository
    active = session_repo.get_active_session(raw_token)
    assert active is not None
    assert active.user_id == user.id

    # Revoke session
    assert session_repo.revoke_session(raw_token) is True
    assert session_repo.get_active_session(raw_token) is None


def test_session_expired_behavior(db_session):
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)

    user = user_repo.create_user(email="expired@example.com", display_name="Exp User")
    token = "expired-token-999"
    past_date = utc_now() - timedelta(hours=1)

    session_repo.create_session(
        user_id=user.id,
        raw_token=token,
        expires_at=past_date
    )

    active = session_repo.get_active_session(token)
    assert active is None


def test_owner_scoped_slug_uniqueness(db_session):
    """Verify that different users CAN have identical project slugs, but a single owner cannot duplicate."""
    user_repo = UserRepository(db_session)
    proj_repo = ProjectRepository(db_session)

    user_a = user_repo.create_user(email="user_a@example.com", display_name="User Alpha")
    user_b = user_repo.create_user(email="user_b@example.com", display_name="User Beta")

    # User A creates project 'control-plane'
    proj_a = proj_repo.create_project(
        name="User A Control Plane",
        slug="control-plane",
        owner_id=user_a.id
    )
    assert proj_a.slug == "control-plane"

    # User B CAN create project with identical slug 'control-plane' (Multi-tenant scoped)
    proj_b = proj_repo.create_project(
        name="User B Control Plane",
        slug="control-plane",
        owner_id=user_b.id
    )
    assert proj_b.slug == "control-plane"
    assert proj_b.id != proj_a.id

    # User A CANNOT create a duplicate slug 'control-plane' within their own account
    with pytest.raises(IntegrityError):
        proj_a_duplicate = Project(
            name="User A Duplicate",
            slug="control-plane",
            owner_id=user_a.id
        )
        db_session.add(proj_a_duplicate)
        db_session.commit()
    db_session.rollback()


def test_project_canonical_membership_authorization(db_session):
    """Verify single canonical authorization model: access is derived from project_members."""
    user_repo = UserRepository(db_session)
    proj_repo = ProjectRepository(db_session)

    owner = user_repo.create_user(email="owner_model@example.com", display_name="Owner Model")
    member = user_repo.create_user(email="collab@example.com", display_name="Collab Model")
    stranger = user_repo.create_user(email="stranger@example.com", display_name="Stranger")

    proj = proj_repo.create_project(name="Platform", slug="platform", owner_id=owner.id)

    # Owner membership
    db_session.add(ProjectMember(project_id=proj.id, user_id=owner.id, role="OWNER"))
    # Collaborator membership
    db_session.add(ProjectMember(project_id=proj.id, user_id=member.id, role="DEVELOPER"))
    db_session.commit()

    # Owner and Member have access
    assert len(proj_repo.list_accessible_projects(owner.id)) == 1
    assert len(proj_repo.list_accessible_projects(member.id)) == 1

    # Stranger has zero access
    assert len(proj_repo.list_accessible_projects(stranger.id)) == 0


def test_project_soft_delete(db_session):
    user_repo = UserRepository(db_session)
    proj_repo = ProjectRepository(db_session)

    user = user_repo.create_user(email="del@example.com", display_name="Delete Tester")
    proj = proj_repo.create_project(name="To Delete", slug="to-delete", owner_id=user.id)

    proj_repo.soft_delete(proj)

    assert proj_repo.get_active_by_id(proj.id) is None
    assert proj_repo.get_by_owner_and_slug(user.id, "to-delete") is None


def test_cascading_deletes_on_user_removal(db_session):
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)
    auth_repo = AuthAccountRepository(db_session)

    user = user_repo.create_user(email="cascade@example.com", display_name="Cascade User")
    auth_repo.create_password_account(user.id, user.email, "hash123")
    session_repo.create_session(user.id, "cascade-tok", utc_now() + timedelta(days=1))

    db_session.delete(user)
    db_session.commit()

    stmt_acc = select(AuthAccount).where(AuthAccount.user_id == user.id)
    assert db_session.scalars(stmt_acc).first() is None

    stmt_sess = select(DBSession).where(DBSession.user_id == user.id)
    assert db_session.scalars(stmt_sess).first() is None
