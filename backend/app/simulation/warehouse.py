"""Warehouse grid topology, cell definitions, and coordinate transformations."""

from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any
import json


class CellType(str, Enum):
    WALL = "#"
    FLOOR = "."
    PICKUP = "P"
    DELIVERY = "D"
    CHARGING = "C"
    INTERSECTION = "I"


DEFAULT_CELL_SIZE: float = 1.0  # Meters per grid cell


def grid_to_world(grid_x: int, grid_y: int, cell_size: float = DEFAULT_CELL_SIZE) -> Tuple[float, float, float]:
    """Convert discrete 2D grid coordinates to 3D world coordinates (X, Y, Z).
    
    Y is elevation (0.0 for floor level).
    world_x = grid_x * cell_size
    world_z = grid_y * cell_size
    """
    world_x = float(grid_x) * cell_size
    world_y = 0.0
    world_z = float(grid_y) * cell_size
    return (world_x, world_y, world_z)


def world_to_grid(world_x: float, world_z: float, cell_size: float = DEFAULT_CELL_SIZE) -> Tuple[int, int]:
    """Convert continuous 3D world coordinates to closest discrete 2D grid coordinates."""
    grid_x = int(round(world_x / cell_size))
    grid_y = int(round(world_z / cell_size))
    return (grid_x, grid_y)


