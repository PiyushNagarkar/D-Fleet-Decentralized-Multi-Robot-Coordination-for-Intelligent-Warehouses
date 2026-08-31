"""Standard D* Lite Incremental Path Planner for Decentralized Robots.

Implements the incremental heuristic search algorithm (Koenig & Likhachev, 2002)
to provide fast replanning under dynamic obstacle changes and sensory updates.

CRITICAL DESIGN MANDATE:
- Consumes ONLY a robot's private LocalWorldModel (or local cost grid).
- Never accesses global simulation truth.
- Implements genuine rhs/g value repair with a priority queue rather than full A* re-runs.
"""

from __future__ import annotations
import heapq
import math
from typing import Dict, List, Optional, Set, Tuple, Any

from app.simulation.warehouse import WarehouseGrid, CellType
from app.robots.local_world_model import LocalWorldModel

INF = float("inf")


class PriorityQueue:
    """Indexed min-priority queue with lazy deletion for D* Lite."""

    def __init__(self):
        self._heap: List[Tuple[float, float, Tuple[int, int]]] = []
        self._entry_finder: Dict[Tuple[int, int], Tuple[float, float]] = {}

    def insert(self, item: Tuple[int, int], priority: Tuple[float, float]) -> None:
        self._entry_finder[item] = priority
        heapq.heappush(self._heap, (priority[0], priority[1], item))

    def remove(self, item: Tuple[int, int]) -> None:
        if item in self._entry_finder:
            del self._entry_finder[item]

    def pop(self) -> Tuple[Tuple[int, int], Tuple[float, float]]:
        while self._heap:
            k1, k2, item = heapq.heappop(self._heap)
            if item in self._entry_finder and self._entry_finder[item] == (k1, k2):
                del self._entry_finder[item]
                return item, (k1, k2)
        raise KeyError("pop from an empty priority queue")

    def top_key(self) -> Tuple[float, float]:
        while self._heap:
            k1, k2, item = self._heap[0]
            if item in self._entry_finder and self._entry_finder[item] == (k1, k2):
                return (k1, k2)
            heapq.heappop(self._heap)
        return (INF, INF)

    def contains(self, item: Tuple[int, int]) -> bool:
        return item in self._entry_finder

    def is_empty(self) -> bool:
        while self._heap:
            k1, k2, item = self._heap[0]
            if item in self._entry_finder and self._entry_finder[item] == (k1, k2):
                return False
            heapq.heappop(self._heap)
        return True

    def __len__(self) -> int:
        return len(self._entry_finder)


