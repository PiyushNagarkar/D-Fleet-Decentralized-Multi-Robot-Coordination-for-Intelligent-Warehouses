import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "D-Fleet"
    assert data["mode"] == "decentralized-simulation"


@pytest.mark.asyncio
async def test_simulation_status_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/simulation/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("idle", "IDLE", "RUNNING", "PAUSED")
    assert "version" in data
    assert data["active_agents"] >= 0
    assert "grid_dimensions" in data
    assert data["metadata"]["engine"] == "decentralized-asyncio"
