"""Comprehensive Unit Tests for D-Fleet Simulation Engine (Environment Layer)."""

import ast
from pathlib import Path
import pytest

from app.simulation.clock import SimulationClock
from app.simulation.warehouse import (
    WarehouseGrid,
    CellType,
    grid_to_world,
    world_to_grid,
)
from app.simulation.obstacle_manager import (
    ObstacleManager,
    ObstacleType,
)
from app.simulation.physics import (
    PhysicsEngine,
    ActionType,
    Direction,
    PhysicalStatus,
)
from app.simulation.events import EventType, EventLog
from app.simulation.engine import SimulationEngine


# 1. Grid Loading & Coordinate Conversion Tests
def test_grid_loads_from_ascii():
    ascii_map = """
    #####
    #C.P#
    #.I.#
    #D..#
    #####
    """
    grid = WarehouseGrid.from_ascii(ascii_map, name="test_ascii")
    assert grid.width == 5
    assert grid.height == 5
    assert grid.get_cell(0, 0) == CellType.WALL
    assert grid.get_cell(1, 1) == CellType.CHARGING
    assert grid.get_cell(3, 1) == CellType.PICKUP
    assert grid.get_cell(2, 2) == CellType.INTERSECTION
    assert grid.get_cell(1, 3) == CellType.DELIVERY
    assert grid.is_traversable(1, 1) is True
    assert grid.is_traversable(0, 0) is False
    assert len(grid.charging_stations) == 1
    assert len(grid.pickup_stations) == 1
    assert len(grid.delivery_stations) == 1
    assert len(grid.intersections) == 1


def test_grid_loads_from_json(tmp_path):
    scenario_path = Path(__file__).resolve().parent.parent.parent / "scenarios" / "small_warehouse.json"
    grid = WarehouseGrid.from_json(scenario_path)
    assert grid.width == 10
    assert grid.height == 10
    assert len(grid.pickup_stations) == 2
    assert len(grid.delivery_stations) == 2
    assert len(grid.charging_stations) == 2
    assert len(grid.intersections) == 2
    assert grid.is_traversable(1, 1) is True
    assert grid.is_traversable(0, 0) is False


def test_coordinate_conversion():
    cell_size = 2.0
    gx, gy = 5, 8
    world_x, world_y, world_z = grid_to_world(gx, gy, cell_size=cell_size)
    assert world_x == 10.0
    assert world_y == 0.0
    assert world_z == 16.0

    recovered_gx, recovered_gy = world_to_grid(world_x, world_z, cell_size=cell_size)
    assert (recovered_gx, recovered_gy) == (gx, gy)


# 2. Obstacle Lifecycle & Movement Tests
def test_obstacles_appear_and_expire_on_schedule():
    mgr = ObstacleManager()
    mgr.add_obstacle(
        x=3,
        y=4,
        start_tick=5,
        duration=10,
        obstacle_type=ObstacleType.STATIC,
        obstacle_id="spill_1",
    )

    # Before start_tick
    spawned, moved, expired = mgr.tick(4)
    assert len(mgr.get_active_obstacle_positions(4)) == 0
    assert not mgr.is_obstacle_at(3, 4, 4)

    # At start_tick (tick 5)
    spawned, moved, expired = mgr.tick(5)
    assert len(spawned) == 1
    assert spawned[0].obstacle_id == "spill_1"
    assert mgr.is_obstacle_at(3, 4, 5)

    # During active duration (tick 10)
    spawned, moved, expired = mgr.tick(10)
    assert mgr.is_obstacle_at(3, 4, 10)

    # At expiration (tick 15 = start 5 + duration 10)
    spawned, moved, expired = mgr.tick(15)
    assert len(expired) == 1
    assert not mgr.is_obstacle_at(3, 4, 15)


def test_moving_obstacle_waypoints():
    mgr = ObstacleManager()
    waypoints = [(1, 1), (2, 1), (3, 1)]
    mgr.add_obstacle(
        x=1,
        y=1,
        start_tick=0,
        obstacle_type=ObstacleType.MOVING,
        waypoints=waypoints,
        speed_ticks_per_step=1,
        obstacle_id="forklift_1",
    )

    mgr.tick(0)
    assert (mgr.get_obstacle("forklift_1").x, mgr.get_obstacle("forklift_1").y) == (1, 1)

    mgr.tick(1)
    assert (mgr.get_obstacle("forklift_1").x, mgr.get_obstacle("forklift_1").y) == (2, 1)

    mgr.tick(2)
    assert (mgr.get_obstacle("forklift_1").x, mgr.get_obstacle("forklift_1").y) == (3, 1)

    # Cycles back
    mgr.tick(3)
    assert (mgr.get_obstacle("forklift_1").x, mgr.get_obstacle("forklift_1").y) == (1, 1)


# 3. Deterministic Clock Tests
def test_clock_determinism():
    clock1 = SimulationClock(dt=0.1, seed=12345)
    clock2 = SimulationClock(dt=0.1, seed=12345)

    random_floats_1 = []
    random_floats_2 = []

    for _ in range(20):
        clock1.tick()
        clock2.tick()
        random_floats_1.append(clock1.rng.random())
        random_floats_2.append(clock2.rng.random())

    assert clock1.current_tick == 20
    assert clock2.current_tick == 20
    assert clock1.current_time_s == pytest.approx(2.0)
    assert random_floats_1 == random_floats_2

    # Reset with same seed
    clock1.reset(seed=12345)
    reset_floats = [clock1.rng.random() for _ in range(20)]
    assert reset_floats == random_floats_1


