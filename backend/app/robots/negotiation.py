"""Decentralized Peer-to-Peer Negotiation and Priority Aging for Autonomous Robots."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Dict, List, Optional, Tuple, Any

from .state import RobotState, RobotStatus
from .local_world_model import LocalWorldModel


class NegotiationOutcome(str, Enum):
    GRANT = "GRANT"      # Grant contested resource to peer
    WAIT = "WAIT"        # Pause in place for 1+ ticks to let peer pass
    YIELD = "YIELD"      # Step aside or vacate cell for higher-priority peer
    REROUTE = "REROUTE"  # Compute alternative detour path
    REJECT = "REJECT"    # Reject peer request (retain own reservation)


@dataclass
class PriorityWeights:
    w_urgency: float = 2.0
    w_battery: float = 1.5
    w_waiting: float = 1.2
    w_progress: float = 1.0
    w_reroute: float = 0.8
    aging_factor: float = 0.5   # f(waiting_time) bonus per waiting tick


class PriorityCalculator:
    """Computes dynamic priority and anti-starvation effective priority for a robot."""

    def __init__(self, weights: Optional[PriorityWeights] = None):
        self.weights = weights or PriorityWeights()

    def compute_urgency(self, state: RobotState) -> float:
        """Urgency derived from base priority and active task status."""
        urgency = float(state.priority * 10.0)
        if state.status in (RobotStatus.MOVING_TO_PICKUP, RobotStatus.MOVING_TO_DELIVERY):
            urgency += 15.0
        if state.carrying_item:
            urgency += 10.0
        return urgency

    def compute_battery_urgency(self, battery_level: float) -> float:
        """Urgency is higher if battery is low (needs to reach charger urgently)."""
        if battery_level <= 20.0:
            return 50.0  # Critical
        if battery_level <= 40.0:
            return 25.0
        return max(0.0, (100.0 - battery_level) * 0.2)

    def compute_progress(self, state: RobotState) -> float:
        """Higher priority given to robots that have already completed more of their path."""
        if not state.current_path:
            return 0.0
        # More progress = higher investment
        return float(state.path_version * 2.0)

    def compute_base_priority(
        self,
        state: RobotState,
        waiting_time: int = 0,
        rerouting_cost: float = 0.0,
    ) -> float:
        """
        priority = w1*urgency + w2*battery_urgency + w3*waiting_time + w4*progress
                   - w5*rerouting_cost
        """
        w = self.weights
        urgency = self.compute_urgency(state)
        battery_urgency = self.compute_battery_urgency(state.battery)
        progress = self.compute_progress(state)

        base_p = (
            w.w_urgency * urgency
            + w.w_battery * battery_urgency
            + w.w_waiting * float(waiting_time)
            + w.w_progress * progress
            - w.w_reroute * rerouting_cost
        )
        return round(base_p, 4)

    def compute_effective_priority(
        self,
        state: RobotState,
        waiting_time: int = 0,
        yield_count: int = 0,
        recent_yield_penalty: float = 0.0,
        rerouting_cost: float = 0.0,
    ) -> float:
        """
        effective_priority = base_priority + f(waiting_time) + yield_compensation - recent_yield_penalty
        Ensures a robot that repeatedly waits or yields rises in priority and cannot starve.
        """
        base_p = self.compute_base_priority(state, waiting_time, rerouting_cost)
        aging_bonus = self.weights.aging_factor * float(waiting_time)
        yield_compensation = float(yield_count * 5.0)  # Boost priority for each recent yield
        
        effective_p = base_p + aging_bonus + yield_compensation - recent_yield_penalty
        return round(effective_p, 4)


class NegotiationEngine:
    """Decentralized negotiation evaluator operated privately by each robot."""

    def __init__(
        self,
        robot_id: str,
        priority_calculator: Optional[PriorityCalculator] = None,
    ):
        self.robot_id = robot_id
        self.calculator = priority_calculator or PriorityCalculator()
        self.waiting_time: int = 0
        self.yield_count: int = 0
        self.recent_yield_penalty: float = 0.0

    def increment_waiting_tick(self) -> int:
        self.waiting_time += 1
        # Slowly decay any recent yield penalty
        self.recent_yield_penalty = max(0.0, self.recent_yield_penalty - 0.5)
        return self.waiting_time

    def record_yield(self) -> None:
        """Called when this robot yields a contested cell."""
        self.yield_count += 1
        self.waiting_time = 0
        # Temporary penalty so other robots can pass, offset by future aging
        self.recent_yield_penalty = 5.0

    def record_win(self) -> None:
        """Called when this robot wins a negotiation."""
        self.waiting_time = 0
        self.yield_count = max(0, self.yield_count - 1)

    def get_my_effective_priority(
        self,
        state: RobotState,
        rerouting_cost: float = 0.0,
    ) -> float:
        return self.calculator.compute_effective_priority(
            state=state,
            waiting_time=self.waiting_time,
            yield_count=self.yield_count,
            recent_yield_penalty=self.recent_yield_penalty,
            rerouting_cost=rerouting_cost,
        )

    def evaluate_reservation_contest(
        self,
        my_state: RobotState,
        peer_id: str,
        peer_effective_priority: float,
        my_rerouting_cost: float = 0.0,
    ) -> NegotiationOutcome:
        """Locally determine negotiation outcome between self and peer for a contested cell/tick.

        Decided locally by comparing effective priority, breaking exact ties deterministically
        by lowest robot_id.
        """
        my_eff_priority = self.get_my_effective_priority(my_state, my_rerouting_cost)

        # Compare effective priorities
        if abs(my_eff_priority - peer_effective_priority) > 1e-4:
            i_win = my_eff_priority > peer_effective_priority
        else:
            # Deterministic tie-breaker: lower robot_id wins
            i_win = self.robot_id < peer_id

        if i_win:
            self.record_win()
            return NegotiationOutcome.REJECT  # Reject peer request, retain reservation
        else:
            self.record_yield()
            # If rerouting is feasible and cheap, choose REROUTE, else YIELD or WAIT
            if my_rerouting_cost > 0 and my_rerouting_cost < 15.0:
                return NegotiationOutcome.REROUTE
            return NegotiationOutcome.YIELD
