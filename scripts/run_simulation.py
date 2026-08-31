#!/usr/bin/env python3
"""Headless Simulation Runner for D-Fleet Multi-Robot Coordination.

Executes scenarios directly from CLI without requiring the web frontend.

Usage:
    python scripts/run_simulation.py --scenario complete_demo.json --ticks 50 --verbose
"""

from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.simulation.warehouse import WarehouseGrid
from app.simulation.engine import SimulationEngine
from app.communication.network import P2PNetwork
from app.robots.robot_agent import RobotAgent
from app.api.scenarios import ScenarioManager
from app.metrics.collector import MetricsCollector
from app.metrics.evaluator import MetricsEvaluator


def main():
    parser = argparse.ArgumentParser(description="D-Fleet Headless Simulation Runner")
    parser.add_argument("--scenario", type=str, default="complete_demo.json", help="Scenario JSON filename")
    parser.add_argument("--ticks", type=int, default=50, help="Number of ticks to execute")
    parser.add_argument("--seed", type=int, default=None, help="Random seed override")
    parser.add_argument("--verbose", action="store_true", help="Print detailed per-tick event stream")
    args = parser.parse_args()

    # Load scenario definition
    scenarios_dir = Path(__file__).resolve().parent.parent / "scenarios"
    scenario_manager = ScenarioManager(scenarios_dir=str(scenarios_dir))
    scenario = scenario_manager.load_scenario(args.scenario)
    if not scenario:
        print(f"Error: Scenario '{args.scenario}' not found in {scenarios_dir}")
        sys.exit(1)

    seed = args.seed if args.seed is not None else scenario.get("seed", 42)
    name = scenario.get("name", "scenario")
    width = scenario.get("width", 14)
    height = scenario.get("height", 10)
    robots_def = scenario.get("robots", [])
    tasks_def = scenario.get("tasks", [])
    obstacles_def = scenario.get("obstacles", [])
    failures_def = scenario.get("failures", [])
    layout_def = scenario.get("layout", [])

    print(f"\n============================================================")
    print(f" D-FLEET HEADLESS SIMULATION RUNNER")
    print(f" Scenario: {name} ({args.scenario}) | Seed: {seed}")
    print(f" Grid: {width}x{height} | Robots: {len(robots_def)} | Tasks: {len(tasks_def)}")
    print(f"============================================================\n")

    # Initialize environment and P2P network
    warehouse = WarehouseGrid.from_ascii(layout_def, name=name)
    engine = SimulationEngine(warehouse=warehouse, seed=seed)
    network = P2PNetwork(seed=seed)

    # Configure communication link degradation if specified
    comm_cfg = scenario.get("communication", {})
    if comm_cfg.get("delay", 0) > 0 or comm_cfg.get("packet_loss", 0.0) > 0.0:
        robot_ids = [r["id"] for r in robots_def]
        for src in robot_ids:
            for dst in robot_ids:
                if src != dst:
                    network.set_link_config(
                        src,
                        dst,
                        latency_ticks=comm_cfg.get("delay", 0),
                        loss_rate=comm_cfg.get("packet_loss", 0.0),
                    )

    # Spawn robots and instantiate independent agents
    agents: dict[str, RobotAgent] = {}
    for r_def in robots_def:
        r_id = r_def["id"]
        start_x, start_y = r_def["start_pos"]
        batt = r_def.get("battery", 100.0)
        prio = r_def.get("priority", 1)
        engine.spawn_robot(r_id, start_x, start_y, battery_level=batt)
        agents[r_id] = RobotAgent(
            robot_id=r_id,
            initial_position=(start_x, start_y),
            static_map=warehouse,
            network=network,
            priority=prio,
            battery=batt,
        )

    # Add dynamic obstacles
    for obs in obstacles_def:
        waypoints = obs.get("waypoints")
        wp_parsed = None
        if waypoints:
            wp_parsed = [(wp["x"], wp["y"]) if isinstance(wp, dict) else (wp[0], wp[1]) for wp in waypoints]
        engine.add_obstacle(
            x=obs["x"],
            y=obs["y"],
            start_tick=obs.get("start_tick", 0),
            duration=obs.get("duration", 50),
            obstacle_type=obs.get("obstacle_type", "STATIC"),
            obstacle_id=obs["id"],
            waypoints=wp_parsed,
            speed_ticks_per_step=obs.get("speed_ticks_per_step", 1),
        )

    # Inject tasks into engine and announce to agents
    for t_def in tasks_def:
        p_loc = (t_def["pickup_pos"][0], t_def["pickup_pos"][1])
        d_loc = (t_def["delivery_pos"][0], t_def["delivery_pos"][1])
        prio = t_def.get("priority", 1)
        itype = t_def.get("item_type", "standard_pod")
        engine.inject_task(
            task_id=t_def["id"],
            pickup_pos=p_loc,
            delivery_pos=d_loc,
            priority=prio,
            item_type=itype,
        )
        for agent in agents.values():
            agent.task_manager.on_task_announced(
                task_id=t_def["id"],
                pickup_location=p_loc,
                delivery_location=d_loc,
                priority=prio,
                spawn_tick=0,
                item_type=itype,
            )

    # Initialize metrics collector
    collector = MetricsCollector()
    start_time = time.time()

    # Step simulation loop
    for tick in range(args.ticks):
        # Process scheduled hardware failures
        for fail in failures_def:
            if fail.get("tick") == tick:
                engine.inject_failure(fail["robot_id"], reason=fail.get("reason", "hardware_fault"))

        # 1. Sense: retrieve local observations from simulation engine
        observations = engine.get_all_observations()

        # 2. Plan & Act: each robot agent executes its local decision cycle
        actions = {}
        for r_id, agent in agents.items():
            obs = observations[r_id]
            actions[r_id] = agent.step(obs)

        # 3. Environment Step: physical execution, collisions, obstacle steps
        engine.step(actions)

        # 4. Ingest events for metrics
        for evt in engine.event_log.get_events(since_tick=tick):
            collector.ingest_event(evt)
            if args.verbose:
                print(f"[T+{tick:04d}] {evt.event_type.value:<25} {evt.robot_id or 'ENV':<5} {evt.payload}")

    collector.total_ticks = args.ticks
    elapsed = time.time() - start_time
    report = MetricsEvaluator.evaluate(collector)

    print(f"\n============================================================")
    print(f" SIMULATION COMPLETED ({args.ticks} ticks in {elapsed:.3f}s)")
    print(f"============================================================")
    print(f" Tasks Completed:       {report.tasks_completed} / {report.tasks_total}")
    print(f" Task Throughput:       {report.throughput_per_100_ticks:.1f} tasks/100t")
    print(f" Avg Delivery Time:     {report.avg_completion_time:.1f} ticks")
    print(f" Avg Waiting Time:      {report.avg_waiting_time:.1f} ticks")
    print(f" Conflicts Resolved:    {report.conflicts_resolved} / {report.conflicts_detected}")
    print(f" Deadlocks Cleared:     {report.deadlocks_resolved} / {report.deadlocks_detected}")
    print(f" Collision Violations:  {report.collisions_count}")
    print(f" P2P Messages Sent:     {report.messages_sent} (Dropped: {report.messages_lost})")
    print(f" Dynamic Replans:       {report.replanning_events}")
    print(f" Rescue Operations:     {report.rescue_operations_completed}")
    print(f"============================================================\n")


if __name__ == "__main__":
    main()