# 4. Physics, Movement & Interactions Tests
def test_physics_movement_and_wall_blocking():
    ascii_map = """
    #####
    #.C.#
    #...#
    #####
    """
    grid = WarehouseGrid.from_ascii(ascii_map)
    engine = SimulationEngine(warehouse=grid)

    r1 = engine.spawn_robot("robot_1", x=1, y=1)
    assert (r1.x, r1.y) == (1, 1)

    # Move East (1,1) -> (2,1)
    obs, results = engine.step({"robot_1": ActionType.MOVE_EAST})
    assert results["robot_1"].success is True
    assert (r1.x, r1.y) == (2, 1)
    assert r1.heading == Direction.EAST

    # Move North into Wall (2,1) -> (2,0 is Wall)
    obs, results = engine.step({"robot_1": ActionType.MOVE_NORTH})
    assert results["robot_1"].success is False
    assert (r1.x, r1.y) == (2, 1)  # Robot does not penetrate wall


def test_robot_robot_collision_prevention_at_physics_layer():
    ascii_map = """
    #####
    #...#
    #####
    """
    grid = WarehouseGrid.from_ascii(ascii_map)
    engine = SimulationEngine(warehouse=grid)

    engine.spawn_robot("robot_1", x=1, y=1)
    engine.spawn_robot("robot_2", x=2, y=1)

    # Robot 1 attempts to move East into Robot 2's cell
    obs, results = engine.step({"robot_1": ActionType.MOVE_EAST, "robot_2": ActionType.WAIT})
    assert results["robot_1"].success is False
    assert results["robot_1"].collision_with_robot_id == "robot_2"
    assert (engine.physics.robots["robot_1"].x, engine.physics.robots["robot_1"].y) == (1, 1)


def test_robot_charging():
    ascii_map = """
    #####
    #C..#
    #####
    """
    grid = WarehouseGrid.from_ascii(ascii_map)
    engine = SimulationEngine(warehouse=grid)

    r1 = engine.spawn_robot("robot_1", x=1, y=1, battery_level=50.0)
    engine.physics.charge_rate_per_tick = 10.0

    obs, results = engine.step({"robot_1": ActionType.CHARGE})
    assert results["robot_1"].success is True
    assert r1.battery_level == pytest.approx(60.0)
    assert r1.status == PhysicalStatus.CHARGING


def test_pickup_and_delivery():
    ascii_map = """
    #####
    #P.D#
    #####
    """
    grid = WarehouseGrid.from_ascii(ascii_map)
    engine = SimulationEngine(warehouse=grid)

    r1 = engine.spawn_robot("robot_1", x=1, y=1)

    # Pickup at P
    obs, results = engine.step({"robot_1": ActionType.PICKUP}, item_ids={"robot_1": "sku_999"})
    assert results["robot_1"].success is True
    assert r1.is_carrying_pod is True
    assert r1.carried_item_id == "sku_999"

    # Move to D (1,1) -> (2,1) -> (3,1)
    engine.step({"robot_1": ActionType.MOVE_EAST})
    engine.step({"robot_1": ActionType.MOVE_EAST})
    assert (r1.x, r1.y) == (3, 1)

    # Dropoff at D
    obs, results = engine.step({"robot_1": ActionType.DROPOFF})
    assert results["robot_1"].success is True
    assert r1.is_carrying_pod is False
    assert r1.carried_item_id is None


def test_failure_injection_and_recovery():
    ascii_map = """
    #####
    #...#
    #####
    """
    grid = WarehouseGrid.from_ascii(ascii_map)
    engine = SimulationEngine(warehouse=grid)
    r1 = engine.spawn_robot("robot_1", x=1, y=1)

    # Inject failure
    assert engine.inject_failure("robot_1", reason="Motor Jam") is True
    assert r1.is_failed is True
    assert r1.status == PhysicalStatus.FAILED

    # Action while failed should fail
    obs, results = engine.step({"robot_1": ActionType.MOVE_EAST})
    assert results["robot_1"].success is False
    assert (r1.x, r1.y) == (1, 1)

    # Recover
    assert engine.recover_robot("robot_1") is True
    assert r1.is_failed is False

    obs, results = engine.step({"robot_1": ActionType.MOVE_EAST})
    assert results["robot_1"].success is True
    assert (r1.x, r1.y) == (2, 1)


# 5. ZERO Robot-Decision Code Import Invariant Test
def test_simulation_module_has_zero_decision_imports():
    """Verify that backend/simulation and backend/app/simulation have NO imports
    from agents, robots, or planning modules (Strict Decentralization Rule)."""
    forbidden_terms = [
        "robots",
        "planning",
        "agents",
        "app.agents",
        "cbs",
        "centralized",
        "joint_planner",
    ]

    simulation_dir = Path(__file__).resolve().parent.parent / "app" / "simulation"
    py_files = list(simulation_dir.glob("*.py"))

    for py_file in py_files:
        with open(py_file, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_terms:
                        assert forbidden not in alias.name.lower(), (
                            f"Illegal import '{alias.name}' found in simulation module {py_file.name}!"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_terms:
                        assert forbidden not in node.module.lower(), (
                            f"Illegal from-import module '{node.module}' found in simulation module {py_file.name}!"
                        )
