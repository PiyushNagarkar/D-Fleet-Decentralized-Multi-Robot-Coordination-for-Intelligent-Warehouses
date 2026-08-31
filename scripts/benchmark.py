#!/usr/bin/env python3
"""D-Fleet Benchmark Evaluator: Decentralized vs Centralized Stop-and-Go Baseline.

Executes identical scenarios under both modes and computes dynamic improvement metrics.

Usage:
    python scripts/benchmark.py --scenario normal.json --ticks 50
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.api.scenarios import ScenarioManager
from app.metrics.comparison import ComparisonEngine


def main():
    parser = argparse.ArgumentParser(description="D-Fleet vs Stop-and-Go Benchmark Evaluator")
    parser.add_argument("--scenario", type=str, default="complete_demo.json", help="Scenario JSON filename")
    parser.add_argument("--ticks", type=int, default=50, help="Number of ticks to execute per mode")
    parser.add_argument("--seed", type=int, default=None, help="Random seed override")
    args = parser.parse_args()

    scenarios_dir = Path(__file__).resolve().parent.parent / "scenarios"
    scenario_manager = ScenarioManager(scenarios_dir=str(scenarios_dir))
    scenario = scenario_manager.load_scenario(args.scenario)
    if not scenario:
        print(f"Error: Scenario '{args.scenario}' not found in {scenarios_dir}")
        sys.exit(1)

    seed = args.seed if args.seed is not None else scenario.get("seed", 42)
    name = scenario.get("name", "scenario")
    print(f"\n==========================================================================")
    print(f" D-FLEET COMPARATIVE BENCHMARK EVALUATOR")
    print(f" Scenario: {name} ({args.scenario}) | Seed: {seed} | Ticks: {args.ticks}")
    print(f"==========================================================================\n")

    print("[1/2] Running DECENTRALIZED D-FLEET mode...")
    from app.simulation.warehouse import WarehouseGrid
    warehouse = WarehouseGrid.from_ascii(scenario.get("layout", []), name=name)
    robots_cfg = scenario.get("robots", [])
    tasks_cfg = scenario.get("tasks", [])

    comparison = ComparisonEngine.run_benchmark_comparison(
        warehouse=warehouse,
        robots_config=robots_cfg,
        tasks_config=tasks_cfg,
        max_ticks=args.ticks,
        seed=seed,
    )
    print("[2/2] Running CENTRALIZED STOP-AND-GO Baseline mode...")
    print("      Benchmark completed successfully.\n")

    print(f"{'METRIC':<30} | {'D-FLEET':<14} | {'BASELINE':<14} | {'ADVANTAGE':<12}")
    print(f"{'-'*30}-+-{'-'*14}-+-{'-'*14}-+-{'-'*12}")

    for metric_name, result in comparison.comparisons.items():
        df_str = f"{result['dfleet']:.1f}"
        bs_str = f"{result['baseline']:.1f}"
        imp = result['improvement_percentage']
        imp_str = f"+{imp:.1f}%" if imp > 0 else f"{imp:.1f}%"
        print(f"{metric_name:<30} | {df_str:<14} | {bs_str:<14} | {imp_str:<12}")

    print(f"==========================================================================\n")
    print(f"Summary: {comparison.summary}\n")


if __name__ == "__main__":
    main()
