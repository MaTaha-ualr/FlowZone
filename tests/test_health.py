"""Tests for health check endpoints."""
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["version"] == "0.2.1"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_detailed(client):
    response = await client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert "model_router" in data
    assert "budget" in data
    assert "active_sessions" in data


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "FlowZone API"
