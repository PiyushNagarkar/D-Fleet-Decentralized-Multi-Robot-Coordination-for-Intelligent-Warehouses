"""Unit tests for Decentralized Task Bidding and Allocation System."""

import pytest
from app.simulation.warehouse import WarehouseGrid
from app.robots.state import RobotState, RobotStatus
from app.robots.local_world_model import LocalWorldModel
from app.tasks.task import Task, TaskStatus
from app.tasks.bidder import TaskBidder
from app.tasks.task_manager import LocalTaskManager


def test_deterministic_bidding_and_winner():
    """Test 1: Given fixed inputs, bidder produces deterministic bids and winner."""
    grid = WarehouseGrid(width=20, height=20)
    bidder = TaskBidder()

    task = Task(
        task_id="task_1",
        pickup_location=(5, 5),
        delivery_location=(15, 15),
        priority=2,
        spawn_tick=10,
    )

    # Robot 1 is close to pickup at (4, 5), full battery
    r1_state = RobotState(robot_id="R1", position=(4, 5), battery=100.0)
    r1_wm = LocalWorldModel(robot_id="R1", static_map=grid)

    # Robot 2 is farther away at (12, 12), full battery
    r2_state = RobotState(robot_id="R2", position=(12, 12), battery=100.0)
    r2_wm = LocalWorldModel(robot_id="R2", static_map=grid)

    bid_r1 = bidder.compute_bid(r1_state, r1_wm, task, current_tick=10)
    bid_r2 = bidder.compute_bid(r2_state, r2_wm, task, current_tick=10)

    assert bid_r1 is not None
    assert bid_r2 is not None
    # R1 is closer, so cost is lower and bid is higher
    assert bid_r1 > bid_r2

    winner = bidder.evaluate_winner({"R1": bid_r1, "R2": bid_r2})
    assert winner == "R1"


def test_tie_breaking_by_lowest_robot_id():
    """Test 2: When bids are identical, tie is broken deterministically by lowest robot_id."""
    bidder = TaskBidder()

    # Identical bids
    bids = {
        "R_Charlie": -25.0,
        "R_Alice": -25.0,
        "R_Bob": -25.0,
    }

    winner = bidder.evaluate_winner(bids)
    assert winner == "R_Alice"  # 'R_Alice' < 'R_Bob' < 'R_Charlie'


def test_losing_bidder_returns_to_idle_and_bids_next():
    """Test 3: Robot that loses a bid returns/stays in IDLE and can win subsequent tasks."""
    grid = WarehouseGrid(width=20, height=20)
    tm_r2 = LocalTaskManager(robot_id="R2")

    r2_state = RobotState(robot_id="R2", position=(10, 10), battery=100.0, status=RobotStatus.IDLE)
    r2_wm = LocalWorldModel(robot_id="R2", static_map=grid)

    # Task 1 announced (close to R1, far from R2)
    t1 = tm_r2.on_task_announced(
        task_id="task_A",
        pickup_location=(1, 1),
        delivery_location=(5, 5),
    )
    bid_r2_t1 = tm_r2.compute_and_record_my_bid("task_A", r2_state, r2_wm, current_tick=1)
    tm_r2.record_peer_bid("task_A", "R1", bid_r2_t1 + 10.0)  # R1 bids higher

    # R2 evaluates auction for Task 1
    winner_t1 = tm_r2.evaluate_auction("task_A")
    assert winner_t1 == "R1"
    # R2 does NOT claim task 1
    assert tm_r2.active_task_id is None
    assert r2_state.status == RobotStatus.IDLE

    # Task 2 announced (very close to R2 at (10, 10))
    t2 = tm_r2.on_task_announced(
        task_id="task_B",
        pickup_location=(10, 11),
        delivery_location=(12, 12),
    )
    bid_r2_t2 = tm_r2.compute_and_record_my_bid("task_B", r2_state, r2_wm, current_tick=5)
    tm_r2.record_peer_bid("task_B", "R1", bid_r2_t2 - 15.0)  # R2 bids higher this time

    winner_t2 = tm_r2.evaluate_auction("task_B")
    assert winner_t2 == "R2"

    # R2 successfully claims Task 2
    claim_success = tm_r2.claim_task("task_B", "R2", winning_bid=bid_r2_t2, current_tick=5)
    assert claim_success is True
    assert tm_r2.active_task_id == "task_B"
    r2_state.transition_to(RobotStatus.MOVING_TO_PICKUP)
    assert r2_state.status == RobotStatus.MOVING_TO_PICKUP


def test_near_simultaneous_claim_conflict_resolution():
    """Test 4: Simulate two robots attempting near-simultaneous claims on the same task.
    Deterministic conflict resolution ensures no double-assignment."""
    grid = WarehouseGrid(width=20, height=20)

    tm_r1 = LocalTaskManager(robot_id="R1")
    tm_r2 = LocalTaskManager(robot_id="R2")

    task_id = "task_contested"
    pickup = (8, 8)
    delivery = (18, 18)

    # Both robots know the task
    tm_r1.on_task_announced(task_id, pickup, delivery)
    tm_r2.on_task_announced(task_id, pickup, delivery)

    # R1 and R2 both bid
    r1_bid = -20.0
    r2_bid = -25.0

    # Both claim the task locally around the same tick
    tm_r1.claim_task(task_id, "R1", winning_bid=r1_bid, current_tick=10)
    tm_r2.claim_task(task_id, "R2", winning_bid=r2_bid, current_tick=10)

    assert tm_r1.active_task_id == task_id
    assert tm_r2.active_task_id == task_id

    # Messages arrive:
    # R2 receives R1's claim broadcast
    r2_holds_claim = tm_r2.handle_peer_claim(
        task_id=task_id,
        claiming_robot_id="R1",
        claiming_bid=r1_bid,
        claim_tick=10,
    )
    # R2 has lower bid (-25.0 < -20.0), so R2 must back off
    assert r2_holds_claim is False
    assert tm_r2.active_task_id is None
    assert tm_r2.known_tasks[task_id].assigned_robot_id == "R1"

    # R1 receives R2's claim broadcast
    r1_holds_claim = tm_r1.handle_peer_claim(
        task_id=task_id,
        claiming_robot_id="R2",
        claiming_bid=r2_bid,
        claim_tick=10,
    )
    # R1 has higher bid (-20.0 > -25.0), so R1 retains claim
    assert r1_holds_claim is True
    assert tm_r1.active_task_id == task_id
    assert tm_r1.known_tasks[task_id].assigned_robot_id == "R1"


def test_task_lifecycle_transitions():
    """Test 5: Full task lifecycle state transitions."""
    tm = LocalTaskManager(robot_id="R1")
    t = tm.on_task_announced("task_100", (2, 2), (8, 8))
    assert t.status == TaskStatus.BIDDING

    assert tm.claim_task("task_100", "R1", winning_bid=10.0, current_tick=1) is True
    assert t.status == TaskStatus.CLAIMED

    tm.mark_going_to_pickup("task_100")
    assert t.status == TaskStatus.GOING_TO_PICKUP

    tm.mark_picked_up("task_100")
    assert t.status == TaskStatus.PICKED_UP

    tm.mark_going_to_delivery("task_100")
    assert t.status == TaskStatus.GOING_TO_DELIVERY

    tm.mark_delivered("task_100", current_tick=25)
    assert t.status == TaskStatus.DELIVERED
    assert t.completed_tick == 25
    assert tm.active_task_id is None
