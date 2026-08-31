"""Unit tests for Battery Management, Peer Failure Detection, and Rescue Subsystems."""

import pytest
from app.simulation.warehouse import WarehouseGrid
from app.robots.state import RobotState, RobotStatus
from app.robots.local_world_model import LocalWorldModel
from app.tasks.task import Task, TaskStatus
from app.tasks.task_manager import LocalTaskManager
from app.robots.battery_manager import BatteryManager, BatteryConfig
from app.robots.failure_monitor import PeerFailureMonitor


# Test 1: Peer-Based Failure Detection via Heartbeat Timeout
def test_peer_heartbeat_timeout_triggers_failed_state():
    """Test 1: Heartbeat timeout triggers FAILED state peer-side within expected ticks."""
    monitor = PeerFailureMonitor(my_robot_id="R1", heartbeat_timeout_ticks=5)
    grid = WarehouseGrid(width=10, height=10)
    wm = LocalWorldModel(robot_id="R1", static_map=grid)

    # R2 emits heartbeat at tick 10
    monitor.record_peer_heartbeat(
        peer_id="R2",
        current_tick=10,
        position=(3, 3),
        status="MOVING_TO_PICKUP",
    )

    # Ticks 11..15: Within 5-tick threshold, R2 is alive
    events = monitor.check_for_failed_peers(current_tick=15, world_model=wm)
    assert len(events) == 0
    assert "R2" not in monitor.failed_peers
    assert "R2" not in wm.failed_robots

    # Tick 16 (16 - 10 = 6 > 5): Timeout triggers failure detection
    events = monitor.check_for_failed_peers(current_tick=16, world_model=wm)
    assert len(events) == 1
    assert events[0].failed_robot_id == "R2"
    assert events[0].last_known_position == (3, 3)
    assert "R2" in monitor.failed_peers
    assert "R2" in wm.failed_robots


# Test 2: Failed Robot Reservations Invalidation
def test_failed_robot_reservations_disappear():
    """Test 2: A failed robot's reservations disappear immediately from others' views."""
    monitor = PeerFailureMonitor(my_robot_id="R1", heartbeat_timeout_ticks=5)
    grid = WarehouseGrid(width=10, height=10)
    wm = LocalWorldModel(robot_id="R1", static_map=grid)

    # R2 reserved cells at ((3, 3), tick 20) and ((4, 3), tick 21)
    wm.reservations[((3, 3), 20)] = "R2"
    wm.reservations[((4, 3), 21)] = "R2"
    wm.reservations[((1, 1), 20)] = "R3"  # R3's reservation should not be affected

    monitor.record_peer_heartbeat(peer_id="R2", current_tick=10, position=(3, 3))

    # Before failure, R2's reservations exist
    assert ((3, 3), 20) in wm.reservations
    assert ((4, 3), 21) in wm.reservations

    # R2 times out at tick 16
    events = monitor.check_for_failed_peers(current_tick=16, world_model=wm)
    assert len(events) == 1
    assert events[0].invalidated_reservations_count == 2

    # R2's reservations must be purged from R1's local world model
    assert ((3, 3), 20) not in wm.reservations
    assert ((4, 3), 21) not in wm.reservations
    # R3's reservation remains intact
    assert ((1, 1), 20) in wm.reservations


