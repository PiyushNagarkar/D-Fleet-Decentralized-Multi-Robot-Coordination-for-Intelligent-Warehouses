/**
 * Robot Domain Types mirroring backend/app/robots/state.py
 */

export enum RobotStatus {
  IDLE = "IDLE",
  BIDDING = "BIDDING",
  CLAIMED = "CLAIMED",
  MOVING_TO_PICKUP = "MOVING_TO_PICKUP",
  PICKING_UP = "PICKING_UP",
  MOVING_TO_DELIVERY = "MOVING_TO_DELIVERY",
  DROPPING_OFF = "DROPPING_OFF",
  CHARGING = "CHARGING",
  LOW_BATTERY = "LOW_BATTERY",
  WAITING = "WAITING",
  YIELDING = "YIELDING",
  DEADLOCKED = "DEADLOCKED",
  FAILED = "FAILED",
}

export type GridPosition = [number, number];

export interface RobotReservation {
  x: number;
  y: number;
  tick: number;
  priority?: number;
}

export interface RobotState {
  id: string;
  position: GridPosition;
  status: RobotStatus;
  battery: number;
  carrying_item?: string | null;
  task_id?: string | null;
  priority: number;
  current_path?: GridPosition[];
  path_version?: number;
  waiting_ticks?: number;
  yield_count?: number;
  is_failed?: boolean;
}

export interface RobotTelemetry {
  id: string;
  position: GridPosition;
  status: RobotStatus;
  battery: number;
  carrying_item?: string | null;
  task_id?: string | null;
  priority: number;
  current_path?: GridPosition[];
}
