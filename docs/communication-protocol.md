# Peer-to-Peer Communication Protocol

## 1. Message Envelope Architecture

All inter-robot communication in D-Fleet is exchanged using standardized P2P message envelopes:

```json
{
  "message_id": "msg_R1_14_1788042548905",
  "type": "RESERVATION_REQUEST",
  "sender": "R1",
  "recipient": "R2",
  "sequence": 14,
  "timestamp": 1788042548.905,
  "send_tick": 42,
  "ttl": 20,
  "payload": {
    "robot_id": "R1",
    "reservations": [{"x": 5, "y": 4, "tick": 44, "priority": 78.5}]
  }
}
```

---

## 2. Message Types & Semantics

| Message Type | Scope | Description |
| :--- | :--- | :--- |
| `ROBOT_STATE` | Broadcast | Periodic broadcast of robot position, status, and battery. |
| `HEARTBEAT` | Broadcast | Live heartbeat containing current reservations and priority. |
| `TASK_ANNOUNCEMENT` | Broadcast | Announcing a new task spawned in the environment. |
| `TASK_BID` | Broadcast | Independent auction bid submission $(-cost + urgency)$. |
| `TASK_CLAIMED` | Broadcast | Announcing winning claim of an auctioned task. |
| `TASK_RELEASED` | Broadcast | Announcing completion or release of a task. |
| `RESERVATION_REQUEST` | Direct / Broadcast | Requesting reservation of a space-time coordinate $(x, y, t)$. |
| `RESERVATION_GRANTED` | Direct | Affirmative response to a reservation contest. |
| `RESERVATION_REJECTED` | Direct | Rejection of competing reservation request. |
| `YIELD_REQUEST` | Direct | Asking peer to yield or wait at a contested narrow aisle. |
| `YIELD_ACCEPTED` | Direct | Confirming yielding intention to peer. |
| `OBSTACLE_UPDATE` | Broadcast | Sharing newly perceived dynamic obstacle coordinates. |
| `PATH_INVALIDATED` | Broadcast | Warning peers that current path has been replanned. |
| `ROBOT_FAILURE` | Broadcast | Self or peer-detected hardware breakdown alert. |
| `DEADLOCK_ALERT` | Broadcast | Warning peers that a wait-for cycle has been detected. |

---

## 3. Network Link Conditions & Resilience

The simulated network layer (`P2PNetwork`) models realistic degraded communications per link $(R_i \leftrightarrow R_j)$:
- **Latency**: Configurable propagation delay in integer simulation ticks.
- **Packet Loss**: Stochastic packet dropping $(0.0 - 1.0)$.
- **Duplication & Jitter**: Multi-path packet arrival simulation.
- **Deduplication & Expiry**: `RobotCommunicator` tracks sequence numbers and TTL to discard duplicate or stale messages.
