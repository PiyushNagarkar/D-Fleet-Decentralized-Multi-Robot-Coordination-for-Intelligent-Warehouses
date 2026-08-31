"""Simulated Peer-to-Peer Communication Network for Decentralized Robots.

Supports simulated transmission latency, packet loss, and out-of-order delivery
to test distributed consensus under realistic network degradation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import random
import uuid


@dataclass
class PeerMessage:
    """A message transmitted directly between two autonomous robots or broadcast."""
    sender_id: str
    recipient_id: str  # Can be a specific robot_id or "BROADCAST"
    message_type: str  # e.g., "OBSTACLE_ALERT", "RESERVATION_REQUEST", "TASK_BID", etc.
    payload: Dict[str, Any]
    send_tick: int
    delivery_tick: int
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "message_type": self.message_type,
            "payload": self.payload,
            "send_tick": self.send_tick,
            "delivery_tick": self.delivery_tick,
        }


class DelayedMessageChannel:
    """In-memory communication bus simulating network delays and packet drops."""

    def __init__(
        self,
        default_latency_ticks: int = 0,
        drop_probability: float = 0.0,
        seed: Optional[int] = 42,
    ):
        self.default_latency_ticks = default_latency_ticks
        self.drop_probability = drop_probability
        self._rng = random.Random(seed)
        self._in_flight: List[PeerMessage] = []
        self._delivered_history: List[PeerMessage] = []

    def send(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: str,
        payload: Dict[str, Any],
        current_tick: int,
        latency_ticks: Optional[int] = None,
        force_drop: bool = False,
    ) -> Optional[PeerMessage]:
        """Transmit a message over the simulated network."""
        # Check packet loss
        if force_drop or (self.drop_probability > 0 and self._rng.random() < self.drop_probability):
            return None  # Packet dropped

        effective_latency = self.default_latency_ticks if latency_ticks is None else latency_ticks
        delivery_tick = current_tick + max(0, effective_latency)

        msg = PeerMessage(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=message_type,
            payload=payload,
            send_tick=current_tick,
            delivery_tick=delivery_tick,
        )
        self._in_flight.append(msg)
        return msg

    def broadcast(
        self,
        sender_id: str,
        recipient_ids: List[str],
        message_type: str,
        payload: Dict[str, Any],
        current_tick: int,
        latency_ticks: Optional[int] = None,
    ) -> List[PeerMessage]:
        """Broadcast a message to multiple recipients individually."""
        sent_messages = []
        for r_id in recipient_ids:
            if r_id == sender_id:
                continue
            msg = self.send(
                sender_id=sender_id,
                recipient_id=r_id,
                message_type=message_type,
                payload=payload,
                current_tick=current_tick,
                latency_ticks=latency_ticks,
            )
            if msg:
                sent_messages.append(msg)
        return sent_messages

    def deliver_for_robot(self, robot_id: str, current_tick: int) -> List[PeerMessage]:
        """Retrieve all messages scheduled for delivery to a specific robot up to current_tick."""
        delivered = []
        remaining = []

        for msg in self._in_flight:
            if msg.delivery_tick <= current_tick and (
                msg.recipient_id == robot_id or msg.recipient_id == "BROADCAST"
            ):
                delivered.append(msg)
                self._delivered_history.append(msg)
            else:
                remaining.append(msg)

        self._in_flight = remaining
        return delivered

    def clear(self) -> None:
        self._in_flight.clear()
        self._delivered_history.clear()
