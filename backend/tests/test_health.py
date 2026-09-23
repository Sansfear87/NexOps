import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


def test_health_check_root():
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["version"] == "0.1.0"
            assert "phase" in data

    asyncio.run(_run())


def test_health_check_v1():
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    asyncio.run(_run())
