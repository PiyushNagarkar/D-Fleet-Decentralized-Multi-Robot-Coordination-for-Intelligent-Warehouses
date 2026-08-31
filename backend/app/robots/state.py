"""Autonomous Robot State representation for D-Fleet."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any


class RobotStatus(str, Enum):
    IDLE = "IDLE"
    BIDDING = "BIDDING"
    MOVING_TO_PICKUP = "MOVING_TO_PICKUP"
    PICKED_UP = "PICKED_UP"
    MOVING_TO_DELIVERY = "MOVING_TO_DELIVERY"
    WAITING = "WAITING"
    NEGOTIATING = "NEGOTIATING"
    REROUTING = "REROUTING"
    LOW_BATTERY = "LOW_BATTERY"
    CHARGING = "CHARGING"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"


@dataclass
class RobotState:
    """Internal state maintained by an individual autonomous robot agent.
    
    CRITICAL: This is the robot's private state, mutated only by its own agent logic.
    """
    robot_id: str
    position: Tuple[int, int]
    next_position: Optional[Tuple[int, int]] = None
    battery: float = 100.0
    status: RobotStatus = RobotStatus.IDLE
    task_id: Optional[str] = None
    carrying_item: Optional[str] = None
    current_path: List[Tuple[int, int]] = field(default_factory=list)
    path_version: int = 0
    priority: int = 1
    last_heartbeat: int = 0
    local_map_version: int = 0

    def set_path(self, path: List[Tuple[int, int]]) -> None:
        """Assign a newly planned local path to the robot."""
        self.current_path = list(path)
        self.path_version += 1
        if len(self.current_path) > 1:
            self.next_position = self.current_path[1]
        elif len(self.current_path) == 1:
            self.next_position = self.current_path[0]
        else:
            self.next_position = None

    def advance_path(self) -> Optional[Tuple[int, int]]:
        """Advance one step along the current path after a successful physical move."""
        if not self.current_path:
            self.next_position = None
            return None

        # Pop the current waypoint that was just reached
        self.position = self.current_path.pop(0)
        
        # Set next_position for prospective reservations and conflict detection
        if self.current_path:
            self.next_position = self.current_path[0]
        else:
            self.next_position = None

        return self.position

    def clear_path(self) -> None:
        self.current_path.clear()
        self.next_position = None
        self.path_version += 1

    def transition_to(self, new_status: RobotStatus) -> None:
        self.status = new_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "robot_id": self.robot_id,
            "position": list(self.position),
            "next_position": list(self.next_position) if self.next_position is not None else None,
            "battery": round(self.battery, 2),
            "status": self.status.value,
            "task_id": self.task_id,
            "carrying_item": self.carrying_item,
            "current_path": [list(p) for p in self.current_path],
            "path_version": self.path_version,
            "priority": self.priority,
            "last_heartbeat": self.last_heartbeat,
            "local_map_version": self.local_map_version,
        }
