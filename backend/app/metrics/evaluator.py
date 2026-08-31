"""Metrics Evaluator computing statistical summaries, KPIs, and performance scorecards."""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import statistics

from .collector import MetricsCollector


@dataclass
class SimulationReport:
    # 1. Task Completion
    tasks_completed: int
    tasks_total: int
    total_completion_time: int
    avg_completion_time: float
    max_completion_time: int

    # 2. Movement & Delays
    total_waiting_time: int
    avg_waiting_time: float
    max_waiting_time: int
    total_path_length: int
    avg_path_length: float

    # 3. Conflicts & Deadlocks
    conflicts_detected: int
    conflicts_resolved: int
    collisions_count: int
    deadlocks_detected: int
    deadlocks_resolved: int
    avg_deadlock_recovery_ticks: float
    replanning_events: int

    # 4. P2P Communication
    messages_sent: int
    messages_received: int
    avg_message_latency: float
    messages_lost: int
    messages_duplicated: int
    messages_stale: int

    # 5. Failures & Resilience
    robot_failures: int
    tasks_reassigned: int
    rescue_operations_completed: int
    avg_failure_recovery_time: float

    # 6. Battery & Energy
    total_energy_consumed: float
    avg_energy_consumed_per_robot: float
    charging_events: int
    avg_final_battery: float

    # 7. High-Level Performance
    total_simulation_ticks: int
    throughput_per_100_ticks: float
    robot_utilization: float  # Moving ticks / total robot ticks

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsEvaluator:
    """Evaluates raw metrics into a structured statistical scorecard."""

    @staticmethod
    def evaluate(collector: MetricsCollector) -> SimulationReport:
        total_ticks = max(1, collector.total_ticks)
        durations = collector.task_durations
        tasks_completed = len(durations)
        tasks_total = max(tasks_completed, len(collector.task_spawn_times))

        # Task completion stats
        total_comp = sum(durations) if durations else 0
        avg_comp = round(statistics.mean(durations), 2) if durations else 0.0
        max_comp = max(durations) if durations else 0

        # Waiting times
        wait_values = list(collector.robot_waiting_ticks.values())
        total_wait = sum(wait_values)
        avg_wait = round(statistics.mean(wait_values), 2) if wait_values else 0.0
        max_wait = max(wait_values) if wait_values else 0

        # Path lengths
        path_values = list(collector.robot_path_lengths.values())
        total_path = sum(path_values)
        avg_path = round(statistics.mean(path_values), 2) if path_values else 0.0

        # Deadlock recovery
        deadlock_recs = collector.deadlock_recovery_times
        avg_deadlock_rec = round(statistics.mean(deadlock_recs), 2) if deadlock_recs else 0.0

        # Message latency
        latencies = collector.message_latencies
        avg_latency = round(statistics.mean(latencies), 2) if latencies else 0.0

        # Failure recovery
        fail_recs = collector.failure_recovery_times
        avg_fail_rec = round(statistics.mean(fail_recs), 2) if fail_recs else 0.0

        # Energy & Battery
        energy_values = list(collector.energy_consumed_by_robot.values())
        total_energy = round(sum(energy_values), 2)
        avg_energy = round(statistics.mean(energy_values), 2) if energy_values else 0.0

        batteries = list(collector.final_robot_batteries.values())
        avg_battery = round(statistics.mean(batteries), 2) if batteries else 100.0

        # Throughput
        throughput = round((tasks_completed / total_ticks) * 100.0, 2)

        # Robot utilization
        moving_values = list(collector.robot_moving_ticks.values())
        total_moving_ticks = sum(moving_values)
        num_robots = max(1, len(collector.robot_moving_ticks) or len(collector.final_robot_batteries) or 1)
        total_possible_robot_ticks = num_robots * total_ticks
        utilization = round((total_moving_ticks / max(1, total_possible_robot_ticks)) * 100.0, 2)

        return SimulationReport(
            tasks_completed=tasks_completed,
            tasks_total=tasks_total,
            total_completion_time=total_comp,
            avg_completion_time=avg_comp,
            max_completion_time=max_comp,
            total_waiting_time=total_wait,
            avg_waiting_time=avg_wait,
            max_waiting_time=max_wait,
            total_path_length=total_path,
            avg_path_length=avg_path,
            conflicts_detected=collector.conflicts_detected,
            conflicts_resolved=collector.conflicts_resolved,
            collisions_count=collector.collisions_count,
            deadlocks_detected=collector.deadlocks_detected,
            deadlocks_resolved=collector.deadlocks_resolved,
            avg_deadlock_recovery_ticks=avg_deadlock_rec,
            replanning_events=collector.replanning_events,
            messages_sent=collector.messages_sent,
            messages_received=collector.messages_received,
            avg_message_latency=avg_latency,
            messages_lost=collector.messages_lost,
            messages_duplicated=collector.messages_duplicated,
            messages_stale=collector.messages_stale,
            robot_failures=collector.robot_failures,
            tasks_reassigned=collector.tasks_reassigned,
            rescue_operations_completed=collector.rescue_operations_completed,
            avg_failure_recovery_time=avg_fail_rec,
            total_energy_consumed=total_energy,
            avg_energy_consumed_per_robot=avg_energy,
            charging_events=collector.charging_events,
            avg_final_battery=avg_battery,
            total_simulation_ticks=total_ticks,
            throughput_per_100_ticks=throughput,
            robot_utilization=utilization,
        )