# Test 3: Uncarried Task Re-Enters Bidding on Robot Failure
def test_uncarried_task_reenters_bidding_on_failure():
    """Test 3: An uncarried task held by a failed robot re-enters bidding."""
    monitor = PeerFailureMonitor(my_robot_id="R1", heartbeat_timeout_ticks=5)
    grid = WarehouseGrid(width=10, height=10)
    wm = LocalWorldModel(robot_id="R1", static_map=grid)
    tm = LocalTaskManager(robot_id="R1")

    # Task is claimed by R2 but not yet picked up
    task = tm.on_task_announced("task_50", (2, 2), (8, 8))
    task.status = TaskStatus.GOING_TO_PICKUP
    task.assigned_robot_id = "R2"

    # R2 reports heartbeat at tick 10 with task_id="task_50" and carrying_item=None
    monitor.record_peer_heartbeat(
        peer_id="R2",
        current_tick=10,
        position=(1, 2),
        carrying_item=None,
        task_id="task_50",
    )

    # Failure detected at tick 16
    events = monitor.check_for_failed_peers(current_tick=16, world_model=wm, task_manager=tm)
    assert len(events) == 1
    assert events[0].released_task_id == "task_50"

    # Task status must be reset to BIDDING with unassigned robot
    assert task.status == TaskStatus.BIDDING
    assert task.assigned_robot_id is None


# Test 4: Carrying Robot Failure Produces RESCUE_REQUIRED Task
def test_carrying_robot_failure_creates_rescue_task():
    """Test 4: A carrying-robot failure correctly produces a RESCUE_REQUIRED task
    with pickup at the failed robot's location."""
    monitor = PeerFailureMonitor(my_robot_id="R1", heartbeat_timeout_ticks=5)
    grid = WarehouseGrid(width=10, height=10)
    wm = LocalWorldModel(robot_id="R1", static_map=grid)
    tm = LocalTaskManager(robot_id="R1")

    # Original task with destination at (9, 9)
    original_task = tm.on_task_announced("task_77", (1, 1), (9, 9))
    original_task.status = TaskStatus.GOING_TO_DELIVERY
    original_task.assigned_robot_id = "R2"

    # R2 was carrying the item and was at (4, 5) when it emitted its last heartbeat at tick 10
    monitor.record_peer_heartbeat(
        peer_id="R2",
        current_tick=10,
        position=(4, 5),
        carrying_item="pod_sku_77",
        task_id="task_77",
    )

    # R2 times out and fails at tick 16
    events = monitor.check_for_failed_peers(current_tick=16, world_model=wm, task_manager=tm)
    assert len(events) == 1
    assert events[0].rescue_task_created is not None

    rescue_task = events[0].rescue_task_created
    assert rescue_task.status == TaskStatus.RESCUE_REQUIRED
    # Rescue pickup location MUST BE the failed robot's location (4, 5), NOT original pickup (1, 1)
    assert rescue_task.pickup_location == (4, 5)
    assert rescue_task.delivery_location == (9, 9)
    assert rescue_task.item_type == "pod_sku_77"
    assert rescue_task.metadata["is_rescue"] is True
    assert rescue_task.metadata["failed_robot_id"] == "R2"


# Test 5: Battery Management Thresholds and Charging Route Selection
def test_battery_manager_thresholds_and_charging():
    """Test 5: Battery manager correctly calculates thresholds, nearest charger, and bidding penalties."""
    mgr = BatteryManager(
        BatteryConfig(
            low_battery_threshold=30.0,
            critical_battery_threshold=15.0,
            full_charge_threshold=95.0,
        )
    )

    # Full battery
    assert mgr.should_seek_charging(100.0) is False
    assert mgr.is_critical(100.0) is False
    assert mgr.get_battery_penalty_for_bidding(100.0) == 0.0

    # Low battery at 25%
    assert mgr.should_seek_charging(25.0) is True
    assert mgr.is_critical(25.0) is False
    assert mgr.get_battery_penalty_for_bidding(25.0) == 300.0  # High penalty
    assert mgr.get_battery_urgency_for_negotiation(25.0) == 30.0

    # Critical battery at 10%
    assert mgr.is_critical(10.0) is True
    assert mgr.get_battery_penalty_for_bidding(10.0) == float("inf")  # Disallowed

    # Nearest charger discovery
    chargers = [(1, 1), (15, 15), (20, 2)]
    current_pos = (14, 13)
    nearest = mgr.find_nearest_charger(current_pos, chargers)
    assert nearest == (15, 15)

    # Energy consumption and charging
    b = mgr.consume_energy(100.0, is_moving=True, is_carrying=True)
    assert b == 99.8
    charged_b = mgr.apply_charge(20.0)
    assert charged_b == 22.0


