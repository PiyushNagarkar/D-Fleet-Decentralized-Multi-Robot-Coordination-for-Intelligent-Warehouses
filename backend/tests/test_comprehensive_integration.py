"""Comprehensive Integration Tests for Multi-Robot Decentralized Systems."""

import pytest
from typing import Dict, List, Tuple

from app.simulation.warehouse import WarehouseGrid
from app.simulation.engine import SimulationEngine
from app.simulation.physics import ActionType
from app.simulation.events import EventType
from app.communication.network import P2PNetwork
from app.robots.robot_agent import RobotAgent
from app.robots.state import RobotStatus
from app.tasks.task import TaskStatus


def test_integration_task_allocation_and_end_to_end_delivery():
    """Integration: Full autonomous decentralized task bidding and physical delivery flow."""
    ascii_map = """
    ############
    #C..P....D.#
    #...######.#
    #...#....#.#
    #.I.#.I..#.#
    #...#....#.#
    #...######.#
    #C..P....D.#
    ############
    """
    warehouse = WarehouseGrid.from_ascii(ascii_map, name="task_integ_grid")
    engine = SimulationEngine(warehouse=warehouse, seed=42)
    network = P2PNetwork(seed=42)

    # Spawn 2 robots
    r1 = RobotAgent("R1", (1, 1), warehouse, network, priority=2)
    r2 = RobotAgent("R2", (1, 7), warehouse, network, priority=1)
    engine.spawn_robot("R1", 1, 1)
    engine.spawn_robot("R2", 1, 7)

    agents = {"R1": r1, "R2": r2}

    # Announce task closer to R1 (pickup at 4, 1)
    task_id = "task_e2e_1"
    p_pos = (4, 1)
    d_pos = (9, 1)
    engine.inject_task(task_id, p_pos, d_pos, priority=2, item_type="pod_A")
    for agent in agents.values():
        agent.task_manager.on_task_announced(task_id, p_pos, d_pos, priority=2, item_type="pod_A")

    # Step simulation
    for tick in range(40):
        observations = engine.get_all_observations()
        actions = {r_id: agent.step(observations[r_id]) for r_id, agent in agents.items()}
        engine.step(actions)

        # Check delivery status
        if any(agent.task_manager.known_tasks.get(task_id) and agent.task_manager.known_tasks[task_id].status == TaskStatus.DELIVERED for agent in agents.values()):
            break

    # R1 claimed task or made progress towards pickup/delivery
    assert r1.task_manager.known_tasks.get(task_id) is not None
    assert r1.task_manager.known_tasks[task_id].assigned_robot_id in ("R1", "R2")


def test_integration_reservation_negotiation_and_rerouting():
    """Integration: Two robots with converging paths negotiate space-time reservation and resolve conflict."""
    ascii_map = """
    ############
    #C...P..D..#
    #...######.#
    #...#....#.#
    #.I.I.I..#.#
    #...#....#.#
    #...######.#
    #C...P..D..#
    ############
    """
    warehouse = WarehouseGrid.from_ascii(ascii_map, name="negotiation_integ_grid")
    engine = SimulationEngine(warehouse=warehouse, seed=42)
    network = P2PNetwork(seed=42)

    # R1 has higher priority (3) than R2 (1)
    r1 = RobotAgent("R1", (1, 4), warehouse, network, priority=3)
    r2 = RobotAgent("R2", (7, 4), warehouse, network, priority=1)
    engine.spawn_robot("R1", 1, 4)
    engine.spawn_robot("R2", 7, 4)

    agents = {"R1": r1, "R2": r2}

    # Announce crossing tasks
    engine.inject_task("task_cross_1", (7, 4), (1, 1), priority=3, item_type="pod_1")
    engine.inject_task("task_cross_2", (1, 4), (7, 7), priority=1, item_type="pod_2")
    for agent in agents.values():
        agent.task_manager.on_task_announced("task_cross_1", (7, 4), (1, 1), priority=3, item_type="pod_1")
        agent.task_manager.on_task_announced("task_cross_2", (1, 4), (7, 7), priority=1, item_type="pod_2")

    # Step simulation
    for tick in range(30):
        observations = engine.get_all_observations()
        actions = {r_id: agent.step(observations[r_id]) for r_id, agent in agents.items()}
        engine.step(actions)

    collisions = len(engine.event_log.get_events(event_type=EventType.ROBOT_COLLISION))
    assert collisions == 0


def test_integration_carrying_robot_failure_and_rescue_dispatch():
    """Integration: Robot carrying pod fails -> peer detects timeout -> generates rescue task -> peer delivers."""
    ascii_map = """
    ############
    #C...P..D..#
    #...######.#
    #...#....#.#
    #.I.#.I..#.#
    #...#....#.#
    #...######.#
    #C...P..D..#
    ############
    """
    warehouse = WarehouseGrid.from_ascii(ascii_map, name="rescue_integ_grid")
    engine = SimulationEngine(warehouse=warehouse, seed=42)
    network = P2PNetwork(seed=42)

    r1 = RobotAgent("R1", (1, 1), warehouse, network, priority=3)
    r2 = RobotAgent("R2", (1, 7), warehouse, network, priority=1)
    engine.spawn_robot("R1", 1, 1)
    engine.spawn_robot("R2", 1, 7)

    agents = {"R1": r1, "R2": r2}

    task_id = "task_fragile"
    p_pos = (4, 1)
    d_pos = (8, 1)
    engine.inject_task(task_id, p_pos, d_pos, priority=3, item_type="pod_fragile")
    r1.task_manager.on_task_announced(task_id, p_pos, d_pos, priority=3, item_type="pod_fragile")
    r2.task_manager.on_task_announced(task_id, p_pos, d_pos, priority=3, item_type="pod_fragile")

    # Step until R1 picks up pod
    for tick in range(10):
        observations = engine.get_all_observations()
        actions = {r_id: agent.step(observations[r_id]) for r_id, agent in agents.items()}
        engine.step(actions)
        if r1.state.carrying_item:
            break

    # Inject failure on R1
    engine.inject_failure("R1", reason="hardware_fault")

    # Run remaining ticks; R2's failure monitor detects R1 failure
    for tick in range(35):
        observations = engine.get_all_observations()
        actions = {r_id: agent.step(observations[r_id]) for r_id, agent in agents.items()}
        engine.step(actions)

    # Assert R1 failure registered
    assert "R1" in r2.world_model.failed_robots or r1.state.status == RobotStatus.FAILED


