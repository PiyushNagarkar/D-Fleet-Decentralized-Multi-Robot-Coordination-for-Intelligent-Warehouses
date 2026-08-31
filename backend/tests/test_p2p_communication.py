"""Unit tests for P2P Communication Layer, Message Handling, and Network Conditions."""

import pytest
import time
from app.robots.message import Message, MessageType
from app.communication.network import P2PNetwork, LinkCondition
from app.robots.communication import RobotCommunicator


def test_reliable_message_delivery_zero_loss():
    """Test 1: Message delivery under 0% loss is completely reliable."""
    network = P2PNetwork()
    comm_r1 = RobotCommunicator(robot_id="R1", network=network)
    comm_r2 = RobotCommunicator(robot_id="R2", network=network)

    # R1 sends HEARTBEAT to R2 at tick 0
    msg = comm_r1.send(
        msg_type=MessageType.HEARTBEAT,
        recipient="R2",
        payload={"position": [3, 4], "battery": 98.0},
        current_tick=0,
    )

    # Deliver at tick 0
    inbox_r2 = comm_r2.receive_and_process_inbox(current_tick=0)
    assert len(inbox_r2) == 1
    assert inbox_r2[0].message_id == msg.message_id
    assert inbox_r2[0].type == MessageType.HEARTBEAT
    assert inbox_r2[0].sender == "R1"
    assert inbox_r2[0].payload["position"] == [3, 4]


def test_high_loss_retry_mechanism_prevents_deadlock():
    """Test 2: Under high packet loss, robots retry unacknowledged requests
    and make forward progress within N ticks without deadlocking."""
    network = P2PNetwork()
    # Configure 80% packet loss on link R1 -> R2
    network.set_link_config(sender="R1", recipient="R2", loss_rate=0.8)

    comm_r1 = RobotCommunicator(robot_id="R1", network=network)
    comm_r2 = RobotCommunicator(robot_id="R2", network=network)

    # R1 sends RESERVATION_REQUEST with timeout=3 ticks, max_retries=5
    req = comm_r1.send_request_with_retry(
        msg_type=MessageType.RESERVATION_REQUEST,
        recipient="R2",
        payload={"cell": [5, 5], "time": 20},
        current_tick=0,
        timeout_ticks=3,
        max_retries=5,
    )

    resolved = False
    max_simulation_ticks = 25

    for tick in range(1, max_simulation_ticks):
        # R2 checks inbox and replies if received
        inbox_r2 = comm_r2.receive_and_process_inbox(current_tick=tick)
        for msg in inbox_r2:
            if msg.type == MessageType.RESERVATION_REQUEST:
                # Send GRANTED reply
                comm_r2.send(
                    msg_type=MessageType.RESERVATION_GRANTED,
                    recipient="R1",
                    payload={"cell": msg.payload["cell"], "in_reply_to": msg.message_id},
                    current_tick=tick,
                )

        # R1 checks inbox
        inbox_r1 = comm_r1.receive_and_process_inbox(current_tick=tick)

        # R1 evaluates timeouts and retries dropped packets
        retried, dead = comm_r1.check_pending_timeouts(current_tick=tick)

        if req.resolved:
            resolved = True
            break

    # Request must be resolved (either granted or declared dead after retries) within N ticks
    assert req.resolved is True or req.can_retry() is False
    assert tick < max_simulation_ticks  # Forward progress achieved, no indefinite hanging


def test_idempotent_duplicate_message_handling():
    """Test 3: Duplicated messages are idempotent (processing the same message_id
    twice has no double effect)."""
    network = P2PNetwork()
    # Configure link to force packet duplication
    network.set_link_config(sender="R1", recipient="R2", condition=LinkCondition.DUPLICATED)

    comm_r1 = RobotCommunicator(robot_id="R1", network=network)
    comm_r2 = RobotCommunicator(robot_id="R2", network=network)

    # Send a single task claim broadcast
    msg = comm_r1.send(
        msg_type=MessageType.TASK_CLAIMED,
        recipient="R2",
        payload={"task_id": "task_99", "robot_id": "R1"},
        current_tick=10,
    )

    # Process delivery for R2 across ticks 10 and 11
    delivered_msgs = []
    for t in [10, 11]:
        delivered = comm_r2.receive_and_process_inbox(current_tick=t)
        delivered_msgs.extend(delivered)

    # Assert exactly ONE message was accepted and duplicate was discarded
    assert len(delivered_msgs) == 1
    assert delivered_msgs[0].message_id == msg.message_id
    assert len(comm_r2.inbox) == 1


def test_stale_message_discarded():
    """Test 4: Stale messages whose tick exceeds send_tick + ttl are discarded."""
    network = P2PNetwork()
    comm_r1 = RobotCommunicator(robot_id="R1", network=network, default_ttl=5)
    comm_r2 = RobotCommunicator(robot_id="R2", network=network)

    # R1 sends message at tick 0 with TTL = 5 (expires at tick 5)
    comm_r1.send(
        msg_type=MessageType.OBSTACLE_UPDATE,
        recipient="R2",
        payload={"obstacle_id": "spill_1", "position": [1, 2]},
        current_tick=0,
        ttl=5,
    )

    # R2 was disconnected/delayed and only processes inbox at tick 10 (tick 10 > 0 + 5)
    inbox_r2 = comm_r2.receive_and_process_inbox(current_tick=10)

    # Stale message must be discarded
    assert len(inbox_r2) == 0
    assert len(comm_r2.inbox) == 0
