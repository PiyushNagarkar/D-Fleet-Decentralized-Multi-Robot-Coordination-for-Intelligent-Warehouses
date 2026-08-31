"""Scenario Manager for discovering and loading warehouse scenarios."""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from app.simulation.warehouse import WarehouseGrid


class ScenarioManager:
    """Discovers and parses warehouse scenario files."""

    def __init__(self, scenarios_dir: Optional[str] = None):
        if scenarios_dir:
            self.scenarios_dir = Path(scenarios_dir)
        else:
            # Default to workspace scenarios directory
            base_dir = Path(__file__).resolve().parents[3]
            self.scenarios_dir = base_dir / "scenarios"

    def list_scenarios(self) -> List[Dict[str, Any]]:
        """List all available scenario files with metadata."""
        results = []
        if not self.scenarios_dir.exists():
            return results

        for p in self.scenarios_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results.append({
                        "id": p.stem,
                        "name": data.get("name", p.stem),
                        "description": data.get("description", ""),
                        "filename": p.name,
                        "dimensions": {
                            "width": data.get("grid", {}).get("width", 0),
                            "height": data.get("grid", {}).get("height", 0),
                        },
                        "robots_count": len(data.get("robots", [])),
                        "tasks_count": len(data.get("tasks", [])),
                    })
            except Exception:
                continue

        return results

    def load_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """Load scenario definition by ID."""
        if not self.scenarios_dir.exists():
            return None

        # Check by ID (stem) or full filename
        target_path = self.scenarios_dir / f"{scenario_id}.json"
        if not target_path.exists():
            target_path = self.scenarios_dir / scenario_id
            if not target_path.exists():
                return None

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None


scenario_manager = ScenarioManager()
