"""Decentralized Task Bidding and Auction Evaluation.

Every robot calculates its own bid independently using local cost components
(distance, congestion, battery, workload, reroute) and task urgency.
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple, Any

from app.robots.state import RobotState, RobotStatus
from app.robots.local_world_model import LocalWorldModel
from .task import Task


class TaskBidder:
    """Computes utility-based bids for decentralized task allocation."""

    def __init__(
        self,
        min_battery_threshold: float = 20.0,
        congestion_radius: int = 4,
        congestion_weight: float = 1.5,
        battery_weight: float = 0.5,
    ):
        self.min_battery_threshold = min_battery_threshold
        self.congestion_radius = congestion_radius
        self.congestion_weight = congestion_weight
        self.battery_weight = battery_weight

    def compute_distance(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Manhattan distance between two 2D points."""
        return float(abs(a[0] - b[0]) + abs(a[1] - b[1]))

    def compute_congestion(
        self,
        target_pos: Tuple[int, int],
        world_model: LocalWorldModel,
    ) -> float:
        """Count known other robots within congestion radius of target position."""
        count = 0
        for peer_info in world_model.known_robots.values():
            if peer_info.robot_id != world_model.robot_id:
                dist = self.compute_distance(peer_info.position, target_pos)
                if dist <= self.congestion_radius:
                    count += 1
        return count * self.congestion_weight

    def compute_battery_penalty(self, battery_level: float) -> float:
        """Penalty increases sharply as battery drops toward reserve."""
        if battery_level <= self.min_battery_threshold:
            return float("inf")
        # Scaled penalty for battery depletion
        return (100.0 - battery_level) * self.battery_weight

    def compute_reroute_cost(
        self,
        robot_state: RobotState,
        pickup_pos: Tuple[int, int],
    ) -> float:
        """Additional penalty if robot must deviate from an active path."""
        if not robot_state.current_path:
            return 0.0
        # Distance from nearest path waypoint to new pickup
        min_dev = min(self.compute_distance(p, pickup_pos) for p in robot_state.current_path)
        return float(min_dev * 0.8)

    def compute_workload_penalty(self, robot_state: RobotState) -> float:
        """Heavy penalty if robot is already executing a task."""
        if robot_state.carrying_item or robot_state.status in (
            RobotStatus.MOVING_TO_PICKUP,
            RobotStatus.PICKED_UP,
            RobotStatus.MOVING_TO_DELIVERY,
        ):
            return 500.0
        elif robot_state.status in (RobotStatus.CHARGING, RobotStatus.LOW_BATTERY):
            return 200.0
        elif robot_state.status == RobotStatus.FAILED:
            return float("inf")
        return 0.0

    def compute_urgency(self, task: Task, current_tick: int) -> float:
        """Calculates urgency boost based on task priority and deadline."""
        base_urgency = float(task.priority * 10.0)
        if task.deadline_tick is not None:
            ticks_left = max(1, task.deadline_tick - current_tick)
            base_urgency += max(0.0, 100.0 / ticks_left)
        return base_urgency

    def compute_bid(
        self,
        robot_state: RobotState,
        world_model: LocalWorldModel,
        task: Task,
        current_tick: int,
    ) -> Optional[float]:
        """Compute independent bid for a given task.
        
        cost = distance_to_pickup + distance_to_delivery + congestion + battery_penalty
               + workload + reroute_cost
        bid = -cost + urgency
        """
        # Disallow bidding if robot is failed or below reserve battery
        if robot_state.status == RobotStatus.FAILED or robot_state.battery <= self.min_battery_threshold:
            return None

        distance_to_pickup = self.compute_distance(robot_state.position, task.pickup_location)
        distance_to_delivery = self.compute_distance(task.pickup_location, task.delivery_location)
        congestion = self.compute_congestion(task.pickup_location, world_model)
        battery_penalty = self.compute_battery_penalty(robot_state.battery)
        workload = self.compute_workload_penalty(robot_state)
        reroute_cost = self.compute_reroute_cost(robot_state, task.pickup_location)

        total_cost = (
            distance_to_pickup
            + distance_to_delivery
            + congestion
            + battery_penalty
            + workload
            + reroute_cost
        )

        if math.isinf(total_cost):
            return None

        urgency = self.compute_urgency(task, current_tick)
        bid = -total_cost + urgency
        return round(bid, 4)

    @staticmethod
    def evaluate_winner(bids: Dict[str, float]) -> Optional[str]:
        """Determine auction winner.
        
        Winner = highest bid; tie broken deterministically by lowest robot_id (lexicographically).
        """
        if not bids:
            return None

        # Sort by: 1) bid descending (-bid), 2) robot_id ascending (lexicographical)
        sorted_bidders = sorted(bids.items(), key=lambda item: (-item[1], str(item[0])))
        return sorted_bidders[0][0]
