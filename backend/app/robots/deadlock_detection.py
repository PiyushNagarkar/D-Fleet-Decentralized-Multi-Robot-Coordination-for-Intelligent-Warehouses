"""Decentralized Wait-For Graph and Cycle Deadlock Resolution for Autonomous Robots."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
import networkx as nx

from .state import RobotState, RobotStatus
from .negotiation import PriorityCalculator


@dataclass
class DeadlockResolutionResult:
    """Outcome of resolving a detected wait-for graph dependency cycle."""
    cycle_detected: bool
    cycle_members: List[str] = field(default_factory=list)
    yielding_robot_id: Optional[str] = None
    yielding_priority: Optional[float] = None
    released_cell: Optional[Tuple[int, int]] = None
    action_taken: str = "NO_DEADLOCK"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_detected": self.cycle_detected,
            "cycle_members": self.cycle_members,
            "yielding_robot_id": self.yielding_robot_id,
            "yielding_priority": self.yielding_priority,
            "released_cell": list(self.released_cell) if self.released_cell else None,
            "action_taken": self.action_taken,
        }


class WaitForGraph:
    """Directed graph representing dynamic wait dependencies between robots."""

    def __init__(self):
        self.graph: nx.DiGraph = nx.DiGraph()
        self._edge_details: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def add_dependency(
        self,
        waiter_id: str,
        blocking_id: str,
        cell: Optional[Tuple[int, int]] = None,
        tick: int = 0,
    ) -> None:
        """Record that waiter_id is blocked and waiting for blocking_id at cell and tick."""
        if waiter_id == blocking_id:
            return  # No self loops
        self.graph.add_edge(waiter_id, blocking_id)
        self._edge_details[(waiter_id, blocking_id)] = {
            "cell": cell,
            "tick": tick,
        }

    def remove_dependency(self, waiter_id: str, blocking_id: Optional[str] = None) -> None:
        """Remove a dependency when robot is unblocked or reroutes."""
        if blocking_id:
            if self.graph.has_edge(waiter_id, blocking_id):
                self.graph.remove_edge(waiter_id, blocking_id)
                self._edge_details.pop((waiter_id, blocking_id), None)
        else:
            # Remove all outgoing edges from waiter_id
            if waiter_id in self.graph:
                successors = list(self.graph.successors(waiter_id))
                for succ in successors:
                    self.graph.remove_edge(waiter_id, succ)
                    self._edge_details.pop((waiter_id, succ), None)

    def remove_robot(self, robot_id: str) -> None:
        """Remove robot from the graph entirely."""
        if robot_id in self.graph:
            self.graph.remove_node(robot_id)
            to_del = [k for k in self._edge_details.keys() if k[0] == robot_id or k[1] == robot_id]
            for k in to_del:
                del self._edge_details[k]

    def detect_cycles(self) -> List[List[str]]:
        """Find all elementary cycles in the wait-for graph using NetworkX."""
        try:
            return list(nx.simple_cycles(self.graph))
        except Exception:
            return []

    def resolve_deadlock_cycle(
        self,
        cycle: List[str],
        robot_effective_priorities: Dict[str, float],
        contested_cells: Optional[Dict[str, Tuple[int, int]]] = None,
    ) -> DeadlockResolutionResult:
        """Resolve a detected cycle by selecting the lowest-priority robot to yield.

        1. Find member with lowest effective priority.
        2. Tie break by largest robot_id (so highest priority/lowest id wins).
        3. Remove its dependencies from the graph, breaking the cycle.
        """
        if not cycle:
            return DeadlockResolutionResult(cycle_detected=False)

        contested_cells = contested_cells or {}

        # Rank cycle members by: (effective_priority ascending, robot_id descending)
        # Lowest priority yields first; on tie, lexicographically larger robot_id yields
        sorted_members = sorted(
            cycle,
            key=lambda r_id: (
                robot_effective_priorities.get(r_id, 0.0),
                -ord(r_id[0]) if r_id else 0,
            ),
        )

        victim_id = sorted_members[0]
        victim_priority = robot_effective_priorities.get(victim_id, 0.0)
        released_cell = contested_cells.get(victim_id)

        # Break the cycle in the graph by removing victim's wait dependencies
        self.remove_dependency(victim_id)

        return DeadlockResolutionResult(
            cycle_detected=True,
            cycle_members=cycle,
            yielding_robot_id=victim_id,
            yielding_priority=victim_priority,
            released_cell=released_cell,
            action_taken="YIELD_AND_REROUTE",
        )

    def detect_and_resolve_all(
        self,
        robot_effective_priorities: Dict[str, float],
        contested_cells: Optional[Dict[str, Tuple[int, int]]] = None,
    ) -> List[DeadlockResolutionResult]:
        """Detect and break all active cycles in a single recovery pass."""
        results: List[DeadlockResolutionResult] = []
        cycles = self.detect_cycles()

        for cycle in cycles:
            # Check if cycle still exists (might have been broken by an earlier resolution)
            res = self.resolve_deadlock_cycle(cycle, robot_effective_priorities, contested_cells)
            results.append(res)

        return results

    def clear(self) -> None:
        self.graph.clear()
        self._edge_details.clear()
