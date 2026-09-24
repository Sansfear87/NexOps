import pytest
import asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db

# Isolated test DB with StaticPool so all connections share the same in-memory tables
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)


def test_auth_and_project_lifecycle():
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Register User A
            reg_resp = await client.post("/api/v1/auth/register", json={
                "email": "user_a@example.com",
                "password": "Password123!",
                "display_name": "User Alpha"
            })
            assert reg_resp.status_code == 201
            reg_data = reg_resp.json()
            token_a = reg_data["session_token"]
            user_a_id = reg_data["user"]["id"]
            assert reg_data["user"]["email"] == "user_a@example.com"

            # 2. Check /me with Token A
            headers_a = {"Authorization": f"Bearer {token_a}"}
            me_resp = await client.get("/api/v1/auth/me", headers=headers_a)
            assert me_resp.status_code == 200
            assert me_resp.json()["display_name"] == "User Alpha"

            # 3. Create Project as User A
            proj_resp = await client.post("/api/v1/projects", headers=headers_a, json={
                "name": "Alpha Platform",
                "slug": "alpha-platform",
                "description": "Internal test project"
            })
            assert proj_resp.status_code == 201
            proj_a = proj_resp.json()
            proj_a_id = proj_a["id"]
            assert proj_a["slug"] == "alpha-platform"
            assert proj_a["owner_id"] == user_a_id

            # 4. List projects for User A
            list_resp = await client.get("/api/v1/projects", headers=headers_a)
            assert list_resp.status_code == 200
            assert len(list_resp.json()) == 1

            # 5. Register User B
            reg_b_resp = await client.post("/api/v1/auth/register", json={
                "email": "user_b@example.com",
                "password": "Password123!",
                "display_name": "User Bravo"
            })
            assert reg_b_resp.status_code == 201
            token_b = reg_b_resp.json()["session_token"]
            headers_b = {"Authorization": f"Bearer {token_b}"}

            # 6. Verify User B has 0 projects
            list_b_resp = await client.get("/api/v1/projects", headers=headers_b)
            assert list_b_resp.status_code == 200
            assert len(list_b_resp.json()) == 0

            # 7. CROSS-USER ACCESS DENIAL: User B attempts to access User A's project
            denial_resp = await client.get(f"/api/v1/projects/{proj_a_id}", headers=headers_b)
            assert denial_resp.status_code == 403
            assert "Access denied" in denial_resp.json()["detail"]

            # 8. UNAUTHENTICATED ACCESS DENIAL
            unauth_resp = await client.get(f"/api/v1/projects/{proj_a_id}")
            assert unauth_resp.status_code == 401

            # 9. User A retrieves their own project
            get_resp = await client.get(f"/api/v1/projects/{proj_a_id}", headers=headers_a)
            assert get_resp.status_code == 200
            assert get_resp.json()["name"] == "Alpha Platform"

            # 10. Delete project as User A
            del_resp = await client.delete(f"/api/v1/projects/{proj_a_id}", headers=headers_a)
            assert del_resp.status_code == 200

            # 11. Verify deleted project is no longer returned
            after_del_resp = await client.get(f"/api/v1/projects/{proj_a_id}", headers=headers_a)
            assert after_del_resp.status_code == 404

            # 12. Logout User A
            logout_resp = await client.post("/api/v1/auth/logout", headers=headers_a)
            assert logout_resp.status_code == 200

            # 13. Verify logged-out token is rejected
            logged_out_me = await client.get("/api/v1/auth/me", headers=headers_a)
            assert logged_out_me.status_code == 401

    asyncio.run(_run())


def test_auth_validation_errors():
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Duplicate email registration error
            await client.post("/api/v1/auth/register", json={
                "email": "testdup@example.com",
                "password": "Password123!",
                "display_name": "First"
            })
            dup_resp = await client.post("/api/v1/auth/register", json={
                "email": "testdup@example.com",
                "password": "Password123!",
                "display_name": "Second"
            })
            assert dup_resp.status_code == 400

            # Invalid login credentials error
            bad_login = await client.post("/api/v1/auth/login", json={
                "email": "testdup@example.com",
                "password": "WrongPassword!"
            })
            assert bad_login.status_code == 401

    asyncio.run(_run())
