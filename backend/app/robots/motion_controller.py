"""Motion Controller translating path waypoints into discrete physical actions."""

from __future__ import annotations
from typing import Optional, Tuple
from app.simulation.physics import ActionType, Direction


class MotionController:
    """Computes directional actions to transition between grid positions."""

    @staticmethod
    def get_action_for_move(
        current_pos: Tuple[int, int],
        target_pos: Tuple[int, int],
    ) -> ActionType:
        """Derive the physical ActionType required to move from current_pos to target_pos."""
        cx, cy = current_pos
        tx, ty = target_pos

        dx = tx - cx
        dy = ty - cy

        if dx == 0 and dy == -1:
            return ActionType.MOVE_NORTH
        elif dx == 0 and dy == 1:
            return ActionType.MOVE_SOUTH
        elif dx == 1 and dy == 0:
            return ActionType.MOVE_EAST
        elif dx == -1 and dy == 0:
            return ActionType.MOVE_WEST
        else:
            return ActionType.WAIT

    @staticmethod
    def heading_from_action(action: ActionType) -> Optional[Direction]:
        if action == ActionType.MOVE_NORTH:
            return Direction.NORTH
        elif action == ActionType.MOVE_SOUTH:
            return Direction.SOUTH
        elif action == ActionType.MOVE_EAST:
            return Direction.EAST
        elif action == ActionType.MOVE_WEST:
            return Direction.WEST
        return None
