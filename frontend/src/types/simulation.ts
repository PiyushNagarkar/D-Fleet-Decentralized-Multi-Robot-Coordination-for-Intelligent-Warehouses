/**
 * Simulation Telemetry, Metrics, and Scenario Types mirroring backend models
 */

import { RobotTelemetry, GridPosition } from "./robot";
import { TaskInfo } from "./task";
import { CommunicationEvent } from "./messages";

export interface SimulationStatus {
  status: "idle" | "running" | "paused" | "completed" | "error";
  current_tick: number;
  active_scenario?: string | null;
  speed: number;
}

export interface DynamicObstacle {
  id: string;
  x: number;
  y: number;
  type: "STATIC" | "MOVING";
  start_tick: number;
  duration: number;
  waypoints?: GridPosition[];
}

export interface SimulationMetrics {
  total_tasks_completed: number;
  total_tasks_spawned: number;
  throughput_tasks_per_hour: number;
  average_completion_time_ticks: number;
  average_waiting_time_ticks: number;
  conflicts_detected: number;
  conflicts_resolved: number;
  deadlocks_detected: number;
  deadlocks_resolved: number;
  replanning_events: number;
  collisions_detected: number;
  messages_sent: number;
  messages_received: number;
  messages_dropped: number;
  average_battery_consumed: number;
  charging_events_count: number;
  robot_failures_count: number;
  rescue_operations_count: number;
}

export interface SimulationEvent {
  event_id: string;
  event_type: string;
  tick: number;
  robot_id?: string | null;
  location?: GridPosition | null;
  payload: Record<string, any>;
  timestamp?: number;
}

export interface ActiveNegotiation {
  id: string;
  robot_a: string;
  robot_b: string;
  priority_a: number;
  priority_b: number;
  decision: string;
  location?: [number, number];
  status: "ACTIVE" | "RESOLVED";
  tick: number;
}

export interface TelemetrySnapshot {
  tick: number;
  status: "idle" | "running" | "paused" | "completed";
  robots: RobotTelemetry[];
  tasks: TaskInfo[];
  obstacles: DynamicObstacle[];
  reservations: Array<{ x: number; y: number; tick: number; owner: string; priority?: number }>;
  events: SimulationEvent[];
  recent_messages: CommunicationEvent[];
  active_negotiations?: ActiveNegotiation[];
  metrics: SimulationMetrics;
}

export interface ScenarioDefinition {
  name: string;
  description: string;
  seed: number;
  width: number;
  height: number;
  cell_size: number;
  layout: string[];
  robots: Array<{ id: string; start_pos: GridPosition; priority: number; battery: number }>;
  tasks: Array<{ id: string; pickup_pos: GridPosition; delivery_pos: GridPosition; priority: number; item_type: string }>;
  obstacles: Array<any>;
  failures: Array<any>;
  communication: { delay: number; packet_loss: number };
}

export interface BaselineComparison {
  metric_name: string;
  dfleet_value: number;
  baseline_value: number;
  improvement_pct: number;
  unit: string;
  is_lower_better: boolean;
}
