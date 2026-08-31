"""Message Envelope and Types for Decentralized Robot Communication."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, Optional
import uuid


class MessageType(str, Enum):
    ROBOT_STATE = "ROBOT_STATE"
    HEARTBEAT = "HEARTBEAT"
    TASK_ANNOUNCEMENT = "TASK_ANNOUNCEMENT"
    TASK_BID = "TASK_BID"
    TASK_CLAIMED = "TASK_CLAIMED"
    TASK_RELEASED = "TASK_RELEASED"
    RESERVATION_REQUEST = "RESERVATION_REQUEST"
    RESERVATION_GRANTED = "RESERVATION_GRANTED"
    RESERVATION_REJECTED = "RESERVATION_REJECTED"
    YIELD_REQUEST = "YIELD_REQUEST"
    YIELD_ACCEPTED = "YIELD_ACCEPTED"
    OBSTACLE_UPDATE = "OBSTACLE_UPDATE"
    PATH_INVALIDATED = "PATH_INVALIDATED"
    ROBOT_FAILURE = "ROBOT_FAILURE"
    TASK_REASSIGNMENT = "TASK_REASSIGNMENT"
    DEADLOCK_ALERT = "DEADLOCK_ALERT"


@dataclass(frozen=True)
class Message:
    """Standardized message envelope for all robot-to-robot communication."""
    type: MessageType
    sender: str
    recipient: str  # specific robot_id or "BROADCAST"
    payload: Dict[str, Any]
    sequence: int = 0
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    send_tick: int = 0
    ttl: int = 20  # Time-to-live in ticks

    def is_stale(self, current_tick: int) -> bool:
        """Check if message is expired relative to current simulation tick."""
        return current_tick > self.send_tick + self.ttl

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "type": self.type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "send_tick": self.send_tick,
            "ttl": self.ttl,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Message:
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            type=MessageType(data["type"]),
            sender=data["sender"],
            recipient=data.get("recipient", "BROADCAST"),
            sequence=data.get("sequence", 0),
            timestamp=data.get("timestamp", time.time()),
            send_tick=data.get("send_tick", 0),
            ttl=data.get("ttl", 20),
            payload=data.get("payload", {}),
        )