class WarehouseGrid:
    """Represents the static 2D topological layout of a warehouse floor."""

    def __init__(
        self,
        width: int,
        height: int,
        cells: Optional[Dict[Tuple[int, int], CellType]] = None,
        cell_size: float = DEFAULT_CELL_SIZE,
        name: str = "default_warehouse",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.name = name
        self.metadata = metadata or {}
        self.cells: Dict[Tuple[int, int], CellType] = cells or {}

        # If cells not provided, default all inside bounds to floor
        if not self.cells:
            for y in range(height):
                for x in range(width):
                    self.cells[(x, y)] = CellType.FLOOR

        self._cached_pickup_stations: List[Tuple[int, int]] = []
        self._cached_delivery_stations: List[Tuple[int, int]] = []
        self._cached_charging_stations: List[Tuple[int, int]] = []
        self._cached_intersections: List[Tuple[int, int]] = []
        self._rebuild_caches()

    def _rebuild_caches(self) -> None:
        self._cached_pickup_stations = [pos for pos, c in self.cells.items() if c == CellType.PICKUP]
        self._cached_delivery_stations = [pos for pos, c in self.cells.items() if c == CellType.DELIVERY]
        self._cached_charging_stations = [pos for pos, c in self.cells.items() if c == CellType.CHARGING]
        self._cached_intersections = [pos for pos, c in self.cells.items() if c == CellType.INTERSECTION]

    def in_bounds(self, x: int, y: int) -> bool:
        """Check whether (x, y) is within the grid boundary."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get_cell(self, x: int, y: int) -> CellType:
        """Get the cell type at (x, y). Returns CellType.WALL if out of bounds."""
        if not self.in_bounds(x, y):
            return CellType.WALL
        return self.cells.get((x, y), CellType.FLOOR)

    def is_traversable(self, x: int, y: int) -> bool:
        """Check if grid cell is physically traversable by a robot (not a wall/shelf)."""
        if not self.in_bounds(x, y):
            return False
        return self.get_cell(x, y) != CellType.WALL

    def set_cell(self, x: int, y: int, cell_type: CellType) -> None:
        """Set cell type at coordinate."""
        if self.in_bounds(x, y):
            self.cells[(x, y)] = cell_type
            self._rebuild_caches()

    @property
    def pickup_stations(self) -> List[Tuple[int, int]]:
        return list(self._cached_pickup_stations)

    @property
    def delivery_stations(self) -> List[Tuple[int, int]]:
        return list(self._cached_delivery_stations)

    @property
    def charging_stations(self) -> List[Tuple[int, int]]:
        return list(self._cached_charging_stations)

    @property
    def intersections(self) -> List[Tuple[int, int]]:
        return list(self._cached_intersections)

    def get_neighbors(
        self,
        x: int,
        y: int,
        allow_diagonal: bool = False,
    ) -> List[Tuple[int, int]]:
        """Return all adjacent traversable cells."""
        cardinal_offsets = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        diagonal_offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        offsets = cardinal_offsets + (diagonal_offsets if allow_diagonal else [])

        neighbors = []
        for dx, dy in offsets:
            nx, ny = x + dx, y + dy
            if self.is_traversable(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    @classmethod
    def from_ascii(
        cls,
        ascii_grid: Union[str, List[str]],
        name: str = "ascii_warehouse",
        cell_size: float = DEFAULT_CELL_SIZE,
    ) -> WarehouseGrid:
        """Parse warehouse layout from ASCII lines or list of strings.
        
        '#' = Wall, '.' = Floor, 'P' = Pickup, 'D' = Delivery, 'C' = Charging, 'I' = Intersection
        """
        if isinstance(ascii_grid, list):
            lines = [line.strip() for line in ascii_grid if line.strip()]
        else:
            lines = [line.strip() for line in ascii_grid.strip().splitlines() if line.strip()]
        if not lines:
            raise ValueError("Empty ASCII grid provided")
        
        height = len(lines)
        width = len(lines[0])
        cells: Dict[Tuple[int, int], CellType] = {}

        for y, line in enumerate(lines):
            for x, char in enumerate(line[:width]):
                try:
                    cells[(x, y)] = CellType(char)
                except ValueError:
                    cells[(x, y)] = CellType.FLOOR

        return cls(width=width, height=height, cells=cells, cell_size=cell_size, name=name)

    @classmethod
    def from_json(cls, json_data: Union[str, Path, Dict[str, Any]]) -> WarehouseGrid:
        """Load warehouse scenario from a JSON string, file path, or dictionary."""
        if isinstance(json_data, (str, Path)):
            path = Path(json_data)
            if path.is_file():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = json.loads(str(json_data))
        else:
            data = json_data

        name = data.get("name", "scenario_warehouse")
        cell_size = data.get("cell_size", DEFAULT_CELL_SIZE)
        metadata = data.get("metadata", {})

        # Check if grid is specified as ASCII layout array or matrix
        if "layout" in data and isinstance(data["layout"], list):
            layout_lines = data["layout"]
            height = len(layout_lines)
            width = max(len(line) for line in layout_lines)
            cells: Dict[Tuple[int, int], CellType] = {}
            for y, line in enumerate(layout_lines):
                for x, char in enumerate(line):
                    try:
                        cells[(x, y)] = CellType(char)
                    except ValueError:
                        cells[(x, y)] = CellType.FLOOR
            # Fill missing trailing spaces with WALL
            for y in range(height):
                for x in range(width):
                    if (x, y) not in cells:
                        cells[(x, y)] = CellType.WALL
            return cls(width=width, height=height, cells=cells, cell_size=cell_size, name=name, metadata=metadata)

        width = data.get("width", 10)
        height = data.get("height", 10)
        cells = {}

        # Default floor
        for y in range(height):
            for x in range(width):
                cells[(x, y)] = CellType.FLOOR

        # Apply specific elements if explicitly defined
        for wall in data.get("walls", []):
            cells[(wall["x"], wall["y"])] = CellType.WALL
        for p in data.get("pickups", []):
            cells[(p["x"], p["y"])] = CellType.PICKUP
        for d in data.get("deliveries", []):
            cells[(d["x"], d["y"])] = CellType.DELIVERY
        for c in data.get("chargers", []):
            cells[(c["x"], c["y"])] = CellType.CHARGING
        for i in data.get("intersections", []):
            cells[(i["x"], i["y"])] = CellType.INTERSECTION

        return cls(width=width, height=height, cells=cells, cell_size=cell_size, name=name, metadata=metadata)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize grid to a dictionary representation."""
        layout_lines = []
        for y in range(self.height):
            line = "".join(self.get_cell(x, y).value for x in range(self.width))
            layout_lines.append(line)

        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "cell_size": self.cell_size,
            "layout": layout_lines,
            "pickup_stations": [list(p) for p in self.pickup_stations],
            "delivery_stations": [list(d) for d in self.delivery_stations],
            "charging_stations": [list(c) for c in self.charging_stations],
            "intersections": [list(i) for i in self.intersections],
            "metadata": self.metadata,
        }
