"""Task definitions and lifecycle state machine for D-Fleet."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class TaskStatus(str, Enum):
    UNASSIGNED = "UNASSIGNED"
    BIDDING = "BIDDING"
    CLAIMED = "CLAIMED"
    GOING_TO_PICKUP = "GOING_TO_PICKUP"
    PICKED_UP = "PICKED_UP"
    GOING_TO_DELIVERY = "GOING_TO_DELIVERY"
    DELIVERED = "DELIVERED"
    RELEASED = "RELEASED"
    FAILED = "FAILED"
    RESCUE_REQUIRED = "RESCUE_REQUIRED"


@dataclass
class Task:
    """Represents a warehouse transport task."""
    task_id: str
    pickup_location: Tuple[int, int]
    delivery_location: Tuple[int, int]
    priority: int = 1
    status: TaskStatus = TaskStatus.UNASSIGNED
    assigned_robot_id: Optional[str] = None
    spawn_tick: int = 0
    deadline_tick: Optional[int] = None
    item_type: str = "standard_pod"
    bids: Dict[str, float] = field(default_factory=dict)
    claim_tick: Optional[int] = None
    claim_bid: Optional[float] = None
    completed_tick: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.status in (
            TaskStatus.CLAIMED,
            TaskStatus.GOING_TO_PICKUP,
            TaskStatus.PICKED_UP,
            TaskStatus.GOING_TO_DELIVERY,
        )

    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.DELIVERED, TaskStatus.FAILED, TaskStatus.RELEASED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "pickup_location": list(self.pickup_location),
            "delivery_location": list(self.delivery_location),
            "priority": self.priority,
            "status": self.status.value,
            "assigned_robot_id": self.assigned_robot_id,
            "spawn_tick": self.spawn_tick,
            "deadline_tick": self.deadline_tick,
            "item_type": self.item_type,
            "bids": self.bids,
            "claim_tick": self.claim_tick,
            "claim_bid": self.claim_bid,
            "completed_tick": self.completed_tick,
            "metadata": self.metadata,
        }
