#!/usr/bin/env python3
"""Custom Scenario Generator for D-Fleet Warehouse Simulations.

Generates reproducible scenario JSON definitions.

Usage:
    python scripts/generate_scenario.py --name custom_rush --robots 4 --tasks 10 --output scenarios/custom_rush.json
"""

from __future__ import annotations
import argparse
import json
import random
from pathlib import Path


def generate_scenario(
    name: str,
    num_robots: int = 4,
    num_tasks: int = 8,
    width: int = 14,
    height: int = 10,
    seed: int = 42,
    comm_delay: int = 0,
    packet_loss: float = 0.0,
) -> dict:
    rng = random.Random(seed)

    # Standard warehouse layout template
    layout = [
        "#" * width,
        "#C..." + "P.." * ((width - 8) // 3) + "D..#",
        "#..." + "#" * (width - 6) + ".#",
        "#...#" + "." * (width - 8) + "#.#",
        "#.I.#" + ".I." * ((width - 8) // 3) + "#.#",
        "#...#" + "." * (width - 8) + "#.#",
        "#..." + "#" * (width - 6) + ".#",
        "#C..." + "P.." * ((width - 8) // 3) + "D..#",
        "#" + "." * (width - 2) + "#",
        "#" * width,
    ]

    # Generate robots
    robots = []
    spawn_candidates = [(1, 1), (1, 7), (width - 2, 1), (width - 2, 7), (1, 4), (width - 2, 4)]
    for i in range(min(num_robots, len(spawn_candidates))):
        r_id = f"R{i+1}"
        robots.append({
            "id": r_id,
            "start_pos": list(spawn_candidates[i]),
            "priority": (i % 3) + 1,
            "battery": rng.uniform(85.0, 100.0),
        })

    # Generate tasks
    tasks = []
    for i in range(num_tasks):
        t_id = f"task_gen_{i+1:02d}"
        p_x = rng.choice([4, 5, 6])
        p_y = rng.choice([1, 7])
        d_x = rng.choice([width - 4, width - 3])
        d_y = rng.choice([1, 7])
        tasks.append({
            "id": t_id,
            "pickup_pos": [p_x, p_y],
            "delivery_pos": [d_x, d_y],
            "priority": rng.randint(1, 4),
            "item_type": f"pod_{chr(65 + (i % 26))}",
        })

    # Dynamic obstacles
    obstacles = [
        {
            "id": "forklift_alpha",
            "x": 3,
            "y": 4,
            "obstacle_type": "MOVING",
            "start_tick": 0,
            "duration": 60,
            "waypoints": [{"x": 3, "y": 4}, {"x": 4, "y": 4}, {"x": 5, "y": 4}, {"x": 4, "y": 4}],
            "speed_ticks_per_step": 2,
        },
        {
            "id": "spill_spontaneous",
            "x": width // 2,
            "y": 7,
            "obstacle_type": "STATIC",
            "start_tick": 6,
            "duration": 20,
        },
    ]

    return {
        "name": name,
        "description": f"Generated reproducible scenario: {name} with {num_robots} robots and {num_tasks} tasks",
        "seed": seed,
        "width": width,
        "height": height,
        "cell_size": 1.0,
        "layout": layout,
        "robots": robots,
        "tasks": tasks,
        "obstacles": obstacles,
        "failures": [],
        "communication": {
            "delay": comm_delay,
            "packet_loss": packet_loss,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="D-Fleet Scenario Generator")
    parser.add_argument("--name", type=str, default="generated_scenario", help="Scenario identifier name")
    parser.add_argument("--robots", type=int, default=4, help="Number of robots (1-6)")
    parser.add_argument("--tasks", type=int, default=8, help="Number of tasks")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    data = generate_scenario(
        name=args.name,
        num_robots=args.robots,
        num_tasks=args.tasks,
        seed=args.seed,
    )

    out_path = Path(args.output) if args.output else Path(__file__).resolve().parent.parent / "scenarios" / f"{args.name}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Generated scenario successfully written to: {out_path}")


if __name__ == "__main__":
    main()
