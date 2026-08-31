"""Isolated Stop-and-Go Baseline Coordinator and Multi-Mode Benchmark Comparison."""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
import copy

from app.simulation.warehouse import WarehouseGrid
from app.simulation.engine import SimulationEngine
from app.simulation.physics import ActionType
from app.communication.network import P2PNetwork
from app.robots.robot_agent import RobotAgent
from app.robots.motion_controller import MotionController
from app.planning.dstar_lite import DStarLite
from app.tasks.task import TaskStatus
from .collector import MetricsCollector
from .evaluator import MetricsEvaluator, SimulationReport


@dataclass
class MetricComparisonItem:
    metric_name: str
    dfleet_value: float
    baseline_value: float
    improvement_percentage: float  # Positive = D-Fleet is better
    higher_is_better: bool = False


@dataclass
class ComparisonReport:
    scenario_name: str
    dfleet_report: Dict[str, Any]
    baseline_report: Dict[str, Any]
    comparisons: Dict[str, Dict[str, Any]]
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StopAndGoBaselineCoordinator:
    """ISOLATED Centralized Stop-and-Go Baseline Coordinator.

    STRICT ISOLATION MANDATE:
    - This coordinator is used EXCLUSIVELY for benchmark comparison runs.
    - It enforces naive serialized stop-and-go coordination:
      Whenever two or more robots are active, it only allows ONE robot to move
      at a time while forcing all other robots to freeze and wait.
    - It is NEVER used as a fallback for the decentralized D-Fleet engine.
    """

    def __init__(self, warehouse: WarehouseGrid):
        self.warehouse = warehouse
        self.motion_controller = MotionController()

    def run(
        self,
        robots_config: List[Dict[str, Any]],
        tasks_config: List[Dict[str, Any]],
        max_ticks: int = 150,
        seed: int = 42,
    ) -> MetricsCollector:
        """Run the scenario using serialized Stop-and-Go coordinator."""
        engine = SimulationEngine(warehouse=self.warehouse, seed=seed)
        collector = MetricsCollector()

        # Initialize robot states
        robot_positions = {}
        robot_paths = {}
        robot_goals = {}
        robot_carrying = {}
        robot_tasks = {}
        robot_status = {}

        for r_cfg in robots_config:
            r_id = r_cfg["id"]
            start_pos = (r_cfg["start_pos"][0], r_cfg["start_pos"][1])
            engine.spawn_robot(r_id, start_pos[0], start_pos[1])
            robot_positions[r_id] = start_pos
            robot_paths[r_id] = []
            robot_goals[r_id] = None
            robot_carrying[r_id] = None
            robot_tasks[r_id] = None
            robot_status[r_id] = "IDLE"

        # Tasks to execute
        pending_tasks = copy.deepcopy(tasks_config)
        for t in pending_tasks:
            engine.inject_task(
                t["id"],
                tuple(t["pickup_pos"]),
                tuple(t["delivery_pos"]),
                item_type=t.get("item_type", "pod"),
            )

        active_robot_turn = 0
        robot_ids = [r["id"] for r in robots_config]

        for tick in range(max_ticks):
            collector.total_ticks = tick + 1

            # Dispatch unassigned tasks naively to idle robots
            for t in pending_tasks:
                if t.get("assigned"):
                    continue
                for r_id in robot_ids:
                    if robot_status[r_id] == "IDLE":
                        t["assigned"] = True
                        robot_tasks[r_id] = t
                        robot_status[r_id] = "MOVING_TO_PICKUP"
                        robot_goals[r_id] = tuple(t["pickup_pos"])
                        # Plan initial path
                        planner = DStarLite.from_grid(self.warehouse)
                        path = planner.plan(robot_positions[r_id], robot_goals[r_id])
                        robot_paths[r_id] = path[1:] if len(path) > 1 else []
                        break

            # SERIALIZED STOP-AND-GO LOGIC:
            # Only ONE robot is permitted to move this tick (round-robin token).
            # All other robots are forced to ActionType.WAIT (Stop).
            moving_robot_id = robot_ids[active_robot_turn % len(robot_ids)]
            active_robot_turn += 1

            actions = {}
            for r_id in robot_ids:
                if r_id == moving_robot_id and robot_paths[r_id]:
                    # Target robot moves
                    next_waypoint = robot_paths[r_id][0]
                    act = self.motion_controller.get_action_for_move(robot_positions[r_id], next_waypoint)
                    actions[r_id] = act
                    robot_paths[r_id].pop(0)
                    robot_positions[r_id] = next_waypoint
                elif r_id == moving_robot_id and robot_goals[r_id] == robot_positions[r_id]:
                    # Handle pickup or dropoff
                    cur_task = robot_tasks[r_id]
                    if cur_task and robot_status[r_id] == "MOVING_TO_PICKUP":
                        actions[r_id] = ActionType.PICKUP
                        robot_status[r_id] = "MOVING_TO_DELIVERY"
                        robot_goals[r_id] = tuple(cur_task["delivery_pos"])
                        planner = DStarLite.from_grid(self.warehouse)
                        path = planner.plan(robot_positions[r_id], robot_goals[r_id])
                        robot_paths[r_id] = path[1:] if len(path) > 1 else []
                    elif cur_task and robot_status[r_id] == "MOVING_TO_DELIVERY":
                        actions[r_id] = ActionType.DROPOFF
                        robot_status[r_id] = "IDLE"
                        robot_tasks[r_id] = None
                        robot_goals[r_id] = None
                    else:
                        actions[r_id] = ActionType.WAIT
                else:
                    # All other robots freeze/wait
                    actions[r_id] = ActionType.WAIT
                    collector.record_waiting_tick(r_id)

            engine.step(actions)
            collector.ingest_event_log(engine.event_log)

            # Stop if all tasks delivered
            all_done = all(t.get("assigned") for t in pending_tasks) and all(robot_status[r] == "IDLE" for r in robot_ids)
            if all_done:
                break

        return collector


