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


def test_project_members_and_rbac_enforcement():
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Register Owner
            owner_reg = await client.post("/api/v1/auth/register", json={
                "email": "owner@example.com",
                "password": "Password123!",
                "display_name": "Project Owner"
            })
            assert owner_reg.status_code == 201
            owner_token = owner_reg.json()["session_token"]
            owner_id = owner_reg.json()["user"]["id"]
            owner_headers = {"Authorization": f"Bearer {owner_token}"}

            # 2. Register Developer
            dev_reg = await client.post("/api/v1/auth/register", json={
                "email": "dev@example.com",
                "password": "Password123!",
                "display_name": "Junior Developer"
            })
            assert dev_reg.status_code == 201
            dev_token = dev_reg.json()["session_token"]
            dev_id = dev_reg.json()["user"]["id"]
            dev_headers = {"Authorization": f"Bearer {dev_token}"}

            # 3. Create Project as Owner
            proj_resp = await client.post("/api/v1/projects", headers=owner_headers, json={
                "name": "Team Service",
                "slug": "team-service",
                "description": "Multi-user project"
            })
            assert proj_resp.status_code == 201
            project_id = proj_resp.json()["id"]

            # 4. Check initial members (Owner should automatically be listed with role OWNER)
            members_resp = await client.get(f"/api/v1/projects/{project_id}/members", headers=owner_headers)
            assert members_resp.status_code == 200
            members = members_resp.json()
            assert len(members) == 1
            assert members[0]["role"] == "OWNER"
            assert members[0]["user_id"] == owner_id

            # 5. Developer cannot invite members (Developer has no access yet -> 403)
            dev_add_attempt = await client.post(f"/api/v1/projects/{project_id}/members", headers=dev_headers, json={
                "email": "stranger@example.com",
                "role": "DEVELOPER"
            })
            assert dev_add_attempt.status_code == 403

            # 6. Owner invites Developer with DEVELOPER role
            add_dev_resp = await client.post(f"/api/v1/projects/{project_id}/members", headers=owner_headers, json={
                "email": "dev@example.com",
                "role": "DEVELOPER"
            })
            assert add_dev_resp.status_code == 201
            assert add_dev_resp.json()["role"] == "DEVELOPER"
            assert add_dev_resp.json()["user_id"] == dev_id

            # 7. Developer can now access the project
            dev_get_proj = await client.get(f"/api/v1/projects/{project_id}", headers=dev_headers)
            assert dev_get_proj.status_code == 200

            # 8. Developer cannot create API keys (Requires MAINTAINER or OWNER -> 403)
            dev_key_attempt = await client.post(f"/api/v1/projects/{project_id}/api-keys", headers=dev_headers, json={
                "name": "Unauthorized Key"
            })
            assert dev_key_attempt.status_code == 403
            assert "Insufficient permissions" in dev_key_attempt.json()["detail"]

            # 9. Developer cannot delete project (Requires OWNER -> 403)
            dev_del_attempt = await client.delete(f"/api/v1/projects/{project_id}", headers=dev_headers)
            assert dev_del_attempt.status_code == 403

            # 10. Owner promotes Developer to MAINTAINER
            promote_resp = await client.patch(f"/api/v1/projects/{project_id}/members/{dev_id}", headers=owner_headers, json={
                "role": "MAINTAINER"
            })
            assert promote_resp.status_code == 200
            assert promote_resp.json()["role"] == "MAINTAINER"

            # 11. Developer (now Maintainer) can create an API key
            maintainer_key_resp = await client.post(f"/api/v1/projects/{project_id}/api-keys", headers=dev_headers, json={
                "name": "Maintainer Automation Key"
            })
            assert maintainer_key_resp.status_code == 201
            assert maintainer_key_resp.json()["raw_key"].startswith("nxp_live_")

            # 12. Guard: Cannot demote the last project owner
            demote_owner_attempt = await client.patch(f"/api/v1/projects/{project_id}/members/{owner_id}", headers=owner_headers, json={
                "role": "DEVELOPER"
            })
            assert demote_owner_attempt.status_code == 400
            assert "Cannot demote the last project owner" in demote_owner_attempt.json()["detail"]

            # 13. Guard: Cannot remove the sole owner
            remove_owner_attempt = await client.delete(f"/api/v1/projects/{project_id}/members/{owner_id}", headers=owner_headers)
            assert remove_owner_attempt.status_code == 400

            # 14. Owner removes Developer
            remove_dev_resp = await client.delete(f"/api/v1/projects/{project_id}/members/{dev_id}", headers=owner_headers)
            assert remove_dev_resp.status_code == 200

            # 15. Removed developer can no longer access the project
            dev_access_after = await client.get(f"/api/v1/projects/{project_id}", headers=dev_headers)
            assert dev_access_after.status_code == 403

    asyncio.run(_run())
