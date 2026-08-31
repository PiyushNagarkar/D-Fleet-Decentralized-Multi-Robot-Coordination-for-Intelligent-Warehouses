"""Unit tests for Space-Time Reservations and Conflict Detection."""

import pytest
from app.simulation.warehouse import WarehouseGrid
from app.robots.local_world_model import LocalWorldModel
from app.planning.reservation_planner import (
    ReservationRecord,
    ReservationTable,
    SpaceTimeAStar,
)
from app.robots.conflict_detection import (
    Conflict,
    ConflictType,
    ConflictDetector,
)


# Test 1: Vertex Conflict Detection
def test_vertex_conflict_detection():
    detector = ConflictDetector()

    # R1 intends to visit [(1, 1), (2, 1), (3, 1)] starting at tick 10
    path_r1 = [(1, 1), (2, 1), (3, 1)]
    start_tick = 10

    # Peer R2 has an existing reservation at (2, 1) at tick 11
    peer_reservations = [
        ReservationRecord(owner="R2", cell=(2, 1), time=11, created_tick=10, ttl=30),
    ]

    conflicts = detector.detect_vertex_conflicts(
        robot_id="R1",
        path=path_r1,
        start_tick=start_tick,
        peer_reservations=peer_reservations,
    )

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.VERTEX_CONFLICT
    assert conflicts[0].robot_id_1 == "R1"
    assert conflicts[0].robot_id_2 == "R2"
    assert conflicts[0].location == (2, 1)
    assert conflicts[0].time_tick == 11


# Test 2: Edge Conflict Detection (Head-On Cell Swap)
def test_edge_conflict_detection():
    detector = ConflictDetector()

    # R1: (2, 1) -> (3, 1) from tick 5 to 6
    path_r1 = [(2, 1), (3, 1)]
    start_tick_r1 = 5

    # R2: (3, 1) -> (2, 1) from tick 5 to 6
    peer_paths = {
        "R2": ([(3, 1), (2, 1)], 5),
    }

    conflicts = detector.detect_edge_conflicts(
        robot_id="R1",
        path=path_r1,
        start_tick=start_tick_r1,
        peer_paths=peer_paths,
    )

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.EDGE_CONFLICT
    assert conflicts[0].robot_id_1 == "R1"
    assert conflicts[0].robot_id_2 == "R2"
    assert conflicts[0].time_tick == 6


# Test 3: Following Conflict Detection (Tailgating in Narrow Aisle)
def test_following_conflict_detection():
    ascii_map = """
    #####
    #####
    #...#
    #####
    #####
    """
    grid = WarehouseGrid.from_ascii(ascii_map)
    detector = ConflictDetector(min_following_headway=1)

    # R1 enters narrow aisle at (1, 2) at tick 10, moves to (2, 2) at tick 11
    path_r1 = [(1, 2), (2, 2)]
    # R2 is directly ahead at (2, 2) at tick 10 (headway = 1, violating minimum safe gap)
    peer_paths = {
        "R2": ([(2, 2), (3, 2)], 10),
    }

    conflicts = detector.detect_following_conflicts(
        robot_id="R1",
        path=path_r1,
        start_tick=10,
        peer_paths=peer_paths,
        grid=grid,
    )

    assert len(conflicts) >= 1
    for c in conflicts:
        assert c.conflict_type == ConflictType.FOLLOWING_CONFLICT
        assert c.robot_id_1 == "R1"
        assert c.robot_id_2 == "R2"


# Test 4: Future Conflict Detection (Converging at Shared Cell at Future Tick)
def test_future_conflict_detection():
    detector = ConflictDetector()
    current_tick = 5

    # R1 trajectory reaches (5, 5) at tick 15
    path_r1 = [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)]
    start_tick_r1 = 11  # (5, 5) is at 11 + 4 = 15

    # R2 trajectory reaches (5, 5) from the north at tick 15
    path_r2 = [(5, 1), (5, 2), (5, 3), (5, 4), (5, 5)]
    start_tick_r2 = 11

    peer_paths = {
        "R2": (path_r2, start_tick_r2),
    }

    conflicts = detector.detect_future_conflicts(
        robot_id="R1",
        path=path_r1,
        start_tick=start_tick_r1,
        peer_paths=peer_paths,
        current_tick=current_tick,
    )

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.FUTURE_CONFLICT
    assert conflicts[0].location == (5, 5)
    assert conflicts[0].time_tick == 15
    assert conflicts[0].details["ticks_ahead"] == 10


# Test 5: Narrow-Aisle Head-On Conflict Detection
def test_narrow_aisle_head_on_conflict():
    ascii_map = """
    #######
    #######
    #.###.#
    #.....#
    #.###.#
    #######
    """
    grid = WarehouseGrid.from_ascii(ascii_map)
    detector = ConflictDetector()

    # R1 traverses row 3 West to East: (1, 3) -> (2, 3) -> (3, 3) -> (4, 3) -> (5, 3)
    path_r1 = [(1, 3), (2, 3), (3, 3), (4, 3), (5, 3)]
    # R2 traverses row 3 East to West: (5, 3) -> (4, 3) -> (3, 3) -> (2, 3) -> (1, 3)
    path_r2 = [(5, 3), (4, 3), (3, 3), (2, 3), (1, 3)]

    peer_paths = {
        "R2": (path_r2, 10),
    }

    conflicts = detector.detect_narrow_aisle_head_on_conflicts(
        robot_id="R1",
        path=path_r1,
        start_tick=10,
        peer_paths=peer_paths,
        grid=grid,
    )

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.NARROW_AISLE_HEAD_ON
    assert conflicts[0].robot_id_1 == "R1"
    assert conflicts[0].robot_id_2 == "R2"


# Test 6: Expired Reservation Safety Invariant Test
def test_expired_reservation_safety_invariant():
    """Safety Invariant: Expired reservations cannot block robots."""
    ascii_map = """
    #####
    #...#
    #####
    """
    grid = WarehouseGrid.from_ascii(ascii_map)
    table = ReservationTable()
    planner = SpaceTimeAStar(warehouse=grid)

    # Add an expired reservation at (2, 1) created at tick 0 with TTL = 10
    # Current simulation tick is 20 (created_tick 0 + TTL 10 < 20 => expired)
    table.add_reservation(
        ReservationRecord(
            owner="R_Ghost",
            cell=(2, 1),
            time=21,
            created_tick=0,
            ttl=10,
        )
    )

    current_tick = 20

    # Reservation table should report (2, 1) as NOT reserved at tick 21 because it is expired
    assert table.is_reserved(cell=(2, 1), time=21, current_tick=current_tick) is False

    # Space-time path planner successfully plans through (2, 1) without being blocked
    start = (1, 1)
    goal = (3, 1)
    path = planner.plan_space_time_path(
        start=start,
        goal=goal,
        start_tick=current_tick,
        reservation_table=table,
        current_tick=current_tick,
    )

    assert path is not None
    assert path == [(1, 1), (2, 1), (3, 1)]
