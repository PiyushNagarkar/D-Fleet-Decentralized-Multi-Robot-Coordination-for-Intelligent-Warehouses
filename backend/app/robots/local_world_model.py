"""Decentralized Local World Model maintained independently by each robot."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
import copy

from app.simulation.warehouse import WarehouseGrid, CellType
from app.simulation.observations import RobotLocalObservation
from .network import PeerMessage


@dataclass
class KnownObstacle:
    obstacle_id: str
    position: Tuple[int, int]
    obstacle_type: str
    first_observed_tick: int
    last_observed_tick: int
    estimated_expiration_tick: Optional[int] = None
    waypoints: List[Tuple[int, int]] = field(default_factory=list)


@dataclass
class KnownRobotInfo:
    robot_id: str
    position: Tuple[int, int]
    heading: str
    is_carrying_pod: bool
    status: str
    battery_level: float
    last_observed_tick: int
    planned_path: List[Tuple[int, int]] = field(default_factory=list)


class LocalWorldModel:
    """Robot's internal private representation of the warehouse environment.

    CRITICAL ARCHITECTURAL MANDATE:
    This model is populated ONLY via:
    1. Direct sensory observations (`update_from_observation`)
    2. Explicit peer-to-peer messages (`update_from_peer_message`)
    
    It is never constructed or synchronized from a central global coordinator.
    Two robots at the exact same simulation tick will have divergent world models
    depending on their local vantage point and communication latency.
    """

    def __init__(
        self,
        robot_id: str,
        static_map: WarehouseGrid,
        default_obstacle_duration_estimate: int = 50,
    ):
        self.robot_id = robot_id
        self.static_map = static_map
        self.default_obstacle_duration_estimate = default_obstacle_duration_estimate
        
        self.dynamic_obstacles: Dict[str, KnownObstacle] = {}
        self.known_robots: Dict[str, KnownRobotInfo] = {}
        self.reservations: Dict[Tuple[Tuple[int, int], int], str] = {}  # ((x, y), tick) -> robot_id
        self.available_tasks: Dict[str, Dict[str, Any]] = {}
        self.failed_robots: Set[str] = set()
        self.map_version: int = 1
        self.last_update_time: int = 0

    def update_from_observation(self, obs: RobotLocalObservation) -> None:
        """Integrate direct sensory readings from local perception cone."""
        current_tick = obs.tick
        self.last_update_time = current_tick

        # 1. Update known nearby robots
        for nr in obs.nearby_robots:
            self.known_robots[nr.robot_id] = KnownRobotInfo(
                robot_id=nr.robot_id,
                position=nr.grid_position,
                heading=nr.heading,
                is_carrying_pod=nr.is_carrying_pod,
                status="UNKNOWN",
                battery_level=100.0,
                last_observed_tick=current_tick,
            )

        # 2. Update known dynamic obstacles
        for no in obs.nearby_obstacles:
            if no.obstacle_id not in self.dynamic_obstacles:
                self.dynamic_obstacles[no.obstacle_id] = KnownObstacle(
                    obstacle_id=no.obstacle_id,
                    position=no.grid_position,
                    obstacle_type=no.obstacle_type,
                    first_observed_tick=current_tick,
                    last_observed_tick=current_tick,
                    estimated_expiration_tick=current_tick + self.default_obstacle_duration_estimate,
                )
                self.map_version += 1
            else:
                existing = self.dynamic_obstacles[no.obstacle_id]
                existing.position = no.grid_position
                existing.last_observed_tick = current_tick

    def update_from_peer_message(self, message: PeerMessage, current_tick: int) -> None:
        """Integrate information received via peer-to-peer communication."""
        self.last_update_time = current_tick
        msg_type = message.message_type
        payload = message.payload

        if msg_type == "OBSTACLE_ALERT":
            obs_id = payload.get("obstacle_id", f"peer_obs_{message.sender_id}")
            pos_raw = payload.get("position")
            if pos_raw:
                pos = (pos_raw[0], pos_raw[1])
                obs_type = payload.get("obstacle_type", "STATIC")
                expiry = payload.get("estimated_expiration_tick", current_tick + self.default_obstacle_duration_estimate)
                
                self.dynamic_obstacles[obs_id] = KnownObstacle(
                    obstacle_id=obs_id,
                    position=pos,
                    obstacle_type=obs_type,
                    first_observed_tick=current_tick,
                    last_observed_tick=current_tick,
                    estimated_expiration_tick=expiry,
                )
                self.map_version += 1

        elif msg_type == "RESERVATION_BROADCAST":
            # Space-time reservation claimed by peer
            owner = payload.get("robot_id", message.sender_id)
            for item in payload.get("reservations", []):
                pos = (item["x"], item["y"])
                tick = item["tick"]
                self.reservations[(pos, tick)] = owner

        elif msg_type == "RESERVATION_RELEASE":
            owner = payload.get("robot_id", message.sender_id)
            for item in payload.get("reservations", []):
                pos = (item["x"], item["y"])
                tick = item["tick"]
                if self.reservations.get((pos, tick)) == owner:
                    del self.reservations[(pos, tick)]

        elif msg_type == "TASK_ANNOUNCEMENT":
            task_id = payload.get("task_id")
            if task_id:
                self.available_tasks[task_id] = payload

        elif msg_type == "TASK_CLAIMED":
            task_id = payload.get("task_id")
            if task_id in self.available_tasks:
                del self.available_tasks[task_id]

        elif msg_type == "ROBOT_FAILURE_ALERT":
            failed_id = payload.get("robot_id", message.sender_id)
            self.failed_robots.add(failed_id)
            if failed_id in self.known_robots:
                self.known_robots[failed_id].status = "FAILED"

        elif msg_type == "HEARTBEAT":
            pos_raw = payload.get("position")
            if pos_raw:
                self.known_robots[message.sender_id] = KnownRobotInfo(
                    robot_id=message.sender_id,
                    position=(pos_raw[0], pos_raw[1]),
                    heading=payload.get("heading", "NORTH"),
                    is_carrying_pod=payload.get("is_carrying_pod", False),
                    status=payload.get("status", "IDLE"),
                    battery_level=payload.get("battery", 100.0),
                    last_observed_tick=current_tick,
                    planned_path=[(p[0], p[1]) for p in payload.get("planned_path", [])],
                )

    def is_cell_blocked(self, x: int, y: int, tick: int, ignore_self: bool = True) -> bool:
        """Evaluate if coordinate (x, y) at time `tick` is blocked in this local model."""
        # 1. Static walls & boundaries
        if not self.static_map.is_traversable(x, y):
            return True

        # 2. Known dynamic obstacles
        for obs in self.dynamic_obstacles.values():
            if obs.position == (x, y):
                if obs.estimated_expiration_tick is None or tick < obs.estimated_expiration_tick:
                    return True

        # 3. Known space-time reservations
        res_owner = self.reservations.get(((x, y), tick))
        if res_owner is not None:
            if not (ignore_self and res_owner == self.robot_id):
                return True

        return False

    def prune_stale_data(self, current_tick: int, max_staleness: int = 50) -> None:
        """Purge expired obstacles and outdated space-time reservations."""
        # Prune expired obstacles
        expired_obs = [
            obs_id for obs_id, obs in self.dynamic_obstacles.items()
            if obs.estimated_expiration_tick and current_tick >= obs.estimated_expiration_tick
        ]
        for obs_id in expired_obs:
            del self.dynamic_obstacles[obs_id]
            self.map_version += 1

        # Prune past reservations
        past_res = [
            key for key in self.reservations.keys()
            if key[1] < current_tick
        ]
        for key in past_res:
            del self.reservations[key]

        # Prune stale known robots
        stale_robots = [
            r_id for r_id, info in self.known_robots.items()
            if current_tick - info.last_observed_tick > max_staleness
        ]
        for r_id in stale_robots:
            del self.known_robots[r_id]

    def snapshot(self) -> Dict[str, Any]:
        """Create a point-in-time dictionary snapshot of the local world model."""
        return {
            "robot_id": self.robot_id,
            "last_update_time": self.last_update_time,
            "map_version": self.map_version,
            "dynamic_obstacles": {
                k: {
                    "obstacle_id": v.obstacle_id,
                    "position": list(v.position),
                    "obstacle_type": v.obstacle_type,
                    "first_observed_tick": v.first_observed_tick,
                    "last_observed_tick": v.last_observed_tick,
                    "estimated_expiration_tick": v.estimated_expiration_tick,
                }
                for k, v in self.dynamic_obstacles.items()
            },
            "known_robots": {
                k: {
                    "robot_id": v.robot_id,
                    "position": list(v.position),
                    "heading": v.heading,
                    "status": v.status,
                    "last_observed_tick": v.last_observed_tick,
                }
                for k, v in self.known_robots.items()
            },
            "reservations_count": len(self.reservations),
            "available_tasks_count": len(self.available_tasks),
            "failed_robots": list(self.failed_robots),
        }
