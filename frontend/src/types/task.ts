/**
 * Task Domain Types mirroring backend/app/tasks/task.py
 */

import { GridPosition } from "./robot";

export enum TaskStatus {
  UNASSIGNED = "UNASSIGNED",
  BIDDING = "BIDDING",
  CLAIMED = "CLAIMED",
  GOING_TO_PICKUP = "GOING_TO_PICKUP",
  PICKED_UP = "PICKED_UP",
  GOING_TO_DELIVERY = "GOING_TO_DELIVERY",
  DELIVERED = "DELIVERED",
  RELEASED = "RELEASED",
  FAILED = "FAILED",
  RESCUE_REQUIRED = "RESCUE_REQUIRED",
}

export interface TaskInfo {
  id: string;
  pickup_location: GridPosition;
  delivery_location: GridPosition;
  status: TaskStatus;
  priority: number;
  item_type: string;
  assigned_robot?: string | null;
  spawn_tick: number;
  claim_tick?: number | null;
  pickup_tick?: number | null;
  delivery_tick?: number | null;
  deadline_tick?: number | null;
  bids?: Record<string, number>;
  rescue_for_robot?: string | null;
}
