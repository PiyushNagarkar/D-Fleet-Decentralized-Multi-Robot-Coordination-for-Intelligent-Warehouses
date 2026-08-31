"""Core Simulation Engine for D-Fleet warehouse environment.

The SimulationEngine coordinates physical mechanics, simulation clock ticks,
grid topology, obstacles, and sensory observations.

CRITICAL ARCHITECTURAL MANDATE:
- This engine is purely the physical environment / digital twin.
- It NEVER decides robot routes or paths.
- It NEVER assigns tasks to robots.
- It NEVER arbitrates conflicts or decides who yields.
- It NEVER grants or denies reservations.
- Every robot makes its own autonomous decisions via independent asyncio agents.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from pathlib import Path

from .clock import SimulationClock
from .warehouse import WarehouseGrid, CellType, DEFAULT_CELL_SIZE
from .obstacle_manager import ObstacleManager, Obstacle, ObstacleType
from .physics import (
    PhysicsEngine,
    RobotPhysicalState,
    ActionType,
    ActionResult,
    PhysicalStatus,
    Direction,
)
from .observations import ObservationEmitter, RobotLocalObservation
from .events import EventLog, EventType, Event


class SimulationEngine:
    """Environment simulation engine managing spatial state, physics, and clock."""

    def __init__(
        self,
        warehouse: Optional[WarehouseGrid] = None,
        dt: float = 0.1,
        seed: Optional[int] = 42,
        perception_radius: int = 4,
        max_event_history: int = 50000,
    ):
        self.clock = SimulationClock(dt=dt, seed=seed)
        self.warehouse = warehouse or WarehouseGrid(width=30, height=30)
        self.obstacle_manager = ObstacleManager()
        self.physics = PhysicsEngine(warehouse=self.warehouse)
        self.observations = ObservationEmitter(perception_radius=perception_radius)
        self.event_log = EventLog(max_history=max_event_history)
        self._is_running: bool = False

    @classmethod
    def from_scenario(
        cls,
        scenario_path_or_dict: Union[str, Path, Dict[str, Any]],
        dt: float = 0.1,
        seed: Optional[int] = 42,
        perception_radius: int = 4,
    ) -> SimulationEngine:
        """Instantiate simulation engine loaded with a scenario configuration."""
        warehouse = WarehouseGrid.from_json(scenario_path_or_dict)
        engine = cls(
            warehouse=warehouse,
            dt=dt,
            seed=seed,
            perception_radius=perception_radius,
        )

        # Load initial obstacles if defined in scenario
        if isinstance(scenario_path_or_dict, dict):
            data = scenario_path_or_dict
        elif isinstance(scenario_path_or_dict, (str, Path)):
            import json
            path = Path(scenario_path_or_dict)
            if path.is_file():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = json.loads(str(scenario_path_or_dict))
        else:
            data = {}

        for obs in data.get("initial_obstacles", []):
            engine.add_obstacle(
                x=obs["x"],
                y=obs["y"],
                start_tick=obs.get("start_tick", 0),
                duration=obs.get("duration"),
                obstacle_type=ObstacleType(obs.get("obstacle_type", "STATIC")),
                waypoints=[(wp["x"], wp["y"]) for wp in obs.get("waypoints", [])],
                speed_ticks_per_step=obs.get("speed_ticks_per_step", 1),
                obstacle_id=obs.get("id"),
            )

        return engine

    # --- Lifecycle Controls ---

    def start(self) -> None:
        self._is_running = True
        self.event_log.emit(
            EventType.SIMULATION_STARTED,
            tick=self.clock.current_tick,
            warehouse_name=self.warehouse.name,
        )

    def pause(self) -> None:
        self.clock.pause()
        self.event_log.emit(
            EventType.SIMULATION_PAUSED,
            tick=self.clock.current_tick,
        )

    def resume(self) -> None:
        self.clock.resume()
        self.event_log.emit(
            EventType.SIMULATION_RESUMED,
            tick=self.clock.current_tick,
        )

    def stop(self) -> None:
        self._is_running = False
        self.event_log.emit(
            EventType.SIMULATION_STOPPED,
            tick=self.clock.current_tick,
        )

    def reset(self, seed: Optional[int] = None) -> None:
        self.clock.reset(seed=seed)
        self.obstacle_manager.reset()
        self.event_log.clear()
        self.physics.robots.clear()
        self.event_log.emit(
            EventType.SIMULATION_RESET,
            tick=0,
        )

    # --- Entity Registration & Physics Spawning ---

    def spawn_robot(
        self,
        robot_id: str,
        x: int,
        y: int,
        heading: Direction = Direction.NORTH,
        battery_level: float = 100.0,
    ) -> RobotPhysicalState:
        state = self.physics.spawn_robot(
            robot_id=robot_id,
            x=x,
            y=y,
            heading=heading,
            battery_level=battery_level,
        )
        self.event_log.emit(
            EventType.ROBOT_SPAWNED,
            tick=self.clock.current_tick,
            robot_id=robot_id,
            location=(x, y),
            heading=heading.value,
            battery_level=battery_level,
        )
        return state

    def remove_robot(self, robot_id: str) -> bool:
        return self.physics.remove_robot(robot_id)

    # --- Fault & Task Injection ---

    def inject_failure(self, robot_id: str, reason: str = "Hardware Fault") -> bool:
        success = self.physics.inject_failure(robot_id, reason)
        if success:
            robot = self.physics.robots.get(robot_id)
            loc = (robot.x, robot.y) if robot else None
            self.event_log.emit(
                EventType.ROBOT_FAILED,
                tick=self.clock.current_tick,
                robot_id=robot_id,
                location=loc,
                reason=reason,
            )
        return success

    def recover_robot(self, robot_id: str) -> bool:
        success = self.physics.recover_robot(robot_id)
        if success:
            robot = self.physics.robots.get(robot_id)
            loc = (robot.x, robot.y) if robot else None
            self.event_log.emit(
                EventType.ROBOT_RECOVERED,
                tick=self.clock.current_tick,
                robot_id=robot_id,
                location=loc,
            )
        return success

    def inject_task(
        self,
        task_id: str,
        pickup_pos: Tuple[int, int],
        delivery_pos: Tuple[int, int],
        priority: int = 1,
        deadline_tick: Optional[int] = None,
        item_type: str = "standard_sku",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """Inject a warehouse transportation task into the event log.
        
        CRITICAL: The engine does not assign this task. Decentralized robot
        agents observe the TASK_SPAWNED event and execute peer-to-peer bidding / auctions.
        """
        payload = {
            "task_id": task_id,
            "pickup_location": list(pickup_pos),
            "delivery_location": list(delivery_pos),
            "priority": priority,
            "deadline_tick": deadline_tick,
            "item_type": item_type,
            "metadata": metadata or {},
        }
        return self.event_log.emit(
            EventType.TASK_SPAWNED,
            tick=self.clock.current_tick,
            location=pickup_pos,
            **payload,
        )

    # --- Obstacle Controls ---

    def add_obstacle(
        self,
        x: int,
        y: int,
        start_tick: Optional[int] = None,
        duration: Optional[int] = None,
        obstacle_type: ObstacleType = ObstacleType.STATIC,
        waypoints: Optional[List[Tuple[int, int]]] = None,
        speed_ticks_per_step: int = 1,
        obstacle_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Obstacle:
        effective_start = self.clock.current_tick if start_tick is None else start_tick
        obs = self.obstacle_manager.add_obstacle(
            x=x,
            y=y,
            start_tick=effective_start,
            duration=duration,
            obstacle_type=obstacle_type,
            waypoints=waypoints,
            speed_ticks_per_step=speed_ticks_per_step,
            obstacle_id=obstacle_id,
            metadata=metadata,
        )
        obs_type_str = obs.obstacle_type.value if hasattr(obs.obstacle_type, "value") else str(obs.obstacle_type)
        self.event_log.emit(
            EventType.OBSTACLE_ADDED,
            tick=self.clock.current_tick,
            location=(x, y),
            obstacle_id=obs.obstacle_id,
            obstacle_type=obs_type_str,
            duration=duration,
        )
        return obs

    def move_obstacle(self, obstacle_id: str, new_x: int, new_y: int) -> bool:
        success = self.obstacle_manager.move_obstacle(obstacle_id, new_x, new_y)
        if success:
            self.event_log.emit(
                EventType.OBSTACLE_MOVED,
                tick=self.clock.current_tick,
                location=(new_x, new_y),
                obstacle_id=obstacle_id,
            )
        return success

    def remove_obstacle(self, obstacle_id: str) -> bool:
        obs = self.obstacle_manager.get_obstacle(obstacle_id)
        loc = (obs.x, obs.y) if obs else None
        success = self.obstacle_manager.remove_obstacle(obstacle_id)
        if success:
            self.event_log.emit(
                EventType.OBSTACLE_REMOVED,
                tick=self.clock.current_tick,
                location=loc,
                obstacle_id=obstacle_id,
            )
        return success

    # --- Step Execution ---

    def step(
        self,
        robot_actions: Optional[Dict[str, Union[ActionType, str]]] = None,
        item_ids: Optional[Dict[str, str]] = None,
    ) -> Tuple[Dict[str, RobotLocalObservation], Dict[str, ActionResult]]:
        """Advance the entire environment simulation by one discrete tick.

        1. Advance clock.
        2. Advance dynamic obstacles (spawn, move, expire).
        3. Apply robot actions physically.
        4. Log physical telemetry events (battery, collisions, motion).
        5. Generate observations for all robots.

        Returns:
            (observations_by_robot_id, action_results_by_robot_id)
        """
        current_tick = self.clock.tick()
        robot_actions = robot_actions or {}
        item_ids = item_ids or {}

        # 1. Update obstacles
        spawned_obs, moved_obs, expired_obs = self.obstacle_manager.tick(current_tick)
        for obs in spawned_obs:
            self.event_log.emit(
                EventType.OBSTACLE_ADDED,
                tick=current_tick,
                location=(obs.x, obs.y),
                obstacle_id=obs.obstacle_id,
            )
        for obs in moved_obs:
            self.event_log.emit(
                EventType.OBSTACLE_MOVED,
                tick=current_tick,
                location=(obs.x, obs.y),
                obstacle_id=obs.obstacle_id,
            )
        for obs in expired_obs:
            self.event_log.emit(
                EventType.OBSTACLE_EXPIRED,
                tick=current_tick,
                location=(obs.x, obs.y),
                obstacle_id=obs.obstacle_id,
            )

        active_obstacle_positions = self.obstacle_manager.get_active_obstacle_positions(current_tick)

        # 2. Execute physical actions for registered robots
        action_results: Dict[str, ActionResult] = {}

        for robot_id, state in list(self.physics.robots.items()):
            action_raw = robot_actions.get(robot_id, ActionType.WAIT)
            action = ActionType(action_raw) if isinstance(action_raw, str) else action_raw
            item_id = item_ids.get(robot_id)

            result = self.physics.execute_action(
                robot_id=robot_id,
                action=action,
                dynamic_obstacles=active_obstacle_positions,
                item_id=item_id,
            )
            action_results[robot_id] = result

            # Log events based on action result
            if result.success:
                if action in (ActionType.MOVE_NORTH, ActionType.MOVE_SOUTH, ActionType.MOVE_EAST, ActionType.MOVE_WEST):
                    self.event_log.emit(
                        EventType.ROBOT_MOVED,
                        tick=current_tick,
                        robot_id=robot_id,
                        location=result.new_position,
                        action=action.value,
                    )
                elif action == ActionType.CHARGE:
                    self.event_log.emit(
                        EventType.CHARGING_PROGRESS,
                        tick=current_tick,
                        robot_id=robot_id,
                        location=result.new_position,
                        battery_level=state.battery_level,
                    )
                elif action == ActionType.PICKUP:
                    self.event_log.emit(
                        EventType.TASK_PICKED_UP,
                        tick=current_tick,
                        robot_id=robot_id,
                        location=result.new_position,
                        item_id=state.carried_item_id,
                    )
                elif action == ActionType.DROPOFF:
                    self.event_log.emit(
                        EventType.TASK_DELIVERED,
                        tick=current_tick,
                        robot_id=robot_id,
                        location=result.new_position,
                    )
            else:
                if result.collision_with_robot_id or result.collision_with_obstacle:
                    self.event_log.emit(
                        EventType.ROBOT_COLLISION,
                        tick=current_tick,
                        robot_id=robot_id,
                        location=result.old_position,
                        collision_robot_id=result.collision_with_robot_id,
                        collision_obstacle=result.collision_with_obstacle,
                        message=result.message,
                    )

            # Battery alert events
            if 0.0 < state.battery_level <= 15.0:
                self.event_log.emit(
                    EventType.BATTERY_CRITICAL,
                    tick=current_tick,
                    robot_id=robot_id,
                    location=(state.x, state.y),
                    battery_level=state.battery_level,
                )
            elif 15.0 < state.battery_level <= 30.0:
                self.event_log.emit(
                    EventType.BATTERY_LOW,
                    tick=current_tick,
                    robot_id=robot_id,
                    location=(state.x, state.y),
                    battery_level=state.battery_level,
                )

        # 3. Generate local observations for all robots
        active_obstacles_list = [
            obs for obs in self.obstacle_manager._obstacles.values()
            if obs.is_alive_at(current_tick)
        ]
        observations: Dict[str, RobotLocalObservation] = {}
        for robot_id, state in self.physics.robots.items():
            obs = self.observations.generate_robot_observation(
                robot_state=state,
                warehouse=self.warehouse,
                all_robots=self.physics.robots,
                active_obstacles=active_obstacles_list,
                current_tick=current_tick,
            )
            observations[robot_id] = obs

        return observations, action_results

    def get_observation(self, robot_id: str) -> Optional[RobotLocalObservation]:
        """Fetch current tick observation for a specific robot."""
        state = self.physics.robots.get(robot_id)
        if not state:
            return None
        active_obstacles = [
            obs for obs in self.obstacle_manager._obstacles.values()
            if obs.is_alive_at(self.clock.current_tick)
        ]
        return self.observations.generate_robot_observation(
            robot_state=state,
            warehouse=self.warehouse,
            all_robots=self.physics.robots,
            active_obstacles=active_obstacles,
            current_tick=self.clock.current_tick,
        )

    def get_all_observations(self) -> Dict[str, RobotLocalObservation]:
        """Fetch observations for all currently registered robots."""
        active_obstacles = [
            obs for obs in self.obstacle_manager._obstacles.values()
            if obs.is_alive_at(self.clock.current_tick)
        ]
        return {
            r_id: self.observations.generate_robot_observation(
                robot_state=state,
                warehouse=self.warehouse,
                all_robots=self.physics.robots,
                active_obstacles=active_obstacles,
                current_tick=self.clock.current_tick,
            )
            for r_id, state in self.physics.robots.items()
        }

    def get_global_snapshot(self) -> Dict[str, Any]:
        """Fetch full digital twin telemetry frame."""
        active_obstacles = [
            obs for obs in self.obstacle_manager._obstacles.values()
            if obs.is_alive_at(self.clock.current_tick)
        ]
        return self.observations.generate_global_snapshot(
            warehouse=self.warehouse,
            all_robots=self.physics.robots,
            active_obstacles=active_obstacles,
            current_tick=self.clock.current_tick,
            clock_time_s=self.clock.current_time_s,
        )
