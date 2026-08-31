"""Physics, spatial movement execution, and physical state management."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
from .warehouse import WarehouseGrid, CellType, grid_to_world


class Direction(str, Enum):
    NORTH = "NORTH"  # y - 1
    SOUTH = "SOUTH"  # y + 1
    EAST = "EAST"    # x + 1
    WEST = "WEST"    # x - 1


DIRECTION_VECTORS: Dict[Direction, Tuple[int, int]] = {
    Direction.NORTH: (0, -1),
    Direction.SOUTH: (0, 1),
    Direction.EAST: (1, 0),
    Direction.WEST: (-1, 0),
}


class ActionType(str, Enum):
    MOVE_NORTH = "MOVE_NORTH"
    MOVE_SOUTH = "MOVE_SOUTH"
    MOVE_EAST = "MOVE_EAST"
    MOVE_WEST = "MOVE_WEST"
    WAIT = "WAIT"
    PICKUP = "PICKUP"
    DROPOFF = "DROPOFF"
    CHARGE = "CHARGE"


class PhysicalStatus(str, Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    WAITING = "WAITING"
    CHARGING = "CHARGING"
    FAILED = "FAILED"


@dataclass
class RobotPhysicalState:
    """True physical state of a robot in the simulation."""
    robot_id: str
    x: int
    y: int
    heading: Direction = Direction.NORTH
    battery_level: float = 100.0        # 0.0 to 100.0%
    is_carrying_pod: bool = False
    carried_item_id: Optional[str] = None
    status: PhysicalStatus = PhysicalStatus.IDLE
    is_failed: bool = False
    failure_reason: Optional[str] = None
    total_distance_moved: float = 0.0
    total_energy_consumed: float = 0.0

    @property
    def world_position(self) -> Tuple[float, float, float]:
        return grid_to_world(self.x, self.y)

    def to_dict(self) -> Dict[str, Any]:
        world_x, world_y, world_z = self.world_position
        return {
            "robot_id": self.robot_id,
            "grid_position": [self.x, self.y],
            "world_position": [world_x, world_y, world_z],
            "heading": self.heading.value,
            "battery_level": round(self.battery_level, 2),
            "is_carrying_pod": self.is_carrying_pod,
            "carried_item_id": self.carried_item_id,
            "status": self.status.value,
            "is_failed": self.is_failed,
            "failure_reason": self.failure_reason,
            "total_distance_moved": round(self.total_distance_moved, 2),
            "total_energy_consumed": round(self.total_energy_consumed, 2),
        }


@dataclass
class ActionResult:
    """Result of applying a physical action in the simulation engine."""
    success: bool
    robot_id: str
    action: ActionType
    old_position: Tuple[int, int]
    new_position: Tuple[int, int]
    battery_delta: float
    message: str = ""
    collision_with_robot_id: Optional[str] = None
    collision_with_obstacle: bool = False


class PhysicsEngine:
    """Pure environment physics and kinematics evaluator.
    
    CRITICAL: Does NOT decide actions or paths. Only validates and applies
    physical actions submitted by independent robot agents.
    """

    def __init__(
        self,
        warehouse: WarehouseGrid,
        move_energy_cost: float = 0.1,
        carry_move_energy_cost: float = 0.2,
        idle_energy_cost: float = 0.01,
        charge_rate_per_tick: float = 2.0,
    ):
        self.warehouse = warehouse
        self.move_energy_cost = move_energy_cost
        self.carry_move_energy_cost = carry_move_energy_cost
        self.idle_energy_cost = idle_energy_cost
        self.charge_rate_per_tick = charge_rate_per_tick
        self.robots: Dict[str, RobotPhysicalState] = {}

    def spawn_robot(
        self,
        robot_id: str,
        x: int,
        y: int,
        heading: Direction = Direction.NORTH,
        battery_level: float = 100.0,
    ) -> RobotPhysicalState:
        """Register and place a robot at physical coordinates."""
        if not self.warehouse.is_traversable(x, y):
            raise ValueError(f"Spawn position ({x}, {y}) is not traversable on warehouse grid")
        
        for r_id, state in self.robots.items():
            if state.x == x and state.y == y:
                raise ValueError(f"Spawn position ({x}, {y}) is already occupied by robot {r_id}")

        state = RobotPhysicalState(
            robot_id=robot_id,
            x=x,
            y=y,
            heading=heading,
            battery_level=battery_level,
        )
        self.robots[robot_id] = state
        return state

    def remove_robot(self, robot_id: str) -> bool:
        if robot_id in self.robots:
            del self.robots[robot_id]
            return True
        return False

    def inject_failure(self, robot_id: str, reason: str = "Hardware Fault") -> bool:
        """Simulate a sudden robot hardware failure."""
        if robot_id in self.robots:
            robot = self.robots[robot_id]
            robot.is_failed = True
            robot.status = PhysicalStatus.FAILED
            robot.failure_reason = reason
            return True
        return False

    def recover_robot(self, robot_id: str) -> bool:
        """Recover a failed robot back to operational status."""
        if robot_id in self.robots:
            robot = self.robots[robot_id]
            robot.is_failed = False
            robot.status = PhysicalStatus.IDLE
            robot.failure_reason = None
            return True
        return False

    def get_occupied_positions(self) -> Dict[Tuple[int, int], str]:
        """Map of (x, y) -> robot_id for all current robots."""
        return {(r.x, r.y): r.robot_id for r in self.robots.values()}

    def execute_action(
        self,
        robot_id: str,
        action: ActionType,
        dynamic_obstacles: Set[Tuple[int, int]],
        item_id: Optional[str] = None,
    ) -> ActionResult:
        """Execute a physical action for a single robot against physical constraints."""
        robot = self.robots.get(robot_id)
        if not robot:
            return ActionResult(
                success=False,
                robot_id=robot_id,
                action=action,
                old_position=(0, 0),
                new_position=(0, 0),
                battery_delta=0.0,
                message=f"Robot {robot_id} not found in physics engine",
            )

        old_pos = (robot.x, robot.y)

        # Check if robot is hardware failed or battery depleted
        if robot.is_failed:
            return ActionResult(
                success=False,
                robot_id=robot_id,
                action=action,
                old_position=old_pos,
                new_position=old_pos,
                battery_delta=0.0,
                message=f"Robot {robot_id} is failed: {robot.failure_reason}",
            )

        if robot.battery_level <= 0.0:
            robot.status = PhysicalStatus.FAILED
            robot.is_failed = True
            robot.failure_reason = "Battery Depleted"
            return ActionResult(
                success=False,
                robot_id=robot_id,
                action=action,
                old_position=old_pos,
                new_position=old_pos,
                battery_delta=0.0,
                message=f"Robot {robot_id} battery depleted",
            )

        # Handle movement actions
        move_directions = {
            ActionType.MOVE_NORTH: Direction.NORTH,
            ActionType.MOVE_SOUTH: Direction.SOUTH,
            ActionType.MOVE_EAST: Direction.EAST,
            ActionType.MOVE_WEST: Direction.WEST,
        }

        if action in move_directions:
            direction = move_directions[action]
            dx, dy = DIRECTION_VECTORS[direction]
            target_x, target_y = robot.x + dx, robot.y + dy
            target_pos = (target_x, target_y)

            # 1. Grid boundary and wall check
            if not self.warehouse.is_traversable(target_x, target_y):
                energy_used = self.idle_energy_cost
                robot.battery_level = max(0.0, robot.battery_level - energy_used)
                robot.total_energy_consumed += energy_used
                return ActionResult(
                    success=False,
                    robot_id=robot_id,
                    action=action,
                    old_position=old_pos,
                    new_position=old_pos,
                    battery_delta=-energy_used,
                    message=f"Move blocked by static wall/boundary at {target_pos}",
                )

            # 2. Dynamic obstacle check
            if target_pos in dynamic_obstacles:
                energy_used = self.idle_energy_cost
                robot.battery_level = max(0.0, robot.battery_level - energy_used)
                robot.total_energy_consumed += energy_used
                return ActionResult(
                    success=False,
                    robot_id=robot_id,
                    action=action,
                    old_position=old_pos,
                    new_position=old_pos,
                    battery_delta=-energy_used,
                    collision_with_obstacle=True,
                    message=f"Move blocked by dynamic obstacle at {target_pos}",
                )

            # 3. Other robot occupancy check
            occupied = self.get_occupied_positions()
            if target_pos in occupied and occupied[target_pos] != robot_id:
                other_id = occupied[target_pos]
                energy_used = self.idle_energy_cost
                robot.battery_level = max(0.0, robot.battery_level - energy_used)
                robot.total_energy_consumed += energy_used
                return ActionResult(
                    success=False,
                    robot_id=robot_id,
                    action=action,
                    old_position=old_pos,
                    new_position=old_pos,
                    battery_delta=-energy_used,
                    collision_with_robot_id=other_id,
                    message=f"Move blocked by robot {other_id} at {target_pos}",
                )

            # Physical movement succeeds
            robot.x = target_x
            robot.y = target_y
            robot.heading = direction
            robot.status = PhysicalStatus.MOVING
            robot.total_distance_moved += 1.0

            energy_used = (
                self.carry_move_energy_cost
                if robot.is_carrying_pod
                else self.move_energy_cost
            )
            robot.battery_level = max(0.0, robot.battery_level - energy_used)
            robot.total_energy_consumed += energy_used

            return ActionResult(
                success=True,
                robot_id=robot_id,
                action=action,
                old_position=old_pos,
                new_position=target_pos,
                battery_delta=-energy_used,
                message=f"Moved to {target_pos}",
            )

        elif action == ActionType.WAIT:
            robot.status = PhysicalStatus.WAITING
            energy_used = self.idle_energy_cost
            robot.battery_level = max(0.0, robot.battery_level - energy_used)
            robot.total_energy_consumed += energy_used
            return ActionResult(
                success=True,
                robot_id=robot_id,
                action=action,
                old_position=old_pos,
                new_position=old_pos,
                battery_delta=-energy_used,
                message="Wait completed",
            )

        elif action == ActionType.CHARGE:
            cell_type = self.warehouse.get_cell(robot.x, robot.y)
            if cell_type != CellType.CHARGING:
                energy_used = self.idle_energy_cost
                robot.battery_level = max(0.0, robot.battery_level - energy_used)
                return ActionResult(
                    success=False,
                    robot_id=robot_id,
                    action=action,
                    old_position=old_pos,
                    new_position=old_pos,
                    battery_delta=-energy_used,
                    message=f"Cannot charge at cell {old_pos} (not a charging station)",
                )

            charge_added = min(self.charge_rate_per_tick, 100.0 - robot.battery_level)
            robot.battery_level = min(100.0, robot.battery_level + charge_added)
            robot.status = PhysicalStatus.CHARGING
            return ActionResult(
                success=True,
                robot_id=robot_id,
                action=action,
                old_position=old_pos,
                new_position=old_pos,
                battery_delta=charge_added,
                message=f"Charged +{charge_added:.2f}%, current: {robot.battery_level:.2f}%",
            )

        elif action == ActionType.PICKUP:
            cell_type = self.warehouse.get_cell(robot.x, robot.y)
            if robot.is_carrying_pod:
                return ActionResult(
                    success=False,
                    robot_id=robot_id,
                    action=action,
                    old_position=old_pos,
                    new_position=old_pos,
                    battery_delta=0.0,
                    message="Already carrying a pod",
                )
            if cell_type != CellType.PICKUP:
                return ActionResult(
                    success=False,
                    robot_id=robot_id,
                    action=action,
                    old_position=old_pos,
                    new_position=old_pos,
                    battery_delta=0.0,
                    message="Pickup action failed: Not at a pickup station",
                )

            robot.is_carrying_pod = True
            robot.carried_item_id = item_id or "pod_default"
            return ActionResult(
                success=True,
                robot_id=robot_id,
                action=action,
                old_position=old_pos,
                new_position=old_pos,
                battery_delta=0.0,
                message=f"Picked up pod {robot.carried_item_id}",
            )

        elif action == ActionType.DROPOFF:
            cell_type = self.warehouse.get_cell(robot.x, robot.y)
            if not robot.is_carrying_pod:
                return ActionResult(
                    success=False,
                    robot_id=robot_id,
                    action=action,
                    old_position=old_pos,
                    new_position=old_pos,
                    battery_delta=0.0,
                    message="Not carrying any pod to drop off",
                )
            if cell_type != CellType.DELIVERY:
                return ActionResult(
                    success=False,
                    robot_id=robot_id,
                    action=action,
                    old_position=old_pos,
                    new_position=old_pos,
                    battery_delta=0.0,
                    message="Dropoff action failed: Not at a delivery station",
                )

            dropped_id = robot.carried_item_id
            robot.is_carrying_pod = False
            robot.carried_item_id = None
            return ActionResult(
                success=True,
                robot_id=robot_id,
                action=action,
                old_position=old_pos,
                new_position=old_pos,
                battery_delta=0.0,
                message=f"Dropped off pod {dropped_id}",
            )

        return ActionResult(
            success=False,
            robot_id=robot_id,
            action=action,
            old_position=old_pos,
            new_position=old_pos,
            battery_delta=0.0,
            message="Unknown action",
        )
