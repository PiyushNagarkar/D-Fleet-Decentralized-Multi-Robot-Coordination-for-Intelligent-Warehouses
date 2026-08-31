/**
 * Coordinate Conversion Utilities for 3D Warehouse Visualization
 *
 * Matches server-side conversion:
 * world_x = grid_x * CELL_SIZE
 * world_z = grid_y * CELL_SIZE
 */

export const CELL_SIZE = 1.0;

export function gridToWorld(
  gridX: number,
  gridY: number,
  heightOffset: number = 0.0
): [number, number, number] {
  return [gridX * CELL_SIZE, heightOffset, gridY * CELL_SIZE];
}

export function worldToGrid(worldX: number, worldZ: number): [number, number] {
  return [Math.round(worldX / CELL_SIZE), Math.round(worldZ / CELL_SIZE)];
}

const ROBOT_COLOR_PALETTE: Record<string, string> = {
  R1: "#0284c7", // Blue (Tailwind cyan/sky)
  R2: "#10b981", // Green (Emerald)
  R3: "#f97316", // Orange
  R4: "#a855f7", // Purple
  R5: "#ec4899", // Pink
  R6: "#eab308", // Yellow
  R7: "#14b8a6", // Teal
  R8: "#6366f1", // Indigo
};

export function getRobotColor(robotId: string): string {
  if (ROBOT_COLOR_PALETTE[robotId]) {
    return ROBOT_COLOR_PALETTE[robotId];
  }
  // Deterministic fallback hash for higher robot IDs
  const colors = Object.values(ROBOT_COLOR_PALETTE);
  let hash = 0;
  for (let i = 0; i < robotId.length; i++) {
    hash = robotId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}
