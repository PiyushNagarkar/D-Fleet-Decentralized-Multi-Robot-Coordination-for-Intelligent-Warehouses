"""Time-Expanded Space-Time Reservations and Path Planning for D-Fleet."""

from __future__ import annotations
from dataclasses import dataclass, field
import heapq
import math
from typing import Dict, List, Optional, Set, Tuple, Any

from app.simulation.warehouse import WarehouseGrid
from app.robots.local_world_model import LocalWorldModel

INF = float("inf")


@dataclass(frozen=True)
class ReservationRecord:
    """A space-time reservation record for a discrete grid cell at a specific tick."""
    owner: str
    cell: Tuple[int, int]
    time: int
    path_version: int = 1
    priority: int = 1
    ttl: int = 30  # Time-to-live in ticks from creation
    created_tick: int = 0

    def is_valid_at(self, current_tick: int) -> bool:
        """Check if reservation is still active and has not expired."""
        # 1. Past time steps are expired
        if self.time < current_tick:
            return False
        # 2. TTL elapsed from creation time
        if current_tick > self.created_tick + self.ttl:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner": self.owner,
            "cell": list(self.cell),
            "time": self.time,
            "path_version": self.path_version,
            "priority": self.priority,
            "ttl": self.ttl,
            "created_tick": self.created_tick,
        }


class ReservationTable:
    """Manages space-time reservations with automatic TTL-based pruning."""

    def __init__(self):
        # Key: ((x, y), time_tick) -> ReservationRecord
        self._reservations: Dict[Tuple[Tuple[int, int], int], ReservationRecord] = {}

    def add_reservation(self, record: ReservationRecord) -> None:
        self._reservations[(record.cell, record.time)] = record

    def add_reservations_for_path(
        self,
        owner: str,
        path: List[Tuple[int, int]],
        start_tick: int,
        priority: int = 1,
        path_version: int = 1,
        ttl: int = 30,
        created_tick: int = 0,
    ) -> List[ReservationRecord]:
        """Reserve all (cell, tick) tuples along a discrete trajectory."""
        records = []
        for i, cell in enumerate(path):
            tick = start_tick + i
            rec = ReservationRecord(
                owner=owner,
                cell=cell,
                time=tick,
                path_version=path_version,
                priority=priority,
                ttl=ttl,
                created_tick=created_tick,
            )
            self.add_reservation(rec)
            records.append(rec)
        return records

    def remove_reservations_for_owner(self, owner: str) -> None:
        to_delete = [k for k, v in self._reservations.items() if v.owner == owner]
        for k in to_delete:
            del self._reservations[k]

    def is_reserved(
        self,
        cell: Tuple[int, int],
        time: int,
        current_tick: int,
        ignore_owner: Optional[str] = None,
    ) -> bool:
        """Check if (cell, time) is reserved by an active, unexpired reservation."""
        rec = self._reservations.get((cell, time))
        if rec is None:
            return False

        # Ignore if reservation is owned by the querying robot
        if ignore_owner is not None and rec.owner == ignore_owner:
            return False

        # Safety Invariant: Expired reservations cannot block robots
        if not rec.is_valid_at(current_tick):
            return False

        return True

    def get_reservation(
        self,
        cell: Tuple[int, int],
        time: int,
        current_tick: int,
    ) -> Optional[ReservationRecord]:
        rec = self._reservations.get((cell, time))
        if rec and rec.is_valid_at(current_tick):
            return rec
        return None

    def prune_expired(self, current_tick: int) -> int:
        """Purge all expired reservations."""
        expired_keys = [
            k for k, v in self._reservations.items()
            if not v.is_valid_at(current_tick)
        ]
        for k in expired_keys:
            del self._reservations[k]
        return len(expired_keys)

    def to_list(self, current_tick: int) -> List[ReservationRecord]:
        return [
            v for v in self._reservations.values()
            if v.is_valid_at(current_tick)
        ]


class SpaceTimeAStar:
    """Time-expanded A* planner searching in (x, y, t) state space."""

    def __init__(
        self,
        warehouse: WarehouseGrid,
        max_time_horizon: int = 100,
    ):
        self.warehouse = warehouse
        self.max_time_horizon = max_time_horizon

    def heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return float(abs(a[0] - b[0]) + abs(a[1] - b[1]))

    def plan_space_time_path(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        start_tick: int,
        reservation_table: ReservationTable,
        world_model: Optional[LocalWorldModel] = None,
        ignore_owner: Optional[str] = None,
        current_tick: Optional[int] = None,
    ) -> Optional[List[Tuple[int, int]]]:
        """Search for a collision-free space-time trajectory from start to goal.

        Actions available at state (x, y, t):
        - Move to adjacent cell (nx, ny, t+1)
        - Wait in place (x, y, t+1)
        """
        eff_current_tick = start_tick if current_tick is None else current_tick

        # Priority queue item: (f_score, g_cost, (x, y, t))
        open_set: List[Tuple[float, float, Tuple[int, int, int]]] = []
        heapq.heappush(open_set, (self.heuristic(start, goal), 0.0, (start[0], start[1], start_tick)))

        g_score: Dict[Tuple[int, int, int], float] = {(start[0], start[1], start_tick): 0.0}
        came_from: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}

        max_tick = start_tick + self.max_time_horizon

        while open_set:
            f, cost, current = heapq.heappop(open_set)
            cx, cy, ct = current

            # Goal check
            if (cx, cy) == goal:
                # Reconstruct path
                path = []
                curr = current
                while curr in came_from:
                    path.append((curr[0], curr[1]))
                    curr = came_from[curr]
                path.append(start)
                path.reverse()
                return path

            if ct >= max_tick:
                continue

            # Candidate next states at ct + 1
            # 1. Cardinal movements
            cardinals = [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]
            # 2. Wait in place
            candidates = cardinals + [(cx, cy)]

            for nx, ny in candidates:
                nt = ct + 1

                # 1. Grid boundary and static wall check
                if not self.warehouse.is_traversable(nx, ny):
                    continue

                # 2. Dynamic obstacle check from local world model
                if world_model and world_model.is_cell_blocked(nx, ny, nt):
                    continue

                # 3. Vertex reservation check (cell reserved at nt)
                if reservation_table.is_reserved((nx, ny), nt, eff_current_tick, ignore_owner=ignore_owner):
                    continue

                # 4. Edge swap reservation check:
                # If moving (cx, cy) -> (nx, ny), check if another robot has reserved (cx, cy) at nt
                # and (nx, ny) at ct (head-on swap)
                if (nx, ny) != (cx, cy):
                    rec_next = reservation_table.get_reservation((cx, cy), nt, eff_current_tick)
                    rec_prev = reservation_table.get_reservation((nx, ny), ct, eff_current_tick)
                    if (
                        rec_next and rec_prev
                        and rec_next.owner == rec_prev.owner
                        and rec_next.owner != ignore_owner
                    ):
                        continue  # Edge collision

                # Cost evaluation (wait in place incurs small penalty to favor movement)
                step_cost = 1.0 if (nx, ny) != (cx, cy) else 1.05
                tentative_g = cost + step_cost
                next_state = (nx, ny, nt)

                if next_state not in g_score or tentative_g < g_score[next_state]:
                    g_score[next_state] = tentative_g
                    came_from[next_state] = current
                    h = self.heuristic((nx, ny), goal)
                    heapq.heappush(open_set, (tentative_g + h, tentative_g, next_state))

        return None  # No feasible space-time path found within horizon
