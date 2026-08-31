# Decentralized Algorithms & Mathematical Formulations

## 1. Decentralized Task Bidding (`TaskBidder`)

When a `TASK_ANNOUNCEMENT` is received, each idle robot independently evaluates a cost and bid:

$$\text{cost} = d_{\text{pickup}} + d_{\text{delivery}} + \text{congestion} + \text{battery\_penalty} + \text{workload} + \text{reroute\_cost}$$

$$\text{bid} = -\text{cost} + \text{urgency}$$

Where:
- $\text{battery\_penalty} = \begin{cases} 50.0 & \text{if } \text{battery} < 30.0 \\ (100.0 - \text{battery}) \times 0.2 & \text{otherwise} \end{cases}$
- $\text{urgency} = \text{priority} \times 10.0$

### Winner Determination & Deterministic Tie-Breaking
Each robot logs peer bids in its `LocalTaskManager`. The winner is:
$$\text{winner} = \arg\max_{r} \text{bid}_r$$
Exact numerical ties are broken deterministically by lexicographically smallest `robot_id` (e.g. `R1 < R2`).

---

## 2. Dedicated Conflict Detectors (`ConflictDetector`)

D-Fleet implements 5 dedicated conflict detectors:

1. **Vertex Conflict**: Two robots plan to occupy the exact same cell $(x, y)$ at the same time step $t$.
2. **Edge Conflict**: Two robots swap adjacent cells across consecutive ticks: $p_1(t) = p_2(t+1)$ and $p_1(t+1) = p_2(t)$.
3. **Following Conflict**: A robot enters a single-lane aisle too closely behind another robot without safe headway.
4. **Future Conflict**: Two currently separate paths converge at a shared cell at a future time step.
5. **Narrow-Aisle Head-On Conflict**: Two robots traveling in opposite directions enter a single-lane aisle.

---

## 3. Dynamic Priority & Anti-Starvation Aging (`NegotiationEngine`)

When a conflict occurs, each robot locally computes its dynamic effective priority:

$$\text{effective\_priority} = \text{base\_priority} + f(\text{waiting\_time}) + \text{yield\_compensation} - \text{recent\_yield\_penalty}$$

$$\text{base\_priority} = w_1 \cdot \text{urgency} + w_2 \cdot \text{battery\_urgency} + w_3 \cdot \text{waiting\_time} + w_4 \cdot \text{progress} - w_5 \cdot \text{reroute\_cost}$$

- **Anti-Starvation Aging**: $f(\text{waiting\_time}) = \alpha \cdot \text{waiting\_time}$ ensures a robot that loses negotiations repeatedly rises in priority and cannot starve.
- **Decaying Penalty**: When a robot yields, it receives a temporary penalty that slowly decays per tick, preventing repetitive yielding cycles.

---

## 4. Deadlock Detection & Graph Cycle Breaking (`WaitForGraph`)

Each robot maintains a local directed wait-for graph $G = (V, E)$ using NetworkX:
- An edge $(R_i \to R_j)$ represents $R_i$ waiting on a cell reserved by $R_j$.
- **Cycle Detection**: Cycles $R_1 \to R_2 \to \dots \to R_k \to R_1$ are detected via Tarjan's algorithm / NetworkX `simple_cycles`.
- **Resolution**: The robot with the lowest effective priority in the cycle yields, clears its path, releases its space-time reservations, and replans an alternative route via D* Lite.
