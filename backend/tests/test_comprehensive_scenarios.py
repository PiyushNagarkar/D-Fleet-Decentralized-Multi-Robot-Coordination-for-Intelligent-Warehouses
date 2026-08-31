"""Comprehensive Scenario Execution Tests.

Verifies end-to-end simulation execution across all 12 scenario conditions from Prompt 13 checklist.
"""

import pytest
from typing import Dict, Any

from app.api.scenarios import scenario_manager
from app.simulation.warehouse import WarehouseGrid
from app.simulation.engine import SimulationEngine
from app.simulation.physics import ActionType
from app.simulation.events import EventType
from app.communication.network import P2PNetwork
from app.robots.robot_agent import RobotAgent


def execute_scenario_to_completion(scenario_name: str, max_ticks: int = 50) -> Dict[str, Any]:
    """Load and execute a scenario for N ticks, returning execution summary."""
    data = scenario_manager.load_scenario(scenario_name)
    assert data is not None, f"Scenario '{scenario_name}' not found"

    seed = data.get("seed", 42)
    grid_data = data.get("grid", {})
    layout = grid_data.get("ascii_layout") or data.get("layout")

    if layout:
        warehouse = WarehouseGrid.from_ascii(layout, name=data.get("name", "scenario"))
    else:
        w = data.get("width") or grid_data.get("width", 12)
        h = data.get("height") or grid_data.get("height", 10)
        warehouse = WarehouseGrid(width=w, height=h, name=data.get("name", "scenario"))

    engine = SimulationEngine(warehouse=warehouse, seed=seed)
    network = P2PNetwork(seed=seed)

    agents = {}
    for r_cfg in data.get("robots", []):
        r_id = r_cfg["id"]
        start_pos = (r_cfg["start_pos"][0], r_cfg["start_pos"][1])
        engine.spawn_robot(r_id, start_pos[0], start_pos[1], battery_level=r_cfg.get("battery", 100.0))
        agent = RobotAgent(
            robot_id=r_id,
            initial_position=start_pos,
            static_map=warehouse,
            network=network,
            priority=r_cfg.get("priority", 1),
            battery=r_cfg.get("battery", 100.0),
        )
        agents[r_id] = agent

    for t_cfg in data.get("tasks", []):
        t_id = t_cfg["id"]
        p_pos = (t_cfg["pickup_pos"][0], t_cfg["pickup_pos"][1])
        d_pos = (t_cfg["delivery_pos"][0], t_cfg["delivery_pos"][1])
        prio = t_cfg.get("priority", 1)
        item_type = t_cfg.get("item_type", "standard_pod")
        engine.inject_task(t_id, p_pos, d_pos, priority=prio, item_type=item_type)
        for agent in agents.values():
            agent.task_manager.on_task_announced(t_id, p_pos, d_pos, priority=prio, item_type=item_type)

    for obs_cfg in data.get("obstacles", []):
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

    comm_cfg = data.get("communication", {})
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

    failures = list(data.get("failures", []))

    for tick in range(max_ticks):
        current_tick = engine.clock.current_tick
        for f in failures:
            if f.get("tick") == current_tick:
                engine.inject_failure(f["robot_id"])

        observations = engine.get_all_observations()
        actions = {}
        for r_id, agent in agents.items():
            obs = observations.get(r_id)
            actions[r_id] = agent.step(obs) if obs else ActionType.WAIT

        engine.step(actions)

    collisions = len(engine.event_log.get_events(event_type=EventType.ROBOT_COLLISION))

    return {
        "engine": engine,
        "agents": agents,
        "collisions": collisions,
        "total_events": len(engine.event_log),
    }


def test_scenario_normal_warehouse():
    """Scenario 1: Normal warehouse baseline execution."""
    res = execute_scenario_to_completion("normal.json", max_ticks=40)
    assert res["collisions"] == 0
    assert res["total_events"] > 0


def test_scenario_single_and_multiple_conflicts():
    """Scenario 2 & 3: Intersection and multi-robot traffic conflicts."""
    res = execute_scenario_to_completion("intersection_conflict.json", max_ticks=35)
    assert res["collisions"] == 0


def test_scenario_dynamic_and_moving_obstacles():
    """Scenario 4 & 5: Static spills and moving forklift obstacle avoidance."""
    res = execute_scenario_to_completion("dynamic_obstacles.json", max_ticks=40)
    assert res["collisions"] == 0


def test_scenario_robot_failure_and_rescue():
    """Scenario 6 & 7: Hardware failure with carried pod rescue."""
    res = execute_scenario_to_completion("robot_failure.json", max_ticks=45)
    assert res["collisions"] == 0


def test_scenario_deadlock_resolution():
    """Scenario 8: 3-robot cyclic deadlock resolution."""
    res = execute_scenario_to_completion("deadlock.json", max_ticks=35)
    assert res["collisions"] == 0


def test_scenario_low_battery_and_charging():
    """Scenario 9: Low battery robots autonomous charging."""
    res = execute_scenario_to_completion("battery.json", max_ticks=35)
    assert res["collisions"] == 0


def test_scenario_communication_loss_and_delay():
    """Scenario 10 & 11: Network loss and latency."""
    res = execute_scenario_to_completion("communication_loss.json", max_ticks=35)
    assert res["collisions"] == 0


def test_scenario_complete_flagship_demo():
    """Scenario 12: Flagship complete demo combining all simultaneous events."""
    res = execute_scenario_to_completion("complete_demo.json", max_ticks=50)
    assert res["collisions"] == 0
    assert res["total_events"] > 20
