"""Configurable Peer-to-Peer Virtual Network for Autonomous Robots."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import random
from typing import Dict, List, Optional, Set, Tuple, Any

from app.robots.message import Message, MessageType
from .latency import LatencyModel
from .packet_loss import PacketLossModel


class LinkCondition(str, Enum):
    NORMAL = "NORMAL"
    DELAYED = "DELAYED"
    LOSSY = "LOSSY"
    DUPLICATED = "DUPLICATED"
    STALE = "STALE"
    DISCONNECTED = "DISCONNECTED"


@dataclass
class LinkConfig:
    condition: LinkCondition = LinkCondition.NORMAL
    latency_ticks: int = 0
    jitter_ticks: int = 0
    loss_rate: float = 0.0
    duplicate_rate: float = 0.0


@dataclass
class InFlightPacket:
    message: Message
    delivery_tick: int


class P2PNetwork:
    """Simulated P2P network bus with per-link impairment injection."""

    def __init__(self, seed: Optional[int] = 42):
        self._rng = random.Random(seed)
        self._link_configs: Dict[Tuple[str, str], LinkConfig] = {}
        self._default_config = LinkConfig()
        self._in_flight: List[InFlightPacket] = []
        self._delivery_log: List[Message] = []
        self._all_sent_messages: List[Dict[str, Any]] = []
        self._registered_robots: Set[str] = set()

        # Telemetry counters
        self.total_messages_sent: int = 0
        self.total_messages_delivered: int = 0
        self.total_messages_lost: int = 0
        self.total_messages_duplicated: int = 0
        self.total_messages_stale: int = 0

    def register_robot(self, robot_id: str) -> None:
        self._registered_robots.add(robot_id)

    def set_link_config(
        self,
        sender: str,
        recipient: str,
        condition: LinkCondition = LinkCondition.NORMAL,
        latency_ticks: int = 0,
        jitter_ticks: int = 0,
        loss_rate: float = 0.0,
        duplicate_rate: float = 0.0,
    ) -> None:
        """Configure network impairment parameters for a specific unidirectional or bidirectional link."""
        self._link_configs[(sender, recipient)] = LinkConfig(
            condition=condition,
            latency_ticks=latency_ticks,
            jitter_ticks=jitter_ticks,
            loss_rate=loss_rate,
            duplicate_rate=duplicate_rate,
        )

    def get_link_config(self, sender: str, recipient: str) -> LinkConfig:
        return self._link_configs.get((sender, recipient), self._default_config)

    def send(self, message: Message, current_tick: int) -> bool:
        """Transmit a message over the simulated network according to link conditions.
        
        Returns True if packet was enqueued, False if dropped or disconnected.
        """
        self.total_messages_sent += 1
        cfg = self.get_link_config(message.sender, message.recipient)

        # 1. Disconnected condition
        if cfg.condition == LinkCondition.DISCONNECTED:
            self.total_messages_lost += 1
            return False

        # 2. Loss evaluation
        effective_loss = cfg.loss_rate if cfg.condition != LinkCondition.LOSSY else max(cfg.loss_rate, 0.5)
        if effective_loss > 0 and self._rng.random() < effective_loss:
            self.total_messages_lost += 1
            return False  # Packet lost

        # 3. Latency evaluation
        effective_latency = cfg.latency_ticks
        if cfg.condition == LinkCondition.DELAYED:
            effective_latency = max(effective_latency, 3)
        if cfg.jitter_ticks > 0:
            effective_latency += self._rng.randint(-cfg.jitter_ticks, cfg.jitter_ticks)
        effective_latency = max(0, effective_latency)

        # 4. Stale injection: if condition is STALE, deliver after message TTL has elapsed
        if cfg.condition == LinkCondition.STALE:
            effective_latency = message.ttl + 5
            self.total_messages_stale += 1

        delivery_tick = current_tick + effective_latency

        # Enqueue packet
        self._in_flight.append(InFlightPacket(message=message, delivery_tick=delivery_tick))
        self._all_sent_messages.append({
            "id": message.message_id,
            "from": message.sender,
            "to": message.recipient,
            "type": message.type.value if hasattr(message.type, "value") else str(message.type),
            "tick": current_tick,
            "timestamp": message.timestamp,
        })
        if len(self._all_sent_messages) > 100:
            self._all_sent_messages.pop(0)

        # 5. Duplication evaluation
        effective_dup = cfg.duplicate_rate if cfg.condition != LinkCondition.DUPLICATED else max(cfg.duplicate_rate, 1.0)
        if effective_dup > 0 and self._rng.random() < effective_dup:
            # Enqueue identical duplicate packet
            dup_delivery = delivery_tick + self._rng.randint(0, 1)
            self._in_flight.append(InFlightPacket(message=message, delivery_tick=dup_delivery))
            self.total_messages_duplicated += 1

        return True

    def broadcast(
        self,
        message: Message,
        recipients: Optional[List[str]] = None,
        current_tick: int = 0,
    ) -> int:
        """Send message copy to multiple recipients."""
        target_recipients = recipients if recipients else list(self._registered_robots)
        enqueued_count = 0
        for r_id in target_recipients:
            if r_id == message.sender:
                continue
            # Create recipient-addressed envelope
            msg_copy = Message(
                message_id=message.message_id,
                type=message.type,
                sender=message.sender,
                recipient=r_id,
                sequence=message.sequence,
                timestamp=message.timestamp,
                send_tick=current_tick,
                ttl=message.ttl,
                payload=dict(message.payload),
            )
            if self.send(msg_copy, current_tick):
                enqueued_count += 1
        return enqueued_count

    def deliver_for_robot(self, robot_id: str, current_tick: int) -> List[Message]:
        """Deliver all pending packets addressed to robot_id ready at or before current_tick."""
        delivered: List[Message] = []
        remaining: List[InFlightPacket] = []

        for pkt in self._in_flight:
            if pkt.delivery_tick <= current_tick and (
                pkt.message.recipient == robot_id or pkt.message.recipient == "BROADCAST"
            ):
                delivered.append(pkt.message)
                self._delivery_log.append(pkt.message)
            else:
                remaining.append(pkt)

        self.total_messages_delivered += len(delivered)
        self._in_flight = remaining
        return delivered

    def clear(self) -> None:
        self._in_flight.clear()
        self._delivery_log.clear()
        self._all_sent_messages.clear()
        self._link_configs.clear()
        self.total_messages_sent = 0
        self.total_messages_delivered = 0
        self.total_messages_lost = 0
        self.total_messages_duplicated = 0
        self.total_messages_stale = 0
