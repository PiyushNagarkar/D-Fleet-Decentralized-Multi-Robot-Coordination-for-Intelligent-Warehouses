"""Sensor observations and spatial perception for D-Fleet robots.

Provides local sensory cones to decentralized robot agents and global telemetry
snapshots for dashboard rendering.
CRITICAL: Emits passive observation payloads only — no path planning or hints.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from .physics import RobotPhysicalState, PhysicalStatus, Direction
from .warehouse import WarehouseGrid, CellType
from .obstacle_manager import Obstacle


@dataclass
class NearbyRobotObservation:
    robot_id: str
    grid_position: Tuple[int, int]
    distance_manhattan: int
    heading: str
    is_carrying_pod: bool


@dataclass
class NearbyObstacleObservation:
    obstacle_id: str
    grid_position: Tuple[int, int]
    distance_manhattan: int
    obstacle_type: str


@dataclass
class RobotLocalObservation:
    """The local sensory state provided to a robot agent at a discrete tick."""
    robot_id: str
    tick: int
    grid_position: Tuple[int, int]
    world_position: Tuple[float, float, float]
    heading: str
    battery_level: float
    is_carrying_pod: bool
    carried_item_id: Optional[str]
    current_cell_type: str
    is_failed: bool
    failure_reason: Optional[str]
    traversable_adjacent: List[Tuple[int, int]]
    nearby_robots: List[NearbyRobotObservation] = field(default_factory=list)
    nearby_obstacles: List[NearbyObstacleObservation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "robot_id": self.robot_id,
            "tick": self.tick,
            "grid_position": list(self.grid_position),
            "world_position": list(self.world_position),
            "heading": self.heading,
            "battery_level": round(self.battery_level, 2),
            "is_carrying_pod": self.is_carrying_pod,
            "carried_item_id": self.carried_item_id,
            "current_cell_type": self.current_cell_type,
            "is_failed": self.is_failed,
            "failure_reason": self.failure_reason,
            "traversable_adjacent": [list(pos) for pos in self.traversable_adjacent],
            "nearby_robots": [
                {
                    "robot_id": r.robot_id,
                    "grid_position": list(r.grid_position),
                    "distance_manhattan": r.distance_manhattan,
                    "heading": r.heading,
                    "is_carrying_pod": r.is_carrying_pod,
                }
                for r in self.nearby_robots
            ],
            "nearby_obstacles": [
                {
                    "obstacle_id": o.obstacle_id,
                    "grid_position": list(o.grid_position),
                    "distance_manhattan": o.distance_manhattan,
                    "obstacle_type": o.obstacle_type,
                }
                for o in self.nearby_obstacles
            ],
        }


class ObservationEmitter:
    """Constructs sensor readings and telemetry frames from simulation physics."""

    def __init__(self, perception_radius: int = 4):
        self.perception_radius = perception_radius

    def generate_robot_observation(
        self,
        robot_state: RobotPhysicalState,
        warehouse: WarehouseGrid,
        all_robots: Dict[str, RobotPhysicalState],
        active_obstacles: List[Obstacle],
        current_tick: int,
    ) -> RobotLocalObservation:
        """Construct local perceptual frame within perception radius."""
        rx, ry = robot_state.x, robot_state.y

        # Detect adjacent traversable cells
        adjacent = warehouse.get_neighbors(rx, ry, allow_diagonal=False)

        # Detect nearby robots
        nearby_robots = []
        for other_id, other_state in all_robots.items():
            if other_id == robot_state.robot_id:
                continue
            dist = abs(other_state.x - rx) + abs(other_state.y - ry)
            if dist <= self.perception_radius:
                nearby_robots.append(
                    NearbyRobotObservation(
                        robot_id=other_id,
                        grid_position=(other_state.x, other_state.y),
                        distance_manhattan=dist,
                        heading=other_state.heading.value,
                        is_carrying_pod=other_state.is_carrying_pod,
                    )
                )

        # Detect nearby obstacles
        nearby_obstacles = []
        for obs in active_obstacles:
            dist = abs(obs.x - rx) + abs(obs.y - ry)
            if dist <= self.perception_radius:
                obs_type_val = obs.obstacle_type.value if hasattr(obs.obstacle_type, "value") else str(obs.obstacle_type)
                nearby_obstacles.append(
                    NearbyObstacleObservation(
                        obstacle_id=obs.obstacle_id,
                        grid_position=(obs.x, obs.y),
                        distance_manhattan=dist,
                        obstacle_type=obs_type_val,
                    )
                )

        current_cell = warehouse.get_cell(rx, ry).value

        return RobotLocalObservation(
            robot_id=robot_state.robot_id,
            tick=current_tick,
            grid_position=(rx, ry),
            world_position=robot_state.world_position,
            heading=robot_state.heading.value,
            battery_level=robot_state.battery_level,
            is_carrying_pod=robot_state.is_carrying_pod,
            carried_item_id=robot_state.carried_item_id,
            current_cell_type=current_cell,
            is_failed=robot_state.is_failed,
            failure_reason=robot_state.failure_reason,
            traversable_adjacent=adjacent,
            nearby_robots=nearby_robots,
            nearby_obstacles=nearby_obstacles,
        )

    def generate_global_snapshot(
        self,
        warehouse: WarehouseGrid,
        all_robots: Dict[str, RobotPhysicalState],
        active_obstacles: List[Obstacle],
        current_tick: int,
        clock_time_s: float,
    ) -> Dict[str, Any]:
        """Construct full global digital twin telemetry frame for WebSocket gateway."""
        return {
            "tick": current_tick,
            "time_s": round(clock_time_s, 2),
            "robots": [r.to_dict() for r in all_robots.values()],
            "active_obstacles": [
                {
                    "obstacle_id": obs.obstacle_id,
                    "obstacle_type": obs.obstacle_type.value,
                    "grid_position": [obs.x, obs.y],
                    "world_position": [
                        float(obs.x) * warehouse.cell_size,
                        0.0,
                        float(obs.y) * warehouse.cell_size,
                    ],
                }
                for obs in active_obstacles
            ],
            "warehouse": {
                "name": warehouse.name,
                "width": warehouse.width,
                "height": warehouse.height,
            },
        }
