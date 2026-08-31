"""FastAPI REST API Routes for D-Fleet Simulation Environment."""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from .simulation import simulation_service
from .scenarios import scenario_manager
from .websocket import telemetry_hub


router = APIRouter(prefix="/api")


# Request schemas
class ObstacleCreateRequest(BaseModel):
    obstacle_id: str = Field(..., json_schema_extra={"example": "spill_1"})
    x: int = Field(..., json_schema_extra={"example": 3})
    y: int = Field(..., json_schema_extra={"example": 3})
    duration: int = Field(default=20, json_schema_extra={"example": 20})


class FailureCreateRequest(BaseModel):
    reason: str = Field(default="simulated_hardware_fault", json_schema_extra={"example": "battery_depletion"})


class SpeedChangeRequest(BaseModel):
    speed: float = Field(default=1.0, json_schema_extra={"example": 2.0})


# Simulation Control Routes
@router.get("/simulation/status")
async def get_simulation_status():
    return simulation_service.get_status()


@router.post("/simulation/start")
async def start_simulation():
    await simulation_service.start()
    return {"status": "started", "simulation_status": simulation_service.status}


@router.post("/simulation/pause")
async def pause_simulation():
    simulation_service.pause()
    await telemetry_hub.broadcast(simulation_service.get_telemetry_snapshot())
    return {"status": "paused", "simulation_status": simulation_service.status}


@router.post("/simulation/reset")
async def reset_simulation():
    simulation_service.reset()
    await telemetry_hub.broadcast(simulation_service.get_telemetry_snapshot())
    return {"status": "reset", "simulation_status": simulation_service.status}


@router.post("/simulation/step")
async def step_simulation():
    snapshot = simulation_service.step_once()
    await telemetry_hub.broadcast(snapshot)
    return {"status": "stepped", "tick": snapshot.get("tick", 0)}


@router.post("/simulation/speed")
async def set_simulation_speed(req: SpeedChangeRequest):
    simulation_service.set_speed(req.speed)
    return {"status": "speed_updated", "speed": simulation_service.speed}


# Robot Query Routes
@router.get("/robots")
async def get_robots():
    return simulation_service.get_robots()


@router.get("/robots/{robot_id}")
async def get_robot(robot_id: str):
    robot = simulation_service.get_robot(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    return robot


# Task Query Routes
@router.get("/tasks")
async def get_tasks():
    return simulation_service.get_tasks()


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    task = simulation_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task


# Metrics and Event Routes
@router.get("/metrics")
async def get_metrics():
    return simulation_service.get_telemetry_snapshot().get("metrics", {})


@router.get("/events")
async def get_events():
    return simulation_service.get_events()


# Scenario Management Routes
@router.get("/scenarios")
async def list_scenarios():
    return scenario_manager.list_scenarios()


@router.post("/scenarios/{scenario_id}/load")
async def load_scenario(scenario_id: str):
    data = scenario_manager.load_scenario(scenario_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    simulation_service.load_scenario_data(data)
    await telemetry_hub.broadcast(simulation_service.get_telemetry_snapshot())
    return {
        "status": "loaded",
        "scenario_id": scenario_id,
        "robots_count": len(simulation_service.agents),
        "tasks_count": len(simulation_service.tasks),
    }


# Injection Routes
@router.post("/failures/{robot_id}")
async def inject_failure(robot_id: str, req: Optional[FailureCreateRequest] = None):
    success = simulation_service.inject_robot_failure(robot_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    await telemetry_hub.broadcast(simulation_service.get_telemetry_snapshot())
    return {"status": "failure_injected", "robot_id": robot_id}


@router.post("/obstacles")
async def inject_obstacle(req: ObstacleCreateRequest):
    success = simulation_service.inject_obstacle(
        obstacle_id=req.obstacle_id,
        x=req.x,
        y=req.y,
        duration=req.duration,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to inject obstacle")
    await telemetry_hub.broadcast(simulation_service.get_telemetry_snapshot())
    return {
        "status": "obstacle_injected",
        "obstacle_id": req.obstacle_id,
        "position": [req.x, req.y],
        "duration": req.duration,
    }
