"""Unit tests for D* Lite Incremental Path Planner."""

import pytest
import math
from app.simulation.warehouse import WarehouseGrid, CellType
from app.robots.local_world_model import LocalWorldModel
from app.robots.network import PeerMessage
from app.planning.dstar_lite import DStarLite, INF


def test_baseline_path_around_static_walls():
    """Test 1: Plan baseline path navigating around warehouse shelving/walls."""
    ascii_map = """
    #######
    #S.#.G#
    #.###.#
    #.....#
    #######
    """
    grid = WarehouseGrid.from_ascii(ascii_map)
    wm = LocalWorldModel(robot_id="R1", static_map=grid)
    planner = DStarLite.from_world_model(wm)

    start = (1, 1)
    goal = (5, 1)

    path = planner.plan(start=start, goal=goal)

    assert len(path) > 0
    assert path[0] == start
    assert path[-1] == goal

    # Verify no path point is on a wall
    for pt in path:
        assert grid.is_traversable(pt[0], pt[1]) is True

    # Expected path goes around the wall block via y=3
    assert (1, 3) in path or (5, 3) in path or (3, 3) in path


def test_incremental_replan_on_midpath_obstacle():
    """Test 2: Inject an obstacle mid-path and verify incremental repair."""
    ascii_map = """
    #######
    #S...G#
    #.....#
    #######
    """
    grid = WarehouseGrid.from_ascii(ascii_map)
    wm = LocalWorldModel(robot_id="R1", static_map=grid)
    planner = DStarLite.from_world_model(wm)

    start = (1, 1)
    goal = (5, 1)

    # Initial straight line path along y=1: (1,1) -> (2,1) -> (3,1) -> (4,1) -> (5,1)
    initial_path = planner.plan(start=start, goal=goal)
    assert initial_path == [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1)]

    # Robot moves from (1, 1) to (2, 1)
    current_pos = (2, 1)

    # A dynamic obstacle appears directly in front at (3, 1)
    # Robot receives peer alert or local observation updating world model
    alert_msg = PeerMessage(
        sender_id="R2",
        recipient_id="R1",
        message_type="OBSTACLE_ALERT",
        payload={"obstacle_id": "spill_1", "position": [3, 1]},
        send_tick=5,
        delivery_tick=5,
    )
    wm.update_from_peer_message(alert_msg, current_tick=5)

    # Sync planner with updated world model
    changed = planner.sync_with_world_model(wm, current_tick=5)
    assert (3, 1) in changed
    assert planner.cost_grid[(3, 1)] == INF

    # Replan without creating a new planner instance
    repaired_path = planner.replan(new_start=current_pos)

    assert len(repaired_path) > 0
    assert repaired_path[0] == current_pos
    assert repaired_path[-1] == goal
    # Path must now detour around (3, 1) via row y=2
    assert (3, 1) not in repaired_path
    assert (2, 2) in repaired_path or (3, 2) in repaired_path


def test_replan_efficiency_versus_scratch_plan():
    """Test 3: Confirm replanning cost (nodes expanded) is significantly lower
    than a full re-plan from scratch on a large grid."""
    grid_size = 40
    grid = WarehouseGrid(width=grid_size, height=grid_size)
    wm = LocalWorldModel(robot_id="R1", static_map=grid)
    planner = DStarLite.from_world_model(wm)

    start = (2, 2)
    goal = (35, 35)

    # Initial plan
    path = planner.plan(start=start, goal=goal)
    initial_nodes_expanded = planner.nodes_expanded
    assert len(path) > 0

    # Advance robot partway along path
    new_start = path[10]

    # Inject a local obstacle near the current position
    obstacle_pos = path[12]
    planner.update_cell_cost(obstacle_pos, INF)

    # Measure incremental replan node expansions
    planner.nodes_expanded = 0
    repaired_path = planner.replan(new_start=new_start)
    incremental_nodes_expanded = planner.nodes_expanded

    # Fresh scratch planner for comparison
    fresh_wm = LocalWorldModel(robot_id="R1", static_map=grid)
    fresh_planner = DStarLite.from_world_model(fresh_wm)
    fresh_planner.update_cell_cost(obstacle_pos, INF)
    scratch_path = fresh_planner.plan(start=new_start, goal=goal)
    scratch_nodes_expanded = fresh_planner.nodes_expanded

    # Assertions
    assert len(repaired_path) > 0
    assert obstacle_pos not in repaired_path
    assert incremental_nodes_expanded < scratch_nodes_expanded, (
        f"Incremental repair expanded {incremental_nodes_expanded} nodes, "
        f"which should be less than scratch plan ({scratch_nodes_expanded} nodes)!"
    )


def test_path_safety_invariants():
    """Test 4: Generated path never traverses walls or obstacles known to the robot's local model."""
    ascii_map = """
    ##########
    #S.......#
    #.#.####.#
    #.#....#.#
    #...##.#.#
    #.#..G.#.#
    #.#....#.#
    #........#
    ##########
    """
    grid = WarehouseGrid.from_ascii(ascii_map)
    wm = LocalWorldModel(robot_id="R1", static_map=grid)

    # Block the left corridor at (1, 4)
    alert = PeerMessage(
        sender_id="R3",
        recipient_id="R1",
        message_type="OBSTACLE_ALERT",
        payload={"obstacle_id": "box_stack", "position": [1, 4]},
        send_tick=1,
        delivery_tick=1,
    )
    wm.update_from_peer_message(alert, current_tick=1)

    planner = DStarLite.from_world_model(wm, current_tick=1)
    start = (1, 1)
    goal = (5, 5)

    path = planner.plan(start=start, goal=goal)

    assert len(path) > 0
    assert path[0] == start
    assert path[-1] == goal

    for pos in path:
        # 1. Never on a wall
        assert grid.is_traversable(pos[0], pos[1]) is True
        # 2. Never on known obstacle
        assert pos != (1, 4)
        # 3. Step distance is valid (Manhattan adjacent)
    for i in range(len(path) - 1):
        p1, p2 = path[i], path[i + 1]
        dist = abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
        assert dist == 1