class ComparisonEngine:
    """Executes identical scenarios under D-Fleet and Baseline modes and computes dynamic improvements."""

    @staticmethod
    def calculate_improvement(
        baseline_val: float,
        dfleet_val: float,
        higher_is_better: bool = False,
    ) -> float:
        """Compute relative percentage improvement.

        For lower-is-better metrics (e.g. completion time, waiting time, energy):
          improvement = (baseline - dfleet) / baseline * 100
        For higher-is-better metrics (e.g. throughput, utilization):
          improvement = (dfleet - baseline) / baseline * 100
        """
        if baseline_val == 0.0:
            return 0.0 if dfleet_val == 0.0 else (100.0 if higher_is_better else -100.0)

        if higher_is_better:
            return round(((dfleet_val - baseline_val) / abs(baseline_val)) * 100.0, 2)
        else:
            return round(((baseline_val - dfleet_val) / abs(baseline_val)) * 100.0, 2)

    @classmethod
    def run_benchmark_comparison(
        cls,
        warehouse: WarehouseGrid,
        robots_config: List[Dict[str, Any]],
        tasks_config: List[Dict[str, Any]],
        max_ticks: int = 150,
        seed: int = 42,
    ) -> ComparisonReport:
        """Run identical scenario under both D-Fleet (Decentralized) and Stop-and-Go Baseline."""

        # 1. Run D-Fleet Decentralized Simulation
        dfleet_collector = cls._run_dfleet_mode(warehouse, robots_config, tasks_config, max_ticks, seed)
        dfleet_report = MetricsEvaluator.evaluate(dfleet_collector)

        # 2. Run Stop-and-Go Baseline Simulation
        baseline_coordinator = StopAndGoBaselineCoordinator(warehouse)
        baseline_collector = baseline_coordinator.run(robots_config, tasks_config, max_ticks, seed)
        baseline_report = MetricsEvaluator.evaluate(baseline_collector)

        # 3. Compute relative improvements
        comparisons = {}
        metrics_to_compare = [
            ("avg_completion_time", False),
            ("total_waiting_time", False),
            ("avg_waiting_time", False),
            ("total_simulation_ticks", False),
            ("throughput_per_100_ticks", True),
            ("robot_utilization", True),
            ("total_energy_consumed", False),
        ]

        for metric_name, higher_is_better in metrics_to_compare:
            d_val = getattr(dfleet_report, metric_name, 0.0)
            b_val = getattr(baseline_report, metric_name, 0.0)
            imp = cls.calculate_improvement(b_val, d_val, higher_is_better)
            comparisons[metric_name] = {
                "dfleet": d_val,
                "baseline": b_val,
                "improvement_percentage": imp,
                "higher_is_better": higher_is_better,
            }

        return ComparisonReport(
            scenario_name=warehouse.name,
            dfleet_report=dfleet_report.to_dict(),
            baseline_report=baseline_report.to_dict(),
            comparisons=comparisons,
            summary=f"D-Fleet achieved {comparisons['avg_completion_time']['improvement_percentage']}% improvement in avg completion time over Stop-and-Go baseline.",
        )

    @classmethod
    def _run_dfleet_mode(
        cls,
        warehouse: WarehouseGrid,
        robots_config: List[Dict[str, Any]],
        tasks_config: List[Dict[str, Any]],
        max_ticks: int = 150,
        seed: int = 42,
    ) -> MetricsCollector:
        """Run D-Fleet multi-agent decentralized execution."""
        engine = SimulationEngine(warehouse=warehouse, seed=seed)
        network = P2PNetwork(seed=seed)
        collector = MetricsCollector()

        agents = {}
        for r_cfg in robots_config:
            r_id = r_cfg["id"]
            pos = (r_cfg["start_pos"][0], r_cfg["start_pos"][1])
            engine.spawn_robot(r_id, pos[0], pos[1])
            agent = RobotAgent(
                robot_id=r_id,
                initial_position=pos,
                static_map=warehouse,
                network=network,
                priority=r_cfg.get("priority", 1),
            )
            agents[r_id] = agent

        for t_cfg in tasks_config:
            t_id = t_cfg["id"]
            p_pos = (t_cfg["pickup_pos"][0], t_cfg["pickup_pos"][1])
            d_pos = (t_cfg["delivery_pos"][0], t_cfg["delivery_pos"][1])
            prio = t_cfg.get("priority", 1)
            item_type = t_cfg.get("item_type", "pod")
            engine.inject_task(t_id, p_pos, d_pos, priority=prio, item_type=item_type)
            for agent in agents.values():
                agent.task_manager.on_task_announced(t_id, p_pos, d_pos, priority=prio, item_type=item_type)

        for tick in range(max_ticks):
            collector.total_ticks = tick + 1
            observations = engine.get_all_observations()
            actions = {}
            for r_id, agent in agents.items():
                obs = observations.get(r_id)
                if obs:
                    act = agent.step(obs)
                    actions[r_id] = act
                    if act == ActionType.WAIT:
                        collector.record_waiting_tick(r_id)
                else:
                    actions[r_id] = ActionType.WAIT

            engine.step(actions)
            collector.ingest_event_log(engine.event_log)

            # Check if all tasks delivered
            all_delivered = all(
                any(
                    agent.task_manager.known_tasks.get(t["id"])
                    and agent.task_manager.known_tasks[t["id"]].status == TaskStatus.DELIVERED
                    for agent in agents.values()
                )
                for t in tasks_config
            )
            if all_delivered:
                break

        return collector