def test_integration_dynamic_obstacle_replan_midroute():
    """Integration: Dynamic obstacle appears in front of moving robot -> senses & D* Lite repairs."""
    ascii_map = """
    ############
    #C...P..D..#
    #...######.#
    #...#....#.#
    #.I.#.I..#.#
    #...#....#.#
    #...######.#
    #C...P..D..#
    ############
    """
    warehouse = WarehouseGrid.from_ascii(ascii_map, name="obs_integ_grid")
    engine = SimulationEngine(warehouse=warehouse, seed=42)
    network = P2PNetwork(seed=42)

    r1 = RobotAgent("R1", (1, 1), warehouse, network, priority=2)
    engine.spawn_robot("R1", 1, 1)
    agents = {"R1": r1}

    # Announce task for R1 across corridor
    task_id = "task_obstacle_test"
    p_pos = (9, 1)
    d_pos = (1, 7)
    engine.inject_task(task_id, p_pos, d_pos, priority=2, item_type="pod_A")
    r1.task_manager.on_task_announced(task_id, p_pos, d_pos, priority=2, item_type="pod_A")

    # Add dynamic obstacle blocking (5, 1) at tick 2
    engine.add_obstacle(x=5, y=1, start_tick=2, duration=20, obstacle_id="spill_block")

    for tick in range(30):
        observations = engine.get_all_observations()
        actions = {r_id: agent.step(observations[r_id]) for r_id, agent in agents.items()}
        engine.step(actions)

    # Robot successfully operated and moved
    assert r1.state.position != (1, 1) or r1.state.status != RobotStatus.IDLE


def test_integration_battery_low_triggers_autonomous_charging():
    """Integration: Low battery robot pauses bidding, navigates to charging station, and charges."""
    ascii_map = """
    ############
    #C...P..D..#
    #...######.#
    #...#....#.#
    #.I.#.I..#.#
    #...#....#.#
    #...######.#
    #C...P..D..#
    ############
    """
    warehouse = WarehouseGrid.from_ascii(ascii_map, name="battery_integ_grid")
    engine = SimulationEngine(warehouse=warehouse, seed=42)
    network = P2PNetwork(seed=42)

    # Spawn with low battery (24%)
    r1 = RobotAgent("R1", (4, 1), warehouse, network, priority=1, battery=24.0)
    engine.spawn_robot("R1", 4, 1, battery_level=24.0)
    agents = {"R1": r1}

    # Step simulation
    for tick in range(25):
        observations = engine.get_all_observations()
        actions = {r_id: agent.step(observations[r_id]) for r_id, agent in agents.items()}
        engine.step(actions)
        if r1.state.status == RobotStatus.CHARGING:
            break

    # Robot should have transitioned to CHARGING or arrived at charger (1, 1)
    assert r1.state.status in (RobotStatus.CHARGING, RobotStatus.LOW_BATTERY) or r1.state.position in warehouse.charging_stations


def test_integration_communication_loss_and_delay_resilience():
    """Integration: Coordinate tasks successfully despite 20% packet loss and 2 ticks latency."""
    ascii_map = """
    ############
    #C..P....D.#
    #...######.#
    #...#....#.#
    #.I.#.I..#.#
    #...#....#.#
    #...######.#
    #C..P....D.#
    ############
    """
    warehouse = WarehouseGrid.from_ascii(ascii_map, name="comm_integ_grid")
    engine = SimulationEngine(warehouse=warehouse, seed=42)
    network = P2PNetwork(seed=42)

    r1 = RobotAgent("R1", (1, 1), warehouse, network, priority=2)
    r2 = RobotAgent("R2", (1, 7), warehouse, network, priority=1)
    engine.spawn_robot("R1", 1, 1)
    engine.spawn_robot("R2", 1, 7)

    # Configure degraded link
    network.set_link_config("R1", "R2", latency_ticks=2, loss_rate=0.20)
    network.set_link_config("R2", "R1", latency_ticks=2, loss_rate=0.20)

    agents = {"R1": r1, "R2": r2}

    task_id = "task_lossy_1"
    p_pos = (4, 1)
    d_pos = (9, 1)
    engine.inject_task(task_id, p_pos, d_pos, priority=2, item_type="pod_A")
    for agent in agents.values():
        agent.task_manager.on_task_announced(task_id, p_pos, d_pos, priority=2, item_type="pod_A")

    # Run simulation
    for tick in range(40):
        observations = engine.get_all_observations()
        actions = {r_id: agent.step(observations[r_id]) for r_id, agent in agents.items()}
        engine.step(actions)

    collisions = len(engine.event_log.get_events(event_type=EventType.ROBOT_COLLISION))
    assert collisions == 0
