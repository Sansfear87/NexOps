import pytest
import asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import user, auth_account, session, project, project_member, api_key, audit_log
from app.main import app
from app.db.session import get_db

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


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(test_engine)


def test_api_key_lifecycle_and_authentication():
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Register User & Login
            reg_resp = await client.post("/api/v1/auth/register", json={
                "email": "keymaster@example.com",
                "password": "Password123!",
                "display_name": "Key Master"
            })
            assert reg_resp.status_code == 201
            token = reg_resp.json()["session_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # 2. Create Project
            proj_resp = await client.post("/api/v1/projects", headers=auth_headers, json={
                "name": "Automation Gateway",
                "slug": "auto-gateway",
                "description": "API key testing project"
            })
            assert proj_resp.status_code == 201
            project_id = proj_resp.json()["id"]

            # 3. Create API Key for Project
            key_resp = await client.post(f"/api/v1/projects/{project_id}/api-keys", headers=auth_headers, json={
                "name": "CI/CD Deployer",
                "expires_in_days": 30,
                "scopes": ["repo:read", "deploy:staging"]
            })
            assert key_resp.status_code == 201
            key_data = key_resp.json()
            raw_key = key_data["raw_key"]
            key_id = key_data["id"]

            assert raw_key.startswith("nxp_live_")
            assert key_data["name"] == "CI/CD Deployer"
            assert key_data["key_prefix"] == raw_key[:16]
            assert key_data["is_active"] is True
            assert key_data["expires_at"] is not None

            # 4. List API Keys (raw key should not be exposed in list)
            list_resp = await client.get(f"/api/v1/projects/{project_id}/api-keys", headers=auth_headers)
            assert list_resp.status_code == 200
            listed_keys = list_resp.json()
            assert len(listed_keys) == 1
            assert "raw_key" not in listed_keys[0]
            assert listed_keys[0]["key_prefix"] == raw_key[:16]

            # 5. Authenticate using X-API-Key header
            api_key_header = {"X-API-Key": raw_key}
            me_resp = await client.get("/api/v1/auth/me", headers=api_key_header)
            assert me_resp.status_code == 200
            assert me_resp.json()["email"] == "keymaster@example.com"

            # 6. Authenticate using Bearer nxp_live_...
            bearer_key_header = {"Authorization": f"Bearer {raw_key}"}
            me_resp_bearer = await client.get("/api/v1/auth/me", headers=bearer_key_header)
            assert me_resp_bearer.status_code == 200
            assert me_resp_bearer.json()["email"] == "keymaster@example.com"

            # 7. Access project using API Key
            proj_get_resp = await client.get(f"/api/v1/projects/{project_id}", headers=api_key_header)
            assert proj_get_resp.status_code == 200
            assert proj_get_resp.json()["slug"] == "auto-gateway"

            # 8. Revoke API Key
            revoke_resp = await client.delete(f"/api/v1/projects/{project_id}/api-keys/{key_id}", headers=auth_headers)
            assert revoke_resp.status_code == 200

            # 9. Verify revoked API key is rejected
            revoked_me = await client.get("/api/v1/auth/me", headers=api_key_header)
            assert revoked_me.status_code == 401

            # 10. Verify revoked key is no longer in active list
            active_list = await client.get(f"/api/v1/projects/{project_id}/api-keys", headers=auth_headers)
            assert active_list.status_code == 200
            assert len(active_list.json()) == 0

    asyncio.run(_run())
