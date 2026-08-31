"""Autonomous Battery Management and Energy Optimization for Robots."""

from __future__ import annotations
from dataclasses import dataclass
import math
from typing import List, Optional, Tuple


@dataclass
class BatteryConfig:
    low_battery_threshold: float = 30.0       # Triggers seeking charging after completing current task step
    critical_battery_threshold: float = 15.0  # Immediate emergency detour to charger
    full_charge_threshold: float = 95.0       # Ready to rejoin task pool
    move_energy_cost: float = 0.1             # Base energy cost per grid step
    carry_move_energy_cost: float = 0.2       # Energy cost when carrying a pod
    wait_energy_cost: float = 0.01            # Energy cost when idling/waiting
    charge_rate_per_tick: float = 2.0         # Battery replenishment rate per tick


class BatteryManager:
    """Manages robot battery state, threshold checks, and charging navigation."""

    def __init__(self, config: Optional[BatteryConfig] = None):
        self.config = config or BatteryConfig()

    def should_seek_charging(self, battery_level: float) -> bool:
        """True if battery is below safe operational threshold."""
        return battery_level <= self.config.low_battery_threshold

    def is_critical(self, battery_level: float) -> bool:
        """True if battery is in critical reserve territory."""
        return battery_level <= self.config.critical_battery_threshold

    def is_fully_charged(self, battery_level: float) -> bool:
        """True if battery has recharged above full operating threshold."""
        return battery_level >= self.config.full_charge_threshold

    def find_nearest_charger(
        self,
        current_pos: Tuple[int, int],
        charging_stations: List[Tuple[int, int]],
    ) -> Optional[Tuple[int, int]]:
        """Find closest charging station using Manhattan distance."""
        if not charging_stations:
            return None

        return min(
            charging_stations,
            key=lambda c: abs(c[0] - current_pos[0]) + abs(c[1] - current_pos[1]),
        )

    def get_battery_penalty_for_bidding(self, battery_level: float) -> float:
        """Penalty for task bidding. Low battery heavily penalizes taking new tasks."""
        if battery_level <= self.config.critical_battery_threshold:
            return float("inf")  # Disallowed
        if battery_level <= self.config.low_battery_threshold:
            return 300.0  # Strong penalty to discourage winning tasks
        return (100.0 - battery_level) * 0.5

    def get_battery_urgency_for_negotiation(self, battery_level: float) -> float:
        """Urgency boost during conflict negotiation when battery is low."""
        if battery_level <= self.config.critical_battery_threshold:
            return 60.0
        if battery_level <= self.config.low_battery_threshold:
            return 30.0
        return max(0.0, (100.0 - battery_level) * 0.2)

    def evaluate_energy_feasibility(
        self,
        current_battery: float,
        pickup_dist: int,
        delivery_dist: int,
        charging_dist: int,
        is_carrying: bool = False,
        safety_reserve: float = 5.0,
    ) -> Tuple[bool, float, float]:
        """
        Evaluates whether a robot has sufficient battery to execute a task and safely reach a charger.
        Returns (can_safely_complete, required_energy, available_energy)
        """
        task_energy = (
            delivery_dist * self.config.carry_move_energy_cost
            if is_carrying
            else (pickup_dist * self.config.move_energy_cost + delivery_dist * self.config.carry_move_energy_cost)
        )
        charging_energy = charging_dist * self.config.move_energy_cost
        required_energy = round(task_energy + charging_energy, 4)
        available_energy = round(max(0.0, current_battery - safety_reserve), 4)
        can_safely_complete = available_energy >= required_energy
        return can_safely_complete, required_energy, available_energy

    def consume_energy(
        self,
        current_battery: float,
        is_moving: bool = True,
        is_carrying: bool = False,
    ) -> float:
        """Calculates updated battery level after an action."""
        if not is_moving:
            used = self.config.wait_energy_cost
        elif is_carrying:
            used = self.config.carry_move_energy_cost
        else:
            used = self.config.move_energy_cost

        return max(0.0, round(current_battery - used, 4))

    def apply_charge(self, current_battery: float) -> float:
        """Replenish battery during charging step."""
        return min(100.0, round(current_battery + self.config.charge_rate_per_tick, 4))
