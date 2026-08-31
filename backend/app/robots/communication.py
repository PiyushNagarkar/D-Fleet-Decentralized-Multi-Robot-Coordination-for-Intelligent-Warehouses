from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, Any
import time

from .message import Message, MessageType

if TYPE_CHECKING:
    from app.communication.network import P2PNetwork


@dataclass
class PendingRequest:
    """Tracks an outgoing request awaiting peer response with retry logic."""
    request_id: str
    request_type: MessageType
    recipient: str
    sent_tick: int
    timeout_ticks: int = 5
    max_retries: int = 3
    retries_count: int = 0
    payload: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    response: Optional[Message] = None

    def has_timed_out(self, current_tick: int) -> bool:
        return (not self.resolved) and (current_tick >= self.sent_tick + self.timeout_ticks)

    def can_retry(self) -> bool:
        return (not self.resolved) and (self.retries_count < self.max_retries)


class RobotCommunicator:
    """Handles sending, receiving, deduplicating, and managing timeouts for robot messages.

    CRITICAL ROBUSTNESS INVARIANTS:
    1. Idempotency: Duplicate messages with previously-seen message_id are discarded.
    2. Freshness: Stale messages exceeding TTL are dropped.
    3. Timeout & Retry: Unanswered requests trigger retries or rerouting rather than deadlock.
    """

    def __init__(
        self,
        robot_id: str,
        network: P2PNetwork,
        default_ttl: int = 20,
        max_seen_history: int = 2000,
    ):
        self.robot_id = robot_id
        self.network = network
        self.default_ttl = default_ttl
        self.max_seen_history = max_seen_history

        # Auto-register with network
        self.network.register_robot(robot_id)

        self.sequence_counter: int = 0
        self.seen_message_ids: Set[str] = set()
        self.inbox: List[Message] = []
        self.outbox: List[Message] = []
        self.pending_requests: Dict[str, PendingRequest] = {}  # request_id -> PendingRequest

    def create_message(
        self,
        msg_type: MessageType,
        recipient: str,
        payload: Dict[str, Any],
        current_tick: int,
        ttl: Optional[int] = None,
        custom_message_id: Optional[str] = None,
    ) -> Message:
        """Construct an outbound envelope with incremented sequence."""
        self.sequence_counter += 1
        msg = Message(
            message_id=custom_message_id or f"msg_{self.robot_id}_{self.sequence_counter}_{int(time.time()*1000)}",
            type=msg_type,
            sender=self.robot_id,
            recipient=recipient,
            sequence=self.sequence_counter,
            timestamp=time.time(),
            send_tick=current_tick,
            ttl=ttl or self.default_ttl,
            payload=payload,
        )
        return msg

    def send(
        self,
        msg_type: MessageType,
        recipient: str,
        payload: Dict[str, Any],
        current_tick: int,
        ttl: Optional[int] = None,
    ) -> Message:
        """Create and transmit a message over the simulated network."""
        msg = self.create_message(msg_type, recipient, payload, current_tick, ttl)
        self.outbox.append(msg)
        self.network.send(msg, current_tick)
        return msg

    def broadcast(
        self,
        msg_type: MessageType,
        payload: Dict[str, Any],
        current_tick: int,
        recipients: Optional[List[str]] = None,
        ttl: Optional[int] = None,
    ) -> Message:
        """Broadcast a message to peer robots."""
        msg = self.create_message(msg_type, "BROADCAST", payload, current_tick, ttl)
        self.outbox.append(msg)
        self.network.broadcast(msg, recipients, current_tick)
        return msg

    def send_request_with_retry(
        self,
        msg_type: MessageType,
        recipient: str,
        payload: Dict[str, Any],
        current_tick: int,
        timeout_ticks: int = 5,
        max_retries: int = 3,
    ) -> PendingRequest:
        """Send a request message and register it in the timeout/retry tracker."""
        msg = self.send(msg_type, recipient, payload, current_tick)
        req = PendingRequest(
            request_id=msg.message_id,
            request_type=msg_type,
            recipient=recipient,
            sent_tick=current_tick,
            timeout_ticks=timeout_ticks,
            max_retries=max_retries,
            payload=payload,
        )
        self.pending_requests[msg.message_id] = req
        return req

    def receive_and_process_inbox(self, current_tick: int) -> List[Message]:
        """Fetch delivered messages, filter out stale and duplicate messages, and return valid items."""
        raw_messages = self.network.deliver_for_robot(self.robot_id, current_tick)
        valid_messages: List[Message] = []

        for msg in raw_messages:
            # 1. Deduplication check (Idempotency invariant)
            if msg.message_id in self.seen_message_ids:
                continue  # Discard duplicate

            # 2. Freshness / Stale check (TTL invariant)
            if msg.is_stale(current_tick):
                continue  # Discard stale message

            # Record message_id as seen
            self.seen_message_ids.add(msg.message_id)
            if len(self.seen_message_ids) > self.max_seen_history:
                # Maintain bounded history
                self.seen_message_ids.pop()

            valid_messages.append(msg)

            # Check if this resolves a pending request
            in_reply_to = msg.payload.get("in_reply_to")
            if in_reply_to and in_reply_to in self.pending_requests:
                req = self.pending_requests[in_reply_to]
                req.resolved = True
                req.response = msg

        self.inbox.extend(valid_messages)
        return valid_messages

    def check_pending_timeouts(self, current_tick: int) -> Tuple[List[PendingRequest], List[PendingRequest]]:
        """Check status of active requests.

        Returns:
            (retried_requests, dead_timed_out_requests)
        """
        retried = []
        dead = []

        for req_id, req in list(self.pending_requests.items()):
            if req.resolved:
                continue

            if req.has_timed_out(current_tick):
                if req.can_retry():
                    # Retry transmission
                    req.retries_count += 1
                    req.sent_tick = current_tick
                    self.send(req.request_type, req.recipient, req.payload, current_tick)
                    retried.append(req)
                else:
                    # Exceeded retries: mark dead so robot can initiate reroute/fallback
                    req.resolved = True
                    dead.append(req)

        return retried, dead
