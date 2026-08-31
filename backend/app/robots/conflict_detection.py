"""Decentralized Multi-Type Conflict Detection for Autonomous Robots.

Detects Vertex, Edge, Following (tailgating), Future Convergence, and Narrow-Aisle
Head-On conflicts strictly using a robot's local knowledge.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any

from app.simulation.warehouse import WarehouseGrid
from app.robots.local_world_model import LocalWorldModel
from app.planning.reservation_planner import ReservationTable, ReservationRecord


class ConflictType(str, Enum):
    VERTEX_CONFLICT = "VERTEX_CONFLICT"
    EDGE_CONFLICT = "EDGE_CONFLICT"
    FOLLOWING_CONFLICT = "FOLLOWING_CONFLICT"
    FUTURE_CONFLICT = "FUTURE_CONFLICT"
    NARROW_AISLE_HEAD_ON = "NARROW_AISLE_HEAD_ON"


@dataclass
class Conflict:
    """Represents a predicted spatial or temporal trajectory conflict between robots."""
    conflict_type: ConflictType
    robot_id_1: str
    robot_id_2: str
    location: Tuple[int, int]
    time_tick: int
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_type": self.conflict_type.value,
            "robot_id_1": self.robot_id_1,
            "robot_id_2": self.robot_id_2,
            "location": list(self.location),
            "time_tick": self.time_tick,
            "details": self.details,
        }


class ConflictDetector:
    """Dedicated detectors for each decentralized conflict category."""

    def __init__(
        self,
        min_following_headway: int = 1,  # Minimum safe steps between robots in narrow corridors
    ):
        self.min_following_headway = min_following_headway

    def is_narrow_aisle(self, grid: WarehouseGrid, x: int, y: int) -> bool:
        """Check if (x, y) is in a single-lane narrow aisle (constrained laterally)."""
        if not grid.is_traversable(x, y):
            return False
        
        # Horizontal corridor: top and bottom are walls
        horiz_walled = not grid.is_traversable(x, y - 1) and not grid.is_traversable(x, y + 1)
        # Vertical corridor: left and right are walls
        vert_walled = not grid.is_traversable(x - 1, y) and not grid.is_traversable(x + 1, y)
        
        return horiz_walled or vert_walled

    def detect_vertex_conflicts(
        self,
        robot_id: str,
        path: List[Tuple[int, int]],
        start_tick: int,
        peer_reservations: List[ReservationRecord],
    ) -> List[Conflict]:
        """Detect Vertex Conflict: Two robots occupying the exact same cell at the exact same tick."""
        conflicts = []
        for i, cell in enumerate(path):
            t = start_tick + i
            for rec in peer_reservations:
                if rec.owner != robot_id and rec.cell == cell and abs(rec.time - t) <= 1:
                    conflicts.append(
                        Conflict(
                            conflict_type=ConflictType.VERTEX_CONFLICT,
                            robot_id_1=robot_id,
                            robot_id_2=rec.owner,
                            location=cell,
                            time_tick=t,
                            details={"reason": f"Vertex collision at cell {cell} at tick {t}"},
                        )
                    )
        return conflicts

    def detect_edge_conflicts(
        self,
        robot_id: str,
        path: List[Tuple[int, int]],
        start_tick: int,
        peer_paths: Dict[str, Tuple[List[Tuple[int, int]], int]],
    ) -> List[Conflict]:
        """Detect Edge Conflict: Two robots swapping cells across consecutive ticks (head-on swap).
        
        p1(t) == p2(t+1) and p1(t+1) == p2(t)
        """
        conflicts = []
        for i in range(len(path) - 1):
            p1_curr = path[i]
            p1_next = path[i + 1]
            t = start_tick + i

            for peer_id, (peer_path, peer_start_tick) in peer_paths.items():
                if peer_id == robot_id:
                    continue

                for j in range(len(peer_path) - 1):
                    peer_t = peer_start_tick + j
                    if abs(peer_t - t) <= 1:
                        p2_curr = peer_path[j]
                        p2_next = peer_path[j + 1]

                        if (p1_curr == p2_next and p1_next == p2_curr) or (p1_next == p2_next):
                            conflicts.append(
                                Conflict(
                                    conflict_type=ConflictType.EDGE_CONFLICT if p1_curr == p2_next else ConflictType.VERTEX_CONFLICT,
                                    robot_id_1=robot_id,
                                    robot_id_2=peer_id,
                                    location=p1_next,
                                    time_tick=t + 1,
                                    details={
                                        "swap_from": p1_curr,
                                        "swap_to": p1_next,
                                        "tick": t + 1,
                                    },
                                )
                            )
        return conflicts

    def detect_following_conflicts(
        self,
        robot_id: str,
        path: List[Tuple[int, int]],
        start_tick: int,
        peer_paths: Dict[str, Tuple[List[Tuple[int, int]], int]],
        grid: Optional[WarehouseGrid] = None,
    ) -> List[Conflict]:
        """Detect Following Conflict: Tailgating or entering a narrow aisle too closely behind another."""
        conflicts = []
        for i in range(len(path)):
            my_pos = path[i]
            t = start_tick + i

            for peer_id, (peer_path, peer_start_tick) in peer_paths.items():
                if peer_id == robot_id:
                    continue

                # Check if peer occupied my position at t - 1 (tailgating directly behind)
                for j in range(len(peer_path)):
                    peer_t = peer_start_tick + j
                    peer_pos = peer_path[j]

                    # In a narrow aisle, if peer is directly ahead at same tick with distance < min_headway
                    if peer_t == t and grid and self.is_narrow_aisle(grid, my_pos[0], my_pos[1]):
                        dist = abs(my_pos[0] - peer_pos[0]) + abs(my_pos[1] - peer_pos[1])
                        if 0 < dist <= self.min_following_headway:
                            conflicts.append(
                                Conflict(
                                    conflict_type=ConflictType.FOLLOWING_CONFLICT,
                                    robot_id_1=robot_id,
                                    robot_id_2=peer_id,
                                    location=my_pos,
                                    time_tick=t,
                                    details={
                                        "headway_distance": dist,
                                        "min_required": self.min_following_headway + 1,
                                    },
                                )
                            )
        return conflicts

    def detect_future_conflicts(
        self,
        robot_id: str,
        path: List[Tuple[int, int]],
        start_tick: int,
        peer_paths: Dict[str, Tuple[List[Tuple[int, int]], int]],
        current_tick: int,
    ) -> List[Conflict]:
        """Detect Future Conflict: Currently separate paths converging at a shared cell at future tick > current_tick."""
        conflicts = []
        for i, cell in enumerate(path):
            t = start_tick + i
            if t <= current_tick:
                continue

            for peer_id, (peer_path, peer_start_tick) in peer_paths.items():
                if peer_id == robot_id:
                    continue

                for j, peer_cell in enumerate(peer_path):
                    peer_t = peer_start_tick + j
                    if peer_t == t and peer_cell == cell:
                        conflicts.append(
                            Conflict(
                                conflict_type=ConflictType.FUTURE_CONFLICT,
                                robot_id_1=robot_id,
                                robot_id_2=peer_id,
                                location=cell,
                                time_tick=t,
                                details={
                                    "future_tick": t,
                                    "ticks_ahead": t - current_tick,
                                },
                            )
                        )
        return conflicts

    def detect_narrow_aisle_head_on_conflicts(
        self,
        robot_id: str,
        path: List[Tuple[int, int]],
        start_tick: int,
        peer_paths: Dict[str, Tuple[List[Tuple[int, int]], int]],
        grid: WarehouseGrid,
    ) -> List[Conflict]:
        """Detect Narrow-Aisle Head-On Conflict: Opposing paths entering the same single-lane corridor."""
        conflicts = []
        for peer_id, (peer_path, peer_start_tick) in peer_paths.items():
            if peer_id == robot_id:
                continue

            # Identify overlapping cells in single-lane narrow aisle
            overlapping_narrow_cells = [
                cell for cell in path
                if cell in peer_path and self.is_narrow_aisle(grid, cell[0], cell[1])
            ]

            if len(overlapping_narrow_cells) >= 2:
                # Check direction of traversal
                my_idx_0 = path.index(overlapping_narrow_cells[0])
                my_idx_1 = path.index(overlapping_narrow_cells[-1])

                peer_idx_0 = peer_path.index(overlapping_narrow_cells[0])
                peer_idx_1 = peer_path.index(overlapping_narrow_cells[-1])

                # If indices are in reverse order, trajectories are head-on opposing
                if (my_idx_1 > my_idx_0 and peer_idx_1 < peer_idx_0) or (
                    my_idx_1 < my_idx_0 and peer_idx_1 > peer_idx_0
                ):
                    conflicts.append(
                        Conflict(
                            conflict_type=ConflictType.NARROW_AISLE_HEAD_ON,
                            robot_id_1=robot_id,
                            robot_id_2=peer_id,
                            location=overlapping_narrow_cells[0],
                            time_tick=start_tick,
                            details={
                                "narrow_segment": [list(c) for c in overlapping_narrow_cells],
                                "reason": "Opposing motion in single-lane aisle",
                            },
                        )
                    )
        return conflicts

    def detect_all_conflicts(
        self,
        robot_id: str,
        path: List[Tuple[int, int]],
        start_tick: int,
        world_model: LocalWorldModel,
        peer_paths: Optional[Dict[str, Tuple[List[Tuple[int, int]], int]]] = None,
        current_tick: Optional[int] = None,
    ) -> List[Conflict]:
        """Run all dedicated conflict detectors against local world model knowledge."""
        eff_current_tick = start_tick if current_tick is None else current_tick
        peer_paths = peer_paths or {}

        # Reconstruct peer paths from known robots if not explicitly provided
        for p_id, p_info in world_model.known_robots.items():
            if p_id != robot_id and p_info.planned_path and p_id not in peer_paths:
                peer_paths[p_id] = (p_info.planned_path, p_info.last_observed_tick)

        # Convert known reservations to records
        peer_reservations = []
        for ((rx, ry), rtick), owner in world_model.reservations.items():
            if owner != robot_id:
                peer_reservations.append(
                    ReservationRecord(
                        owner=owner,
                        cell=(rx, ry),
                        time=rtick,
                        created_tick=world_model.last_update_time,
                        ttl=50,
                    )
                )

        conflicts: List[Conflict] = []

        # 1. Vertex Conflicts
        conflicts.extend(
            self.detect_vertex_conflicts(robot_id, path, start_tick, peer_reservations)
        )

        # 2. Edge Conflicts
        conflicts.extend(
            self.detect_edge_conflicts(robot_id, path, start_tick, peer_paths)
        )

        # 3. Following Conflicts
        conflicts.extend(
            self.detect_following_conflicts(
                robot_id, path, start_tick, peer_paths, grid=world_model.static_map
            )
        )

        # 4. Future Conflicts
        conflicts.extend(
            self.detect_future_conflicts(
                robot_id, path, start_tick, peer_paths, current_tick=eff_current_tick
            )
        )

        # 5. Narrow-Aisle Head-On Conflicts
        conflicts.extend(
            self.detect_narrow_aisle_head_on_conflicts(
                robot_id, path, start_tick, peer_paths, grid=world_model.static_map
            )
        )

        return conflicts
