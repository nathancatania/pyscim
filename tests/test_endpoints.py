import pytest
from httpx import ASGITransport, AsyncClient
from src.scim.main import app
from src.scim.config import settings


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["environment"] == settings.environment


@pytest.mark.asyncio
async def test_service_provider_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"{settings.api_prefix}/ServiceProviderConfig")
        assert response.status_code == 200
        data = response.json()
        assert "schemas" in data
        assert data["patch"]["supported"] is True
        assert data["bulk"]["supported"] is True


@pytest.mark.asyncio
async def test_schemas_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"{settings.api_prefix}/Schemas")
        assert response.status_code == 200
        data = response.json()
        assert "schemas" in data
        assert data["totalResults"] >= 3  # User, Group, Enterprise User


@pytest.mark.asyncio
async def test_user_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"{settings.api_prefix}/Schemas/urn:ietf:params:scim:schemas:core:2.0:User"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "urn:ietf:params:scim:schemas:core:2.0:User"
        assert data["name"] == "User"
        assert "attributes" in data