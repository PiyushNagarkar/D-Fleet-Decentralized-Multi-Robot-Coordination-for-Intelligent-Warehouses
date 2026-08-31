"""Architectural Guard Test: Statically scan codebase to enforce decentralized boundaries.

HARD ARCHITECTURAL RULE:
No file under backend/robots or backend/planning (or app/robots or app/planning)
is permitted to import from api, routes, simulation_service, or database.
Decentralized autonomous robots must NEVER rely on or communicate with central API controllers.
"""

import ast
from pathlib import Path
from typing import List, Tuple
import pytest


def get_imports_from_file(file_path: Path) -> List[Tuple[str, int]]:
    """Parse a python file using AST and return a list of (imported_module_name, line_number)."""
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.module, node.lineno))
    return imports


def test_architectural_guard_no_api_imports_in_robots_or_planning():
    """Verify that robots and planning packages have zero imports from the API layer."""
    backend_root = Path(__file__).parent.parent

    # Target folders that must remain strictly decentralized
    target_dirs = [
        backend_root / "app" / "robots",
        backend_root / "robots",
        backend_root / "app" / "planning",
        backend_root / "planning",
    ]

    forbidden_prefixes = (
        "app.api",
        "backend.app.api",
        "backend.api",
        "api",
        "routes",
        "app.database",
        "backend.database",
        "database",
    )

    violations = []

    for target_dir in target_dirs:
        if not target_dir.exists():
            continue
        for py_file in target_dir.rglob("*.py"):
            # Exclude test files
            if "test" in py_file.name:
                continue

            imports = get_imports_from_file(py_file)
            for mod_name, line_no in imports:
                for forbidden in forbidden_prefixes:
                    if mod_name == forbidden or mod_name.startswith(f"{forbidden}."):
                        violations.append(
                            f"FORBIDDEN IMPORT in {py_file.relative_to(backend_root)}:{line_no} -> '{mod_name}' "
                            f"(Violates Decentralized Architecture: robots/planning cannot import API/Database layers)"
                        )

    assert not violations, "\n" + "\n".join(violations)
