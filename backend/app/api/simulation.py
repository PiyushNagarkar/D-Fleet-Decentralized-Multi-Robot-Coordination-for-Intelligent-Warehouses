"""Simulation Service and Asynchronous Background Orchestrator.

CRITICAL ARCHITECTURAL MANDATES:
1. Genuinely Decentralized: SimulationService only steps the physical environment and clock.
2. Each RobotAgent makes its own sense-plan-act decisions locally.
3. FastAPI is non-deciding infrastructure providing REST + WebSocket telemetry.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any

from app.simulation.warehouse import WarehouseGrid
from app.simulation.engine import SimulationEngine
from app.simulation.physics import ActionType
from app.simulation.events import EventType
from app.communication.network import P2PNetwork
from app.robots.robot_agent import RobotAgent
from app.robots.state import RobotStatus
from app.tasks.task import TaskStatus
from app.metrics.collector import MetricsCollector
from app.metrics.evaluator import MetricsEvaluator
from .websocket import telemetry_hub

logger = logging.getLogger("dfleet.simulation")
logger.setLevel(logging.INFO)


class SimulationService:
    """Orchestrates physical environment simulation, independent agents, and telemetry."""

    def __init__(self):
        self.grid: Optional[WarehouseGrid] = None
        self.engine: Optional[SimulationEngine] = None
        self.network: P2PNetwork = P2PNetwork()
        self.agents: Dict[str, RobotAgent] = {}
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.metrics_collector: MetricsCollector = MetricsCollector()
        self.status: str = "IDLE"  # IDLE, RUNNING, PAUSED, COMPLETED
        self.speed: float = 1.0
        self.base_tick_delay: float = 0.25  # Base seconds per tick
        self._runner_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.scheduled_failures: List[Dict[str, Any]] = []

        # Initialize with default flagship scenario layout
        self._init_default_scenario()

    def _init_default_scenario(self) -> None:
        ascii_map = """
        ################
        #C...P......D..#
        #...########...#
        #...#......#...#
        #.I.#..I...#.I.#
        #...#......#...#
        #...########...#
        #C...P......D..#
        #..............#
        ################
        """
        self.grid = WarehouseGrid.from_ascii(ascii_map, name="complete_demo")
        self.engine = SimulationEngine(warehouse=self.grid, seed=42)
        self.network = P2PNetwork(seed=42)
        self.agents.clear()
        self.tasks.clear()
        self.scheduled_failures.clear()
        self.metrics_collector = MetricsCollector()

        # Spawn default 4 robots
        self.spawn_robot("R1", 1, 1, priority=3, battery=98.0)
        self.spawn_robot("R2", 1, 7, priority=2, battery=95.0)
        self.spawn_robot("R3", 14, 1, priority=2, battery=90.0)
        self.spawn_robot("R4", 14, 7, priority=1, battery=100.0)

        # Inject default tasks
        self.inject_task("task_01", (5, 1), (12, 1), priority=3, item_type="pod_alpha")
        self.inject_task("task_02", (5, 7), (12, 7), priority=2, item_type="pod_beta")
        self.inject_task("task_03", (5, 1), (12, 7), priority=1, item_type="pod_gamma")
        self.inject_task("task_04", (5, 7), (12, 1), priority=2, item_type="pod_delta")

        self.status = "IDLE"

    def inject_task(
        self,
        task_id: str,
        pickup_pos: Tuple[int, int],
        delivery_pos: Tuple[int, int],
        priority: int = 1,
        item_type: str = "standard_pod",
    ) -> None:
        """Register task in environment and announce to independent robot agents."""
        tick = self.engine.clock.current_tick if self.engine else 0
        self.tasks[task_id] = {
            "task_id": task_id,
            "pickup_position": list(pickup_pos),
            "delivery_position": list(delivery_pos),
            "status": "UNASSIGNED",
            "priority": priority,
            "item_type": item_type,
            "spawn_tick": tick,
        }
        if self.engine:
            self.engine.inject_task(task_id, pickup_pos, delivery_pos, priority=priority, item_type=item_type)
        # Decentralized task broadcast to all agents
        for agent in self.agents.values():
            agent.task_manager.on_task_announced(
                task_id=task_id,
                pickup_location=pickup_pos,
                delivery_location=delivery_pos,
                priority=priority,
                spawn_tick=tick,
                item_type=item_type,
            )

    def load_scenario_data(self, scenario_data: Dict[str, Any]) -> None:
        """Initialize engine and independent agents from scenario dictionary."""
        grid_data = scenario_data.get("grid", {})
        ascii_layout = grid_data.get("ascii_layout") or scenario_data.get("layout")

        if ascii_layout:
            self.grid = WarehouseGrid.from_ascii(ascii_layout, name=scenario_data.get("name", "scenario"))
        else:
            w = scenario_data.get("width") or grid_data.get("width", 16)
            h = scenario_data.get("height") or grid_data.get("height", 12)
            self.grid = WarehouseGrid(width=w, height=h, name=scenario_data.get("name", "scenario"))

        seed = scenario_data.get("seed", 42)
        self.engine = SimulationEngine(warehouse=self.grid, seed=seed)
        self.network = P2PNetwork(seed=seed)
        self.agents.clear()
        self.tasks.clear()
        self.metrics_collector = MetricsCollector()
        self.scheduled_failures = list(scenario_data.get("failures", []))

        # Spawn robots
        robots_cfg = scenario_data.get("robots", [])
        if robots_cfg:
            for r_cfg in robots_cfg:
                r_id = r_cfg["id"]
                start_pos = r_cfg.get("start_pos", [1, 1])
                prio = r_cfg.get("priority", 1)
                battery = r_cfg.get("battery", 100.0)
                self.spawn_robot(r_id, start_pos[0], start_pos[1], priority=prio, battery=battery)
        else:
            spawn_locs = self.grid.charging_stations if self.grid and self.grid.charging_stations else [(1, 1)]
            for i, loc in enumerate(spawn_locs[:4]):
                self.spawn_robot(f"R{i+1}", loc[0], loc[1], priority=i+1)

        # Inject tasks
        for t_cfg in scenario_data.get("tasks", []):
            t_id = t_cfg["id"]
            p_pos = (t_cfg["pickup_pos"][0], t_cfg["pickup_pos"][1])
            d_pos = (t_cfg["delivery_pos"][0], t_cfg["delivery_pos"][1])
            prio = t_cfg.get("priority", 1)
            item_type = t_cfg.get("item_type", "standard_pod")
            self.inject_task(t_id, p_pos, d_pos, priority=prio, item_type=item_type)

        # Inject obstacles
        for obs_cfg in scenario_data.get("obstacles", []):
            waypoints = obs_cfg.get("waypoints")
            wp_parsed = None
            if waypoints:
                wp_parsed = [(wp["x"], wp["y"]) if isinstance(wp, dict) else (wp[0], wp[1]) for wp in waypoints]
            self.engine.add_obstacle(
                x=obs_cfg["x"],
                y=obs_cfg["y"],
                start_tick=obs_cfg.get("start_tick", 0),
                duration=obs_cfg.get("duration", 50),
                obstacle_type=obs_cfg.get("obstacle_type", "STATIC"),
                waypoints=wp_parsed,
                speed_ticks_per_step=obs_cfg.get("speed_ticks_per_step", 1),
                obstacle_id=obs_cfg.get("id"),
            )

        # Communication link impairment configuration
        comm_cfg = scenario_data.get("communication", {})
        delay = comm_cfg.get("delay", 0)
        loss = comm_cfg.get("packet_loss", 0.0)
        jitter = comm_cfg.get("jitter", 0)
        if delay > 0 or loss > 0 or jitter > 0:
            for r1 in self.agents.keys():
                for r2 in self.agents.keys():
                    if r1 != r2:
                        self.network.set_link_config(
                            sender=r1,
                            recipient=r2,
                            latency_ticks=delay,
                            loss_rate=loss,
                            jitter_ticks=jitter,
                        )

        self.status = "IDLE"
        logger.info(f"Loaded scenario '{self.grid.name}' with {len(self.agents)} robots and {len(self.tasks)} tasks.")

    def spawn_robot(
        self,
        robot_id: str,
        x: int,
        y: int,
        priority: int = 1,
        battery: float = 100.0,
    ) -> RobotAgent:
        """Instantiate an autonomous agent and register in physics environment."""
        self.engine.spawn_robot(robot_id, x=x, y=y, battery_level=battery)
        agent = RobotAgent(
            robot_id=robot_id,
            initial_position=(x, y),
            static_map=self.grid,
            network=self.network,
            priority=priority,
            battery=battery,
        )
        self.agents[robot_id] = agent
        return agent

    async def start(self) -> None:
        """Start or resume background simulation execution."""
        if self.status == "RUNNING":
            return
        self.status = "RUNNING"
        logger.info("Simulation STARTED.")
        if not self._runner_task or self._runner_task.done():
            self._runner_task = asyncio.create_task(self._run_loop())

    def pause(self) -> None:
        """Pause simulation execution."""
        self.status = "PAUSED"
        logger.info("Simulation PAUSED.")

    def reset(self) -> None:
        """Reset simulation to initial scenario state."""
        self.pause()
        self._init_default_scenario()
        logger.info("Simulation RESET.")

    def set_speed(self, speed: float) -> None:
        """Adjust simulation execution rate multiplier."""
        self.speed = max(0.2, min(10.0, speed))

    def step_once(self) -> Dict[str, Any]:
        """Execute a single simulation tick across all agents and environment."""
        if not self.engine or not self.grid:
            return {}

        current_tick = self.engine.clock.current_tick

        # Trigger any scheduled failures for this tick
        for fail_cfg in self.scheduled_failures:
            if fail_cfg.get("tick") == current_tick:
                self.inject_robot_failure(fail_cfg["robot_id"])

        # 1. Sense: retrieve local observations from simulation engine
        observations = self.engine.get_all_observations()

        # 2. Plan & Act: each robot agent executes its local decision cycle
        actions = {}
        for r_id, agent in self.agents.items():
            obs = observations.get(r_id)
            if obs:
                actions[r_id] = agent.step(obs)
            else:
                actions[r_id] = ActionType.WAIT

        # 3. Environment Step: physical execution, collisions, obstacle steps
        self.engine.step(actions)

        # 4. Ingest events for metrics
        self.metrics_collector.total_ticks = current_tick + 1
        for evt in self.engine.event_log.get_events(since_tick=current_tick):
            self.metrics_collector.ingest_event(evt)

        # 5. Generate and return telemetry snapshot
        snapshot = self.get_telemetry_snapshot()
        return snapshot

    async def _run_loop(self) -> None:
        """Background asynchronous execution loop."""
        logger.info("Starting background simulation runner loop...")
        try:
            while self.status == "RUNNING":
                snapshot = self.step_once()
                await telemetry_hub.broadcast(snapshot)
                delay = max(0.02, self.base_tick_delay / self.speed)
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception(f"Error in simulation run loop: {e}")

    def inject_robot_failure(self, robot_id: str) -> bool:
        """Inject failure into robot's physical hardware."""
        if not self.engine or robot_id not in self.engine.physics.robots:
            return False
        self.engine.inject_failure(robot_id, reason="hardware_breakdown")
        if robot_id in self.agents:
            self.agents[robot_id].state.transition_to(RobotStatus.FAILED)
        return True

    def inject_obstacle(
        self,
        obstacle_id: str,
        x: int,
        y: int,
        duration: int = 20,
    ) -> bool:
        """Inject dynamic obstacle into environment."""
        if not self.engine:
            return False
        current_tick = self.engine.clock.current_tick
        self.engine.add_obstacle(
            x=x,
            y=y,
            start_tick=current_tick,
            duration=duration,
            obstacle_id=obstacle_id,
        )
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "version": "0.1.0",
            "active_agents": len(self.agents),
            "grid_dimensions": [self.grid.width, self.grid.height] if self.grid else [16, 12],
            "tick": self.engine.clock.current_tick if self.engine else 0,
            "scenario_name": self.grid.name if self.grid else "none",
            "robots_count": len(self.agents),
            "tasks_count": len(self.tasks),
            "speed": self.speed,
            "metadata": {
                "engine": "decentralized-asyncio",
                "controller": "none",
            },
        }

    def get_robots(self) -> List[Dict[str, Any]]:
        results = []
        for r_id, agent in self.agents.items():
            phys = self.engine.physics.robots.get(r_id) if self.engine else None
            results.append({
                "id": r_id,
                "robot_id": r_id,
                "position": [phys.x, phys.y] if phys else list(agent.state.position),
                "battery": round(phys.battery_level if phys else agent.state.battery, 1),
                "status": phys.status.value if phys else agent.state.status.value,
                "carrying_item": phys.carried_item_id if phys else agent.state.carrying_item,
                "task_id": agent.state.task_id,
                "current_path": [list(p) for p in agent.state.current_path],
                "path": [list(p) for p in agent.state.current_path],
                "priority": agent.state.priority,
            })
        return results

    def get_robot(self, robot_id: str) -> Optional[Dict[str, Any]]:
        for r in self.get_robots():
            if r["id"] == robot_id or r["robot_id"] == robot_id:
                return r
        return None

    def get_tasks(self) -> List[Dict[str, Any]]:
        results = []
        for t_id, t_dict in self.tasks.items():
            status_val = t_dict.get("status", "UNASSIGNED")
            assigned_robot = None
            for agent in self.agents.values():
                if t_id in agent.task_manager.known_tasks:
                    kt = agent.task_manager.known_tasks[t_id]
                    status_val = kt.status.value
                    if kt.assigned_robot_id:
                        assigned_robot = kt.assigned_robot_id
                        break

            p_pos = t_dict.get("pickup_position") or t_dict.get("pickup_pos", [0, 0])
            d_pos = t_dict.get("delivery_position") or t_dict.get("delivery_pos", [0, 0])
            results.append({
                "id": t_id,
                "task_id": t_id,
                "pickup_location": list(p_pos),
                "pickup_position": list(p_pos),
                "delivery_location": list(d_pos),
                "delivery_position": list(d_pos),
                "status": status_val,
                "priority": t_dict.get("priority", 1),
                "item_type": t_dict.get("item_type", "standard_pod"),
                "assigned_robot": assigned_robot,
                "spawn_tick": t_dict.get("spawn_tick", 0),
            })
        return results

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        for t in self.get_tasks():
            if t["id"] == task_id or t["task_id"] == task_id:
                return t
        return None

    def get_events(self) -> List[Dict[str, Any]]:
        if not self.engine:
            return []
        return [e.to_dict() for e in self.engine.event_log._events]

    def get_telemetry_snapshot(self) -> Dict[str, Any]:
        """Construct full JSON telemetry snapshot for frontend visualization."""
        tick = self.engine.clock.current_tick if self.engine else 0
        robots_list = self.get_robots()
        tasks_list = self.get_tasks()

        # Reservations aggregation from agent tables
        reservations_list = []
        for agent in self.agents.values():
            if hasattr(agent, "reservations") and agent.reservations:
                for res in agent.reservations.get_active_reservations(tick):
                    reservations_list.append({
                        "x": res.cell[0],
                        "y": res.cell[1],
                        "tick": res.time_tick,
                        "owner": res.owner,
                        "priority": res.priority,
                    })

        # Obstacles
        obstacles_list = []
        if self.engine:
            for obs in self.engine.obstacle_manager._obstacles.values():
                if obs.is_alive_at(tick):
                    obstacles_list.append({
                        "id": obs.obstacle_id,
                        "x": obs.x,
                        "y": obs.y,
                        "type": obs.obstacle_type.value if hasattr(obs.obstacle_type, "value") else str(obs.obstacle_type),
                        "start_tick": obs.start_tick,
                        "duration": obs.duration or 50,
                    })

        # Recent P2P messages
        recent_msgs = []
        if hasattr(self.network, "_all_sent_messages"):
            recent_msgs = self.network._all_sent_messages[-25:]
        elif hasattr(self.network, "_delivery_log"):
            recent_msgs = [
                {
                    "id": m.message_id,
                    "from": m.sender,
                    "to": m.recipient,
                    "type": m.type.value if hasattr(m.type, "value") else str(m.type),
                    "tick": m.send_tick,
                    "timestamp": m.timestamp,
                }
                for m in self.network._delivery_log[-25:]
            ]

        # Evaluation metrics
        eval_report = MetricsEvaluator.evaluate(self.metrics_collector)
        completed_tasks_count = sum(1 for t in tasks_list if t["status"] == "DELIVERED")
        metrics_dict = {
            "total_tasks_completed": completed_tasks_count,
            "total_tasks_spawned": len(tasks_list),
            "throughput_tasks_per_hour": round((completed_tasks_count / max(1, tick)) * 3600.0 / 10.0, 1),
            "average_completion_time_ticks": eval_report.avg_completion_time,
            "average_waiting_time_ticks": eval_report.avg_waiting_time,
            "conflicts_detected": eval_report.conflicts_detected,
            "conflicts_resolved": eval_report.conflicts_resolved,
            "deadlocks_detected": eval_report.deadlocks_detected,
            "deadlocks_resolved": eval_report.deadlocks_resolved,
            "replanning_events": eval_report.replanning_events,
            "collisions_detected": eval_report.collisions_count,
            "messages_sent": getattr(self.network, "total_messages_sent", self.metrics_collector.messages_sent),
            "messages_received": getattr(self.network, "total_messages_delivered", self.metrics_collector.messages_received),
            "messages_dropped": getattr(self.network, "total_messages_lost", self.metrics_collector.messages_lost),
            "average_battery_consumed": eval_report.avg_energy_consumed_per_robot,
            "charging_events_count": eval_report.charging_events,
            "robot_failures_count": eval_report.robot_failures,
            "rescue_operations_count": eval_report.rescue_operations_completed,
        }

        # Events
        events_list = [e.to_dict() for e in self.engine.event_log.get_events(since_tick=0)] if self.engine else []

        return {
            "type": "SIMULATION_TELEMETRY",
            "tick": tick,
            "status": self.status.lower(),
            "robots": robots_list,
            "tasks": tasks_list,
            "obstacles": obstacles_list,
            "reservations": reservations_list,
            "recent_messages": recent_msgs,
            "events": events_list,
            "metrics": metrics_dict,
        }


simulation_service = SimulationService()
