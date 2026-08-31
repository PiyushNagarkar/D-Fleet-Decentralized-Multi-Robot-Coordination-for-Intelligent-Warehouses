"""Event vocabulary and append-only event log for D-Fleet simulation.

This module defines the full telemetry and event schema.
CRITICAL: This module NEVER makes decisions, assigns tasks, or resolves conflicts.
It strictly acts as a passive, append-only observability recorder.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import time
import uuid


class EventType(str, Enum):
    # Task Events
    TASK_SPAWNED = "TASK_SPAWNED"
    TASK_ANNOUNCED = "TASK_ANNOUNCED"
    TASK_BID_SUBMITTED = "TASK_BID_SUBMITTED"
    TASK_AWARDED = "TASK_AWARDED"
    TASK_PICKED_UP = "TASK_PICKED_UP"
    TASK_DELIVERED = "TASK_DELIVERED"
    TASK_CANCELLED = "TASK_CANCELLED"
    TASK_FAILED = "TASK_FAILED"

    # Reservation & Coordination Events
    RESERVATION_REQUESTED = "RESERVATION_REQUESTED"
    RESERVATION_ACQUIRED = "RESERVATION_ACQUIRED"
    RESERVATION_RELEASED = "RESERVATION_RELEASED"
    RESERVATION_DENIED = "RESERVATION_DENIED"

    # Conflict & Deadlock Events
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    CONFLICT_NEGOTIATING = "CONFLICT_NEGOTIATING"
    CONFLICT_RESOLVED = "CONFLICT_RESOLVED"
    DEADLOCK_DETECTED = "DEADLOCK_DETECTED"
    DEADLOCK_RESOLVED = "DEADLOCK_RESOLVED"

    # Obstacle Events
    OBSTACLE_ADDED = "OBSTACLE_ADDED"
    OBSTACLE_MOVED = "OBSTACLE_MOVED"
    OBSTACLE_EXPIRED = "OBSTACLE_EXPIRED"
    OBSTACLE_REMOVED = "OBSTACLE_REMOVED"

    # Robot State, Motion & Hardware Events
    ROBOT_SPAWNED = "ROBOT_SPAWNED"
    ROBOT_MOVED = "ROBOT_MOVED"
    ROBOT_WAITING = "ROBOT_WAITING"
    ROBOT_ROTATED = "ROBOT_ROTATED"
    ROBOT_COLLISION = "ROBOT_COLLISION"
    ROBOT_FAILED = "ROBOT_FAILED"
    ROBOT_RECOVERED = "ROBOT_RECOVERED"

    # Battery & Charging Events
    BATTERY_LOW = "BATTERY_LOW"
    BATTERY_CRITICAL = "BATTERY_CRITICAL"
    CHARGING_STARTED = "CHARGING_STARTED"
    CHARGING_PROGRESS = "CHARGING_PROGRESS"
    CHARGING_FINISHED = "CHARGING_FINISHED"

    # Simulation Lifecycle
    SIMULATION_STARTED = "SIMULATION_STARTED"
    SIMULATION_PAUSED = "SIMULATION_PAUSED"
    SIMULATION_RESUMED = "SIMULATION_RESUMED"
    SIMULATION_STOPPED = "SIMULATION_STOPPED"
    SIMULATION_RESET = "SIMULATION_RESET"


@dataclass(frozen=True)
class Event:
    """Immutable simulation event representation."""
    event_type: EventType
    tick: int
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    robot_id: Optional[str] = None
    location: Optional[Tuple[int, int]] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "tick": self.tick,
            "timestamp": self.timestamp,
            "robot_id": self.robot_id,
            "location": list(self.location) if self.location is not None else None,
            "payload": self.payload,
        }


class EventLog:
    """Append-only in-memory log for simulation telemetry and auditing."""

    def __init__(self, max_history: Optional[int] = 50000):
        self._events: List[Event] = []
        self._max_history = max_history

    def record(self, event: Event) -> None:
        """Append an event to the log."""
        self._events.append(event)
        if self._max_history and len(self._events) > self._max_history:
            self._events.pop(0)

    def emit(
        self,
        event_type: EventType,
        tick: int,
        robot_id: Optional[str] = None,
        location: Optional[Tuple[int, int]] = None,
        **payload: Any,
    ) -> Event:
        """Convenience helper to construct and record an event."""
        ev = Event(
            event_type=event_type,
            tick=tick,
            robot_id=robot_id,
            location=location,
            payload=payload,
        )
        self.record(ev)
        return ev

    def get_events(
        self,
        since_tick: Optional[int] = None,
        event_type: Optional[EventType] = None,
        robot_id: Optional[str] = None,
    ) -> List[Event]:
        """Filter and retrieve events."""
        results = self._events
        if since_tick is not None:
            results = [e for e in results if e.tick >= since_tick]
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        if robot_id is not None:
            results = [e for e in results if e.robot_id == robot_id]
        return results

    def clear(self) -> None:
        """Clear all events (e.g. upon simulation reset)."""
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)
