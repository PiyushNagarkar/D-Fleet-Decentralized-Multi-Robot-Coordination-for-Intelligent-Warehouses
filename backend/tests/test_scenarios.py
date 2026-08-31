"""Determinism and Reproducibility Tests for All Scenario Files."""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
import pytest

from app.simulation.warehouse import WarehouseGrid
from app.simulation.engine import SimulationEngine
from app.simulation.physics import ActionType
from app.communication.network import P2PNetwork
from app.robots.robot_agent import RobotAgent
from app.api.scenarios import scenario_manager


def run_scenario_events(scenario_data: Dict[str, Any], ticks: int = 25) -> List[Dict[str, Any]]:
    """Execute scenario in headless mode and return serialized event log sequence."""
    seed = scenario_data.get("seed", 42)

    grid_data = scenario_data.get("grid", {})
    layout = grid_data.get("ascii_layout") or scenario_data.get("layout")
    if layout:
        warehouse = WarehouseGrid.from_ascii(layout, name=scenario_data.get("name", "scenario"))
    else:
        w = scenario_data.get("width") or grid_data.get("width", 12)
        h = scenario_data.get("height") or grid_data.get("height", 10)
        warehouse = WarehouseGrid(width=w, height=h, name=scenario_data.get("name", "scenario"))

    engine = SimulationEngine(warehouse=warehouse, seed=seed)
    network = P2PNetwork(seed=seed)

    # Spawn robots
    agents: Dict[str, RobotAgent] = {}
    robots_cfg = scenario_data.get("robots", [])
    for r_cfg in robots_cfg:
        r_id = r_cfg["id"]
        start_pos = (r_cfg["start_pos"][0], r_cfg["start_pos"][1])
        engine.spawn_robot(r_id, start_pos[0], start_pos[1])
        agent = RobotAgent(
            robot_id=r_id,
            initial_position=start_pos,
            static_map=warehouse,
            network=network,
            priority=r_cfg.get("priority", 1),
            battery=r_cfg.get("battery", 100.0),
        )
        agents[r_id] = agent

    # Inject tasks
    for t_cfg in scenario_data.get("tasks", []):
        t_id = t_cfg["id"]
        p_pos = (t_cfg["pickup_pos"][0], t_cfg["pickup_pos"][1])
        d_pos = (t_cfg["delivery_pos"][0], t_cfg["delivery_pos"][1])
        prio = t_cfg.get("priority", 1)
        item_type = t_cfg.get("item_type", "standard_pod")
        engine.inject_task(t_id, p_pos, d_pos, priority=prio, item_type=item_type)
        for agent in agents.values():
            agent.task_manager.on_task_announced(t_id, p_pos, d_pos, priority=prio, item_type=item_type)

    # Inject obstacles
    for obs_cfg in scenario_data.get("obstacles", []):
        engine.add_obstacle(
            x=obs_cfg["x"],
            y=obs_cfg["y"],
            start_tick=obs_cfg.get("start_tick", 0),
            duration=obs_cfg.get("duration"),
            obstacle_type=obs_cfg.get("obstacle_type", "STATIC"),
            waypoints=[(wp["x"], wp["y"]) for wp in obs_cfg.get("waypoints", [])],
            speed_ticks_per_step=obs_cfg.get("speed_ticks_per_step", 1),
            obstacle_id=obs_cfg.get("id"),
        )

    # Impairment config
    comm_cfg = scenario_data.get("communication", {})
    delay = comm_cfg.get("delay", 0)
    loss = comm_cfg.get("packet_loss", 0.0)
    jitter = comm_cfg.get("jitter", 0)
    if delay > 0 or loss > 0 or jitter > 0:
        for r1 in agents.keys():
            for r2 in agents.keys():
                if r1 != r2:
                    network.set_link_config(
                        sender=r1,
                        recipient=r2,
                        latency_ticks=delay,
                        loss_rate=loss,
                        jitter_ticks=jitter,
                    )

    failures = list(scenario_data.get("failures", []))

    # Run for N ticks
    for tick in range(ticks):
        current_tick = engine.clock.current_tick

        # Trigger scheduled failures
        for f in failures:
            if f.get("tick") == current_tick:
                engine.inject_failure(f["robot_id"])

        observations = engine.get_all_observations()
        actions = {}
        for r_id, agent in agents.items():
            obs = observations.get(r_id)
            if obs:
                actions[r_id] = agent.step(obs)
            else:
                actions[r_id] = ActionType.WAIT

        engine.step(actions)

    # Extract deterministic event log entries (excluding non-deterministic wall-clock timestamps and random UUIDs)
    event_signatures = [
        {
            "event_type": e.event_type.value,
            "tick": e.tick,
            "robot_id": e.robot_id,
            "location": list(e.location) if e.location else None,
            "payload": e.payload,
        }
        for e in engine.event_log._events
    ]
    return event_signatures


@pytest.mark.parametrize(
    "scenario_file",
    [
        "normal.json",
        "intersection_conflict.json",
        "dynamic_obstacles.json",
        "robot_failure.json",
        "deadlock.json",
        "battery.json",
        "communication_loss.json",
        "complete_demo.json",
    ],
)
def test_scenario_deterministic_reproducibility(scenario_file: str):
    """Confirm loading each scenario file twice with same seed produces identical event logs."""
    data = scenario_manager.load_scenario(scenario_file)
    assert data is not None, f"Failed to load scenario file '{scenario_file}'"

    # Run 1
    events_run1 = run_scenario_events(data, ticks=30)
    # Run 2
    events_run2 = run_scenario_events(data, ticks=30)

    # Assert byte-identical JSON serialized representations
    json1 = json.dumps(events_run1, sort_keys=True)
    json2 = json.dumps(events_run2, sort_keys=True)

    assert json1 == json2, f"Scenario '{scenario_file}' produced non-deterministic results between runs!"