class DStarLite:
    """Incremental D* Lite path planner.

    Maintains g and rhs values backwards from goal to start so that robot
    movement only requires updating start and accumulated heuristic modifier k_m.
    """

    def __init__(
        self,
        grid_width: int,
        grid_height: int,
        allow_diagonal: bool = False,
    ):
        self.width = grid_width
        self.height = grid_height
        self.allow_diagonal = allow_diagonal

        self.s_start: Optional[Tuple[int, int]] = None
        self.s_goal: Optional[Tuple[int, int]] = None
        self.s_last: Optional[Tuple[int, int]] = None
        self.k_m: float = 0.0

        self.g: Dict[Tuple[int, int], float] = {}
        self.rhs: Dict[Tuple[int, int], float] = {}
        self.u: PriorityQueue = PriorityQueue()
        self.cost_grid: Dict[Tuple[int, int], float] = {}

        # Performance tracking metrics
        self.nodes_expanded: int = 0
        self.total_replans: int = 0

        # Initialize default traversability
        for y in range(grid_height):
            for x in range(grid_width):
                self.cost_grid[(x, y)] = 1.0

    @classmethod
    def from_grid(
        cls,
        warehouse: WarehouseGrid,
        allow_diagonal: bool = False,
    ) -> DStarLite:
        """Create and initialize a D* Lite planner directly from a WarehouseGrid."""
        planner = cls(
            grid_width=warehouse.width,
            grid_height=warehouse.height,
            allow_diagonal=allow_diagonal,
        )
        for y in range(warehouse.height):
            for x in range(warehouse.width):
                if not warehouse.is_traversable(x, y):
                    planner.update_cell_cost((x, y), INF)
        return planner

    @classmethod
    def from_world_model(
        cls,
        world_model: LocalWorldModel,
        allow_diagonal: bool = False,
        current_tick: int = 0,
    ) -> DStarLite:
        """Create and initialize a D* Lite planner from a robot's local world model."""
        planner = cls(
            grid_width=world_model.static_map.width,
            grid_height=world_model.static_map.height,
            allow_diagonal=allow_diagonal,
        )
        planner.sync_with_world_model(world_model, current_tick=current_tick)
        return planner

    def sync_with_world_model(
        self,
        world_model: LocalWorldModel,
        current_tick: int = 0,
    ) -> List[Tuple[int, int]]:
        """Sync internal cost grid with local world model and trigger incremental repair."""
        changed_cells = []
        for y in range(self.height):
            for x in range(self.width):
                new_cost = self._derive_cell_cost(world_model, x, y, current_tick)
                old_cost = self.cost_grid.get((x, y), 1.0)
                if abs(new_cost - old_cost) > 1e-6:
                    self.update_cell_cost((x, y), new_cost)
                    changed_cells.append((x, y))
        return changed_cells

    def _derive_cell_cost(
        self,
        world_model: LocalWorldModel,
        x: int,
        y: int,
        tick: int,
    ) -> float:
        """Derive cell traversal cost from local world model knowledge."""
        # Static wall
        if not world_model.static_map.is_traversable(x, y):
            return INF

        # Known dynamic obstacles
        for obs in world_model.dynamic_obstacles.values():
            if obs and obs.position == (x, y):
                if obs.estimated_expiration_tick is None or tick < obs.estimated_expiration_tick:
                    return INF

        # Space-time reservations of other robots
        for ((rx, ry), rtick), owner in world_model.reservations.items():
            if (rx, ry) == (x, y) and rtick == tick and owner != world_model.robot_id:
                return INF

        # Soft penalty for known other robot locations
        for r_info in world_model.known_robots.values():
            if r_info.position == (x, y) and r_info.robot_id != world_model.robot_id:
                return 5.0  # Avoid crowded cells if alternative exists

        return 1.0

    def heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Admissible heuristic (Manhattan or Octile)."""
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        if self.allow_diagonal:
            return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)
        return float(dx + dy)

    def calculate_key(self, s: Tuple[int, int]) -> Tuple[float, float]:
        """Compute lexicographic priority key for node s."""
        min_g_rhs = min(self.get_g(s), self.get_rhs(s))
        if self.s_start is None:
            h = 0.0
        else:
            h = self.heuristic(self.s_start, s)
        return (min_g_rhs + h + self.k_m, min_g_rhs)

    def get_g(self, s: Tuple[int, int]) -> float:
        return self.g.get(s, INF)

    def get_rhs(self, s: Tuple[int, int]) -> float:
        if s == self.s_goal:
            return 0.0
        return self.rhs.get(s, INF)

    def get_neighbors(self, s: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Return adjacent grid coordinates within bounds."""
        x, y = s
        cardinals = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        diagonals = [(x + 1, y + 1), (x + 1, y - 1), (x - 1, y + 1), (x - 1, y - 1)]
        candidates = cardinals + (diagonals if self.allow_diagonal else [])
        return [
            pos for pos in candidates
            if 0 <= pos[0] < self.width and 0 <= pos[1] < self.height
        ]

    def cost(self, u: Tuple[int, int], v: Tuple[int, int]) -> float:
        """Directed edge cost for moving from u to v."""
        u_cost = self.cost_grid.get(u, 1.0)
        v_cost = self.cost_grid.get(v, 1.0)
        if math.isinf(u_cost) or math.isinf(v_cost):
            return INF
        
        # Diagonal movement scale
        if u[0] != v[0] and u[1] != v[1]:
            return v_cost * math.sqrt(2)
        return v_cost

    def update_vertex(self, u: Tuple[int, int]) -> None:
        """Update rhs value and priority queue membership for node u."""
        if u != self.s_goal:
            min_rhs = INF
            for s_prime in self.get_neighbors(u):
                c = self.cost(u, s_prime)
                if not math.isinf(c):
                    val = c + self.get_g(s_prime)
                    if val < min_rhs:
                        min_rhs = val
            self.rhs[u] = min_rhs

        if self.u.contains(u):
            self.u.remove(u)

        if not math.isclose(self.get_g(u), self.get_rhs(u), abs_tol=1e-6):
            self.u.insert(u, self.calculate_key(u))

    def compute_shortest_path(self) -> None:
        """Main D* Lite search loop repairing inconsistent nodes."""
        if self.s_start is None:
            return

        while (
            self.u.top_key() < self.calculate_key(self.s_start)
            or not math.isclose(self.get_rhs(self.s_start), self.get_g(self.s_start), abs_tol=1e-6)
        ):
            if self.u.is_empty():
                break

            u, k_old = self.u.pop()
            self.nodes_expanded += 1
            k_new = self.calculate_key(u)

            if k_old < k_new:
                self.u.insert(u, k_new)
            elif self.get_g(u) > self.get_rhs(u):
                # Overconsistent
                self.g[u] = self.get_rhs(u)
                for s in self.get_neighbors(u):
                    self.update_vertex(s)
            else:
                # Underconsistent
                self.g[u] = INF
                for s in self.get_neighbors(u) + [u]:
                    self.update_vertex(s)

    def plan(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
    ) -> List[Tuple[int, int]]:
        """Full initial plan from start to goal."""
        self.s_start = start
        self.s_goal = goal
        self.s_last = start
        self.k_m = 0.0

        self.g.clear()
        self.rhs.clear()
        self.u = PriorityQueue()
        self.nodes_expanded = 0

        self.rhs[self.s_goal] = 0.0
        self.u.insert(self.s_goal, self.calculate_key(self.s_goal))

        self.compute_shortest_path()
        return self.extract_path()

    def update_cell_cost(self, cell: Tuple[int, int], new_cost: float) -> None:
        """Update single cell traversal cost and trigger incremental vertex repairs."""
        old_cost = self.cost_grid.get(cell, 1.0)
        if math.isclose(old_cost, new_cost, abs_tol=1e-6):
            return

        self.cost_grid[cell] = new_cost

        # Update the cell itself and all neighboring predecessor vertices
        for neighbor in self.get_neighbors(cell):
            self.update_vertex(neighbor)
        self.update_vertex(cell)

    def replan(
        self,
        new_start: Optional[Tuple[int, int]] = None,
    ) -> List[Tuple[int, int]]:
        """Incrementally repair search graph from current/new start location."""
        if self.s_start is None or self.s_goal is None or self.s_last is None:
            raise ValueError("Planner must be initialized with plan() before replan()")

        if new_start is not None and new_start != self.s_start:
            self.s_start = new_start
            self.k_m += self.heuristic(self.s_last, self.s_start)
            self.s_last = self.s_start

        self.total_replans += 1
        self.compute_shortest_path()
        return self.extract_path()

    def extract_path(self) -> List[Tuple[int, int]]:
        """Greedily reconstruct path from s_start to s_goal using g and c."""
        if self.s_start is None or self.s_goal is None:
            return []

        if math.isinf(self.get_g(self.s_start)) and math.isinf(self.get_rhs(self.s_start)):
            return []  # No path exists

        curr = self.s_start
        path = [curr]
        visited = {curr}

        max_steps = self.width * self.height * 2

        while curr != self.s_goal and len(path) < max_steps:
            best_next = None
            min_val = INF

            for nxt in self.get_neighbors(curr):
                c = self.cost(curr, nxt)
                if not math.isinf(c):
                    val = c + self.get_g(nxt)
                    if val < min_val:
                        min_val = val
                        best_next = nxt

            if best_next is None or math.isinf(min_val):
                return []  # Path is blocked

            curr = best_next
            if curr in visited:
                # Cycle detected
                return []
            visited.add(curr)
            path.append(curr)

        if curr != self.s_goal:
            return []

        return path
