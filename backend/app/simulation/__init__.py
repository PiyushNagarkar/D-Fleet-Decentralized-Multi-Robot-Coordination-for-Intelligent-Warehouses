"""D-Fleet Simulation Environment Package.

Contains the purely physical simulation environment, grid topologies, clock,
physics engine, dynamic obstacle manager, event logging, and observations.
"""

from .clock import SimulationClock
from .warehouse import (
    CellType,
    WarehouseGrid,
    DEFAULT_CELL_SIZE,
    grid_to_world,
    world_to_grid,
)
from .obstacle_manager import (
    Obstacle,
    ObstacleType,
    ObstacleAction,
    ObstacleManager,
)
from .physics import (
    Direction,
    DIRECTION_VECTORS,
    ActionType,
    PhysicalStatus,
    RobotPhysicalState,
    ActionResult,
    PhysicsEngine,
)
from .observations import (
    NearbyRobotObservation,
    NearbyObstacleObservation,
    RobotLocalObservation,
    ObservationEmitter,
)
from .events import (
    EventType,
    Event,
    EventLog,
)
from .engine import SimulationEngine

__all__ = [
    "SimulationClock",
    "CellType",
    "WarehouseGrid",
    "DEFAULT_CELL_SIZE",
    "grid_to_world",
    "world_to_grid",
    "Obstacle",
    "ObstacleType",
    "ObstacleAction",
    "ObstacleManager",
    "Direction",
    "DIRECTION_VECTORS",
    "ActionType",
    "PhysicalStatus",
    "RobotPhysicalState",
    "ActionResult",
    "PhysicsEngine",
    "NearbyRobotObservation",
    "NearbyObstacleObservation",
    "RobotLocalObservation",
    "ObservationEmitter",
    "EventType",
    "Event",
    "EventLog",
    "SimulationEngine",
]
