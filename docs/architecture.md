# D-Fleet System Architecture

## 1. Architectural Philosophy: Strictly Decentralized

D-Fleet is designed from first principles with **NO centralized controller, NO centralized task allocator, and NO joint MAPF/CBS solver**.

```
                           Simulation Environment Layer
                       (Physics, Warehouse Grid, Events)
                                       |
                   Direct Sensor Readings & Observations
                                       |
                  ┌────────────────────┼────────────────────┐
                  ▼                    ▼                    ▼
          ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
          │ RobotAgent 1 │     │ RobotAgent 2 │     │ RobotAgent 3 │
          │ (Sense-Plan) │     │ (Sense-Plan) │     │ (Sense-Plan) │
          └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
                 ▲                    ▲                    ▲
                 └──────── P2P Mesh Communication ─────────┘
```

### Why FastAPI is NOT a Central Controller
FastAPI acts purely as an **observability gateway and physical environment interface**:
1. It streams read-only telemetry out to the dashboard via `/ws/simulation` (Safety Invariant #9).
2. It hosts REST endpoints for simulation controls (`/api/simulation/start`, `/api/simulation/pause`, `/api/simulation/reset`) and environment disturbance injections (`/api/obstacles`, `/api/failures/{id}`).
3. It **never** assigns tasks, computes paths, resolves robot conflicts, or commands individual robot wheel velocities.
4. If the FastAPI gateway is disconnected or closed, the multi-agent system continues executing headlessly via CLI.

---

## 2. Robot Agent Anatomy (`RobotAgent`)

Each robot instance is an independent autonomous agent that maintains its own private local state:

- **`RobotState`**: Current position, heading, battery level, status enum, active path waypoints, and priority.
- **`LocalWorldModel`**: Private representation of the warehouse built solely from direct observations and received peer messages.
- **`DStarLite`**: Incremental heuristic path repair algorithm.
- **`TaskBidder` & `LocalTaskManager`**: Autonomous cost calculation and market auction claiming.
- **`ConflictDetector`**: 5 dedicated geometric and space-time conflict detectors.
- **`NegotiationEngine`**: Dynamic effective priority evaluation and anti-starvation aging.
- **`WaitForGraph`**: Local NetworkX dependency graph for deadlock cycle detection.
- **`BatteryManager`**: Autonomous battery threshold monitoring and charging detour planning.
- **`PeerFailureMonitor`**: Heartbeat timeout tracking and rescue task generation.
- **`RobotCommunicator`**: Point-to-point and broadcast messaging over the simulated P2P mesh network.

---

## 3. Autonomous Control Loop

Every simulation tick, each `RobotAgent` executes the following sense-plan-act sequence:

```
1. Observe: Integrate direct sensor observations into LocalWorldModel.
2. Ingest: Process incoming peer messages from the P2P network inbox.
3. Health Check: Evaluate peer heartbeats for hardware failure detection.
4. Battery Check: If low battery, pause task bidding and route to nearest charger.
5. Task Lifecycle: Calculate bids for unassigned tasks or advance active milestones.
6. Path Validation: Sync dynamic obstacles with D* Lite and repair path if blocked.
7. Conflict Detection & Negotiation: Detect vertex/edge/narrow-aisle conflicts and negotiate.
8. Deadlock Recovery: Inspect WaitForGraph cycles and yield if lowest priority in cycle.
9. Physical Step: Request motion controller translation/rotation toward next waypoint.
10. State Broadcast: Broadcast heartbeat and space-time reservations to peer robots.
```
