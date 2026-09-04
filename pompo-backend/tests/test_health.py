"""Health endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_endpoint(client: AsyncClient) -> None:
    """Liveness probe should always return alive."""
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["alive"] is True


@pytest.mark.asyncio
async def test_health_endpoint_returns_components(client: AsyncClient) -> None:
    """Health endpoint should return all subsystem components."""
    response = await client.get("/api/v1/health")
    data = response.json()
    assert "components" in data
    assert "application" in data["components"]
    assert "database" in data["components"]
    assert "redis" in data["components"]
    assert "celery" in data["components"]
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_readiness_endpoint_returns_checks(client: AsyncClient) -> None:
    """Readiness probe should return individual check results."""
    response = await client.get("/api/v1/health/ready")
    data = response.json()
    assert "ready" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]


@pytest.mark.asyncio
async def test_request_id_header_present(client: AsyncClient) -> None:
    """Every response should include an X-Request-ID header."""
    response = await client.get("/api/v1/health/live")
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_debug_schema_routes_are_available_in_testing(client: AsyncClient) -> None:
    """Testing keeps OpenAPI so contract tests can call app.openapi()."""
    docs = await client.get("/docs")
    schema = await client.get("/openapi.json")
    assert docs.status_code == 200
    assert schema.status_code == 200


@pytest.mark.asyncio
async def test_custom_request_id_preserved(client: AsyncClient) -> None:
    """Custom X-Request-ID should be preserved in the response."""
    custom_id = "test-request-id-12345"
    response = await client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": custom_id},
    )
    assert response.headers.get("x-request-id") == custom_id
