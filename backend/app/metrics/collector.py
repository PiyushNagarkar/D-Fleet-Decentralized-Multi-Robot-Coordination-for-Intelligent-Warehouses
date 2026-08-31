"""Metrics Collector aggregating simulation telemetry, performance counters, and event streams."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
import statistics

from app.simulation.events import EventLog, Event, EventType


@dataclass
class MetricsCollector:
    """Collects and aggregates granular simulation execution metrics."""

    # 1. Task Completion Metrics
    task_spawn_times: Dict[str, int] = field(default_factory=dict)
    task_completion_times: Dict[str, int] = field(default_factory=dict)
    task_durations: List[int] = field(default_factory=list)

    # 2. Movement and Delays
    robot_waiting_ticks: Dict[str, int] = field(default_factory=dict)
    robot_moving_ticks: Dict[str, int] = field(default_factory=dict)
    robot_path_lengths: Dict[str, int] = field(default_factory=dict)

    # 3. Conflicts, Deadlocks & Replanning
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    collisions_count: int = 0
    deadlocks_detected: int = 0
    deadlocks_resolved: int = 0
    deadlock_recovery_times: List[int] = field(default_factory=list)
    replanning_events: int = 0

    # 4. P2P Communication
    messages_sent: int = 0
    messages_received: int = 0
    messages_lost: int = 0
    messages_duplicated: int = 0
    messages_stale: int = 0
    message_latencies: List[int] = field(default_factory=list)

    # 5. Failures and Rescues
    robot_failures: int = 0
    tasks_reassigned: int = 0
    rescue_operations_completed: int = 0
    failure_recovery_times: List[int] = field(default_factory=list)

    # 6. Energy and Battery
    energy_consumed_by_robot: Dict[str, float] = field(default_factory=dict)
    charging_events: int = 0
    final_robot_batteries: Dict[str, float] = field(default_factory=dict)

    # Total simulation ticks
    total_ticks: int = 0

    def ingest_event(self, event: Event) -> None:
        """Ingest a single EventLog event to update metrics counters."""
        e_type = event.event_type
        t = event.tick
        p = event.payload or {}
        r_id = event.robot_id

        if e_type == EventType.TASK_SPAWNED:
            task_id = p.get("task_id")
            if task_id:
                self.task_spawn_times[task_id] = t

        elif e_type == EventType.TASK_DELIVERED:
            task_id = p.get("task_id") or p.get("item_id")
            if task_id and task_id in self.task_spawn_times:
                duration = max(1, t - self.task_spawn_times[task_id])
                self.task_completion_times[task_id] = t
                self.task_durations.append(duration)

        elif e_type == EventType.ROBOT_MOVED:
            if r_id:
                self.robot_moving_ticks[r_id] = self.robot_moving_ticks.get(r_id, 0) + 1
                self.robot_path_lengths[r_id] = self.robot_path_lengths.get(r_id, 0) + 1

        elif e_type == EventType.ROBOT_COLLISION:
            self.collisions_count += 1

        elif e_type == EventType.ROBOT_FAILED:
            self.robot_failures += 1

        elif e_type == EventType.ROBOT_RECOVERED:
            rec_time = p.get("recovery_ticks", 5)
            self.failure_recovery_times.append(rec_time)

        elif e_type == EventType.CHARGING_STARTED:
            self.charging_events += 1

    def ingest_event_log(self, event_log: EventLog) -> None:
        """Process all events from an EventLog."""
        for ev in event_log._events:
            self.ingest_event(ev)

    def record_waiting_tick(self, robot_id: str) -> None:
        self.robot_waiting_ticks[robot_id] = self.robot_waiting_ticks.get(robot_id, 0) + 1

    def record_conflict_detected(self) -> None:
        self.conflicts_detected += 1

    def record_conflict_resolved(self) -> None:
        self.conflicts_resolved += 1

    def record_deadlock_resolved(self, recovery_ticks: int = 1) -> None:
        self.deadlocks_detected += 1
        self.deadlocks_resolved += 1
        self.deadlock_recovery_times.append(recovery_ticks)

    def record_replanning_event(self) -> None:
        self.replanning_events += 1

    def record_message_sent(self) -> None:
        self.messages_sent += 1

    def record_message_received(self, latency: int = 0) -> None:
        self.messages_received += 1
        self.message_latencies.append(latency)

    def record_message_dropped(self) -> None:
        self.messages_lost += 1

    def record_message_duplicated(self) -> None:
        self.messages_duplicated += 1

    def record_message_stale(self) -> None:
        self.messages_stale += 1

    def record_rescue_completed(self) -> None:
        self.rescue_operations_completed += 1

    def record_energy_consumed(self, robot_id: str, energy: float) -> None:
        self.energy_consumed_by_robot[robot_id] = round(
            self.energy_consumed_by_robot.get(robot_id, 0.0) + energy, 4
        )

    def record_final_battery(self, robot_id: str, battery: float) -> None:
        self.final_robot_batteries[robot_id] = round(battery, 2)
