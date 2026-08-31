"""Unit and Integration tests for Metrics Collector, Evaluator, and Baseline Comparison."""

import pytest
from app.simulation.warehouse import WarehouseGrid
from app.simulation.events import EventLog, EventType
from app.metrics.collector import MetricsCollector
from app.metrics.evaluator import MetricsEvaluator
from app.metrics.comparison import ComparisonEngine, StopAndGoBaselineCoordinator


def test_metric_calculations_against_synthetic_events():
    """Test 1: Unit tests for each metric calculation against a synthetic event log."""
    collector = MetricsCollector()
    event_log = EventLog()

    # Synthetic event stream:
    # 1. Task 1 spawned at tick 10, delivered at tick 30 (duration = 20)
    event_log.emit(EventType.TASK_SPAWNED, tick=10, location=(1, 1), task_id="task_1")
    event_log.emit(EventType.TASK_DELIVERED, tick=30, location=(5, 5), task_id="task_1")

    # 2. Task 2 spawned at tick 15, delivered at tick 45 (duration = 30)
    event_log.emit(EventType.TASK_SPAWNED, tick=15, location=(2, 2), task_id="task_2")
    event_log.emit(EventType.TASK_DELIVERED, tick=45, location=(8, 8), task_id="task_2")

    # 3. Robot motion and collisions
    event_log.emit(EventType.ROBOT_MOVED, tick=11, robot_id="R1", location=(2, 1))
    event_log.emit(EventType.ROBOT_MOVED, tick=12, robot_id="R1", location=(3, 1))
    event_log.emit(EventType.ROBOT_MOVED, tick=16, robot_id="R2", location=(2, 3))
    event_log.emit(EventType.ROBOT_COLLISION, tick=20)

    # 4. Failures & Recovery
    event_log.emit(EventType.ROBOT_FAILED, tick=25, robot_id="R2")
    event_log.emit(EventType.ROBOT_RECOVERED, tick=30, robot_id="R2", recovery_ticks=5)

    # 5. Charging
    event_log.emit(EventType.CHARGING_STARTED, tick=35, robot_id="R1")

    # Ingest event log
    collector.ingest_event_log(event_log)
    collector.total_ticks = 50

    # Custom telemetry counters
    collector.record_waiting_tick("R1")
    collector.record_waiting_tick("R1")
    collector.record_waiting_tick("R2")
    collector.record_conflict_detected()
    collector.record_conflict_resolved()
    collector.record_deadlock_resolved(recovery_ticks=3)
    collector.record_replanning_event()
    collector.record_message_sent()
    collector.record_message_sent()
    collector.record_message_received(latency=1)
    collector.record_message_dropped()
    collector.record_rescue_completed()
    collector.record_energy_consumed("R1", 12.5)
    collector.record_energy_consumed("R2", 8.0)
    collector.record_final_battery("R1", 87.5)
    collector.record_final_battery("R2", 92.0)

    # Evaluate report
    report = MetricsEvaluator.evaluate(collector)

    # Assertions
    assert report.tasks_completed == 2
    assert report.tasks_total == 2
    assert report.total_completion_time == 50  # 20 + 30
    assert report.avg_completion_time == 25.0  # (20 + 30) / 2
    assert report.max_completion_time == 30

    assert report.total_waiting_time == 3  # 2 for R1, 1 for R2
    assert report.avg_waiting_time == 1.5
    assert report.max_waiting_time == 2

    assert report.total_path_length == 3  # 2 for R1, 1 for R2
    assert report.collisions_count == 1
    assert report.conflicts_detected == 1
    assert report.conflicts_resolved == 1
    assert report.deadlocks_detected == 1
    assert report.deadlocks_resolved == 1
    assert report.avg_deadlock_recovery_ticks == 3.0
    assert report.replanning_events == 1

    assert report.messages_sent == 2
    assert report.messages_received == 1
    assert report.messages_lost == 1
    assert report.avg_message_latency == 1.0

    assert report.robot_failures == 1
    assert report.rescue_operations_completed == 1
    assert report.avg_failure_recovery_time == 5.0

    assert report.total_energy_consumed == 20.5
    assert report.avg_energy_consumed_per_robot == 10.25
    assert report.charging_events == 1
    assert report.avg_final_battery == 89.75


def test_baseline_comparison_integration_and_improvement_calculation():
    """Test 2: Run a small scenario under both D-Fleet and Stop-and-Go Baseline modes
    and confirm the comparison report has expected fields and plausible non-hardcoded signs."""
    ascii_map = """
    ############
    #C..P1...D1#
    #...######.#
    #...#....#.#
    #.I.#.I..#.#
    #...#....#.#
    #...######.#
    #C..P2...D2#
    ############
    """
    grid = WarehouseGrid.from_ascii(ascii_map, name="benchmark_warehouse")

    robots_config = [
        {"id": "R1", "start_pos": [1, 1], "priority": 2},
        {"id": "R2", "start_pos": [1, 7], "priority": 1},
    ]

    tasks_config = [
        {"id": "task_A", "pickup_pos": [4, 1], "delivery_pos": [9, 1], "priority": 2, "item_type": "pod_A"},
        {"id": "task_B", "pickup_pos": [4, 7], "delivery_pos": [9, 7], "priority": 1, "item_type": "pod_B"},
    ]

    # Execute dynamic benchmark comparison
    comparison_report = ComparisonEngine.run_benchmark_comparison(
        warehouse=grid,
        robots_config=robots_config,
        tasks_config=tasks_config,
        max_ticks=80,
        seed=42,
    )

    # 1. Structure Verification
    assert comparison_report.scenario_name == "benchmark_warehouse"
    assert "dfleet_report" in comparison_report.to_dict()
    assert "baseline_report" in comparison_report.to_dict()
    assert "comparisons" in comparison_report.to_dict()
    assert "summary" in comparison_report.to_dict()

    comparisons = comparison_report.comparisons
    assert "avg_completion_time" in comparisons
    assert "total_waiting_time" in comparisons
    assert "throughput_per_100_ticks" in comparisons

    # 2. Plausibility Assertions
    # In Stop-and-Go baseline, robots serialize movements (forcing waiting),
    # whereas D-Fleet allows concurrent multi-robot movement.
    dfleet_wait = comparisons["total_waiting_time"]["dfleet"]
    baseline_wait = comparisons["total_waiting_time"]["baseline"]
    assert baseline_wait > dfleet_wait, f"Expected Stop-and-Go to have more waiting time ({baseline_wait}) than D-Fleet ({dfleet_wait})"

    waiting_improvement = comparisons["total_waiting_time"]["improvement_percentage"]
    assert waiting_improvement > 0.0, "Expected positive improvement in waiting time reduction"

    # Improvement is dynamically calculated, not hardcoded
    expected_calc = ComparisonEngine.calculate_improvement(baseline_wait, dfleet_wait, higher_is_better=False)
    assert waiting_improvement == expected_calc
