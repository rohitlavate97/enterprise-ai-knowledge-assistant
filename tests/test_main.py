"""Tests for the main FastAPI application endpoints."""

from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check() -> None:
    """Test the health check endpoint returns 200 OK and healthy status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "healthy"}
