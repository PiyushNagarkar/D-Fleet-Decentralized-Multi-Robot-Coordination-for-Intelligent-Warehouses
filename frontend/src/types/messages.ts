/**
 * P2P Message Envelope and Protocol Types mirroring backend/app/robots/message.py
 */

export enum MessageType {
  ROBOT_STATE = "ROBOT_STATE",
  HEARTBEAT = "HEARTBEAT",
  TASK_ANNOUNCEMENT = "TASK_ANNOUNCEMENT",
  TASK_BID = "TASK_BID",
  TASK_CLAIMED = "TASK_CLAIMED",
  TASK_RELEASED = "TASK_RELEASED",
  RESERVATION_REQUEST = "RESERVATION_REQUEST",
  RESERVATION_GRANTED = "RESERVATION_GRANTED",
  RESERVATION_REJECTED = "RESERVATION_REJECTED",
  YIELD_REQUEST = "YIELD_REQUEST",
  YIELD_ACCEPTED = "YIELD_ACCEPTED",
  OBSTACLE_UPDATE = "OBSTACLE_UPDATE",
  PATH_INVALIDATED = "PATH_INVALIDATED",
  ROBOT_FAILURE = "ROBOT_FAILURE",
  TASK_REASSIGNMENT = "TASK_REASSIGNMENT",
  RESCUE_REQUIRED = "RESCUE_REQUIRED",
  DEADLOCK_ALERT = "DEADLOCK_ALERT",
}

export interface MessageEnvelope {
  message_id: string;
  type: MessageType;
  sender: string;
  recipient?: string | null;
  sequence: number;
  timestamp: number;
  send_tick: number;
  ttl: number;
  payload: Record<string, any>;
}

export interface CommunicationEvent {
  id: string;
  tick: number;
  from: string;
  to: string;
  type: MessageType;
  latency_ms?: number;
  status: "SENT" | "DELIVERED" | "DROPPED" | "DUPLICATED";
}