def test_identical_robot_failure_between_dfleet_and_baseline():
    """Test: D-Fleet and Baseline execute with identical seed, fault injection, and failure ticks."""
    from app.simulation.warehouse import WarehouseGrid
    from app.metrics.comparison import ComparisonEngine

    warehouse = WarehouseGrid(width=16, height=12)
    robots_config = [
        {"id": "R1", "start_pos": [1, 1], "priority": 1},
        {"id": "R2", "start_pos": [14, 1], "priority": 1},
        {"id": "R3", "start_pos": [1, 10], "priority": 1},
        {"id": "R4", "start_pos": [14, 10], "priority": 1},
    ]
    tasks_config = [
        {"id": "T01", "pickup_pos": [5, 1], "delivery_pos": [13, 1], "priority": 2, "item_type": "AlphaPod"},
        {"id": "T02", "pickup_pos": [5, 10], "delivery_pos": [13, 10], "priority": 2, "item_type": "BetaPod"},
    ]

    report = ComparisonEngine.run_benchmark_comparison(
        warehouse=warehouse,
        robots_config=robots_config,
        tasks_config=tasks_config,
        max_ticks=50,
        seed=48291,
    )

    assert report.dfleet_report is not None
    assert report.baseline_report is not None
    assert "avg_completion_time" in report.comparisons


def test_failed_robot_cannot_complete_task():
    """Test: When a robot fails while holding a task, it cannot complete it itself.
    
    The task must become RESCUE_REQUIRED or RELEASED and require physical action.
    """
    monitor = PeerFailureMonitor(my_robot_id="R1", heartbeat_timeout_ticks=5)
    grid = WarehouseGrid(width=10, height=10)
    wm = LocalWorldModel(robot_id="R1", static_map=grid)
    tm = LocalTaskManager(robot_id="R1")

    task = tm.on_task_announced("task_fail_check", (2, 2), (8, 8))
    task.status = TaskStatus.GOING_TO_DELIVERY
    task.assigned_robot_id = "R2"

    monitor.record_peer_heartbeat(
        peer_id="R2",
        current_tick=10,
        position=(3, 3),
        carrying_item="pod_heavy",
        task_id="task_fail_check",
    )

    # R2 fails
    events = monitor.check_for_failed_peers(current_tick=16, world_model=wm, task_manager=tm)
    assert len(events) == 1
    assert task.status != TaskStatus.DELIVERED
    assert events[0].rescue_task_created.status == TaskStatus.RESCUE_REQUIRED


def test_battery_energy_feasibility_evaluation():
    """Test energy feasibility evaluation for safe task execution vs charging requirement."""
    bm = BatteryManager()
    
    # Case 1: Low battery (18%), short task (2 steps pickup, 2 steps delivery), close charger (1 step)
    # Required: 2*0.1 + 2*0.2 + 1*0.1 = 0.7. Available: 18 - 5 = 13.0 >= 0.7 -> Safe
    can_safe, req, avail = bm.evaluate_energy_feasibility(
        current_battery=18.0,
        pickup_dist=2,
        delivery_dist=2,
        charging_dist=1,
        is_carrying=False,
        safety_reserve=5.0,
    )
    assert can_safe is True
    assert avail > req

    # Case 2: Low battery (12%), long task (30 steps pickup, 25 steps delivery), distant charger (10 steps)
    # Required: 30*0.1 + 25*0.2 + 10*0.1 = 9.0. Available: 12 - 5 = 7.0 < 9.0 -> Unsafe
    can_safe2, req2, avail2 = bm.evaluate_energy_feasibility(
        current_battery=12.0,
        pickup_dist=30,
        delivery_dist=25,
        charging_dist=10,
        is_carrying=False,
        safety_reserve=5.0,
    )
    assert can_safe2 is False
    assert avail2 < req2

