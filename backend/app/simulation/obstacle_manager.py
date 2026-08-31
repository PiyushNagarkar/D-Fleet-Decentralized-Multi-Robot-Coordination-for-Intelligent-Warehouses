"""Dynamic and static obstacle management for D-Fleet warehouse simulation."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import uuid


class ObstacleType(str, Enum):
    STATIC = "STATIC"           # Spilled pallet, temporary drop-off
    MOVING = "MOVING"           # Human worker, forklift, AGV
    SCHEDULED = "SCHEDULED"     # Maintenance zone active between ticks


class ObstacleAction(str, Enum):
    ADD_OBSTACLE = "ADD_OBSTACLE"
    MOVE_OBSTACLE = "MOVE_OBSTACLE"
    REMOVE_OBSTACLE = "REMOVE_OBSTACLE"


@dataclass
class Obstacle:
    """Represents an active or scheduled dynamic obstacle in the warehouse."""
    obstacle_id: str
    obstacle_type: ObstacleType
    start_tick: int
    x: int
    y: int
    duration: Optional[int] = None  # None indicates indefinite until explicitly removed
    waypoints: List[Tuple[int, int]] = field(default_factory=list)
    speed_ticks_per_step: int = 1   # Moves to next waypoint every N ticks
    is_active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    _waypoint_idx: int = 0
    _ticks_at_current_waypoint: int = 0

    @property
    def end_tick(self) -> Optional[int]:
        if self.duration is not None:
            return self.start_tick + self.duration
        return None

    def is_alive_at(self, tick: int) -> bool:
        if tick < self.start_tick:
            return False
        if self.duration is not None and tick >= self.start_tick + self.duration:
            return False
        return True

    def step(self, tick: int) -> Optional[Tuple[int, int]]:
        """Update obstacle position if moving. Returns new (x, y) or None."""
        if not self.is_alive_at(tick):
            self.is_active = False
            return None

        self.is_active = True

        if self.obstacle_type == ObstacleType.MOVING and self.waypoints:
            if tick > self.start_tick:
                self._ticks_at_current_waypoint += 1
                if self._ticks_at_current_waypoint >= self.speed_ticks_per_step:
                    self._ticks_at_current_waypoint = 0
                    self._waypoint_idx = (self._waypoint_idx + 1) % len(self.waypoints)
                    self.x, self.y = self.waypoints[self._waypoint_idx]
            return (self.x, self.y)

        return (self.x, self.y)


class ObstacleManager:
    """Manages scheduled, static, and dynamic moving obstacles."""

    def __init__(self):
        self._obstacles: Dict[str, Obstacle] = {}

    def add_obstacle(
        self,
        x: int,
        y: int,
        start_tick: int = 0,
        duration: Optional[int] = None,
        obstacle_type: ObstacleType = ObstacleType.STATIC,
        waypoints: Optional[List[Tuple[int, int]]] = None,
        speed_ticks_per_step: int = 1,
        obstacle_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Obstacle:
        """Schedule or add a new dynamic obstacle."""
        obs_id = obstacle_id or f"obs_{uuid.uuid4().hex[:8]}"
        if isinstance(obstacle_type, str):
            try:
                obstacle_type = ObstacleType(obstacle_type.upper())
            except ValueError:
                obstacle_type = ObstacleType.STATIC
        obs = Obstacle(
            obstacle_id=obs_id,
            obstacle_type=obstacle_type,
            start_tick=start_tick,
            x=x,
            y=y,
            duration=duration,
            waypoints=waypoints or ([(x, y)] if not waypoints else waypoints),
            speed_ticks_per_step=speed_ticks_per_step,
            metadata=metadata or {},
        )
        self._obstacles[obs_id] = obs
        return obs

    def move_obstacle(self, obstacle_id: str, new_x: int, new_y: int) -> bool:
        """Explicitly move an obstacle to new coordinates."""
        if obstacle_id in self._obstacles:
            self._obstacles[obstacle_id].x = new_x
            self._obstacles[obstacle_id].y = new_y
            return True
        return False

    def remove_obstacle(self, obstacle_id: str) -> bool:
        """Manually remove an obstacle."""
        if obstacle_id in self._obstacles:
            del self._obstacles[obstacle_id]
            return True
        return False

    def get_obstacle(self, obstacle_id: str) -> Optional[Obstacle]:
        return self._obstacles.get(obstacle_id)

    def tick(self, current_tick: int) -> Tuple[List[Obstacle], List[Obstacle], List[Obstacle]]:
        """Advance obstacle states by one tick.
        
        Returns:
            (newly_spawned, moved_obstacles, expired_obstacles)
        """
        spawned = []
        moved = []
        expired = []

        for obs in list(self._obstacles.values()):
            was_active = obs.is_active
            old_pos = (obs.x, obs.y)
            new_pos = obs.step(current_tick)

            if not was_active and obs.is_active:
                spawned.append(obs)
            elif was_active and not obs.is_active:
                expired.append(obs)
            elif obs.is_active and new_pos != old_pos:
                moved.append(obs)

        return spawned, moved, expired

    def get_active_obstacle_positions(self, current_tick: int) -> Set[Tuple[int, int]]:
        """Returns set of all grid cells currently occupied by active dynamic obstacles."""
        return {
            (obs.x, obs.y)
            for obs in self._obstacles.values()
            if obs.is_alive_at(current_tick)
        }

    def is_obstacle_at(self, x: int, y: int, current_tick: int) -> bool:
        """Check if any active obstacle is at (x, y)."""
        return (x, y) in self.get_active_obstacle_positions(current_tick)

    def reset(self) -> None:
        """Clear all obstacles."""
        self._obstacles.clear()
