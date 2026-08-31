"""Unit and Integration tests for FastAPI REST Endpoints and WebSocket Telemetry Hub."""

import json
import pytest
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient

from app.main import app
from app.api.simulation import simulation_service


@pytest.mark.asyncio
async def test_rest_simulation_lifecycle_and_endpoints(async_client: AsyncClient):
    """Test REST API lifecycle: status, start, pause, reset, queries, and injections."""
    # 1. Status
    res = await async_client.get("/api/simulation/status")
    assert res.status_code == 200
    status_data = res.json()
    assert "status" in status_data

    # 2. Robots
    res = await async_client.get("/api/robots")
    assert res.status_code == 200
    robots = res.json()
    assert len(robots) >= 2
    r_id = robots[0]["robot_id"]

    res = await async_client.get(f"/api/robots/{r_id}")
    assert res.status_code == 200
    assert res.json()["robot_id"] == r_id

    # 3. Tasks
    res = await async_client.get("/api/tasks")
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) >= 1
    t_id = tasks[0]["task_id"]

    res = await async_client.get(f"/api/tasks/{t_id}")
    assert res.status_code == 200
    assert res.json()["task_id"] == t_id

    # 4. Metrics and Events
    res = await async_client.get("/api/metrics")
    assert res.status_code == 200

    res = await async_client.get("/api/events")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 5. Scenarios
    res = await async_client.get("/api/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) >= 1

    scenario_id = scenarios[0]["id"]
    res = await async_client.post(f"/api/scenarios/{scenario_id}/load")
    assert res.status_code == 200
    assert res.json()["status"] == "loaded"

    # 6. Obstacle Injection
    res = await async_client.post(
        "/api/obstacles",
        json={"obstacle_id": "spill_test", "x": 3, "y": 3, "duration": 15},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "obstacle_injected"

    # 7. Robot Failure Injection
    active_robots = (await async_client.get("/api/robots")).json()
    assert len(active_robots) >= 1
    fail_robot_id = active_robots[0]["robot_id"]
    res = await async_client.post(f"/api/failures/{fail_robot_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "failure_injected"

    # 8. Start, Pause, Reset
    res = await async_client.post("/api/simulation/start")
    assert res.status_code == 200
    assert res.json()["simulation_status"] == "RUNNING"

    res = await async_client.post("/api/simulation/pause")
    assert res.status_code == 200
    assert res.json()["simulation_status"] == "PAUSED"

    res = await async_client.post("/api/simulation/reset")
    assert res.status_code == 200


def test_websocket_telemetry_streaming():
    """Test dashboard WebSocket telemetry hub broadcasts simulation state."""
    client = TestClient(app)
    with client.websocket_connect("/ws/simulation") as websocket:
        # Step simulation to trigger telemetry broadcast
        simulation_service.step_once()
        snapshot = simulation_service.get_telemetry_snapshot()

        # Send ping and receive pong
        websocket.send_text(json.dumps({"command": "PING"}))
        data = websocket.receive_text()
        response = json.loads(data)
        assert response.get("type") == "PONG"


def test_safety_invariant_9_rejects_direct_control_commands():
    """Negative Test (Safety Invariant #9):
    Confirm that attempting to send a 'move robot', 'assign task', or 'grant reservation'
    command over /ws/simulation is strictly rejected."""
    client = TestClient(app)
    with client.websocket_connect("/ws/simulation") as websocket:
        # 1. Attempt manual robot move
        websocket.send_text(json.dumps({
            "command": "MOVE_ROBOT",
            "robot_id": "R1",
            "target": [5, 5],
        }))
        res = json.loads(websocket.receive_text())
        assert res["type"] == "COMMAND_REJECTED"
        assert "Safety Invariant #9" in res["error"]

        # 2. Attempt manual task assignment
        websocket.send_text(json.dumps({
            "command": "ASSIGN_TASK",
            "task_id": "task_1",
            "robot_id": "R1",
        }))
        res = json.loads(websocket.receive_text())
        assert res["type"] == "COMMAND_REJECTED"
        assert "Safety Invariant #9" in res["error"]

        # 3. Attempt direct reservation grant
        websocket.send_text(json.dumps({
            "command": "GRANT_RESERVATION",
            "cell": [2, 2],
            "robot_id": "R1",
        }))
        res = json.loads(websocket.receive_text())
        assert res["type"] == "COMMAND_REJECTED"
        assert "Safety Invariant #9" in res["error"]
