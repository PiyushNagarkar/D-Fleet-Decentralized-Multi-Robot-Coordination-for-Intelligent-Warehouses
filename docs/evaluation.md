# Evaluation & Baseline Benchmark Methodology

## 1. Metrics Tracked

D-Fleet tracks 7 comprehensive categories of performance metrics in `MetricsCollector`:

1. **Task Completion**: Total completed tasks, completion time (total/avg/max), and throughput rate.
2. **Delays & Movement**: Waiting time (total/avg/max), total path lengths traveled, and average path lengths.
3. **Conflicts & Deadlocks**: Conflicts detected/resolved, physical collisions prevented, deadlocks detected/resolved, deadlock recovery times, and dynamic D* Lite replans.
4. **P2P Communication**: Messages sent, received, average latency, dropped packets, and stale message rejections.
5. **Failures & Resilience**: Hardware failure count, uncarried tasks rebidded, and rescue operations completed.
6. **Battery & Energy**: Battery consumed, average final battery level, and charging station visits.
7. **Utilization**: Robot operational utilization ratio (moving ticks vs total ticks).

---

## 2. Stop-and-Go Baseline Benchmark Coordinator

To objectively measure the advantages of decentralized coordination, D-Fleet includes an isolated `StopAndGoBaselineCoordinator` in `backend/app/metrics/comparison.py`.

### Baseline Mechanism
- When two or more robots are active in the warehouse, the Stop-and-Go coordinator permits only **ONE** robot to move while freezing all others.
- Both modes are executed against the exact same scenario layout, random seed, robot spawn positions, and task spawn sequence.

### Relative Improvement Formula
For metrics where **lower is better** (e.g. completion time, waiting time):
$$\text{improvement} = \frac{\text{baseline} - \text{dfleet}}{\text{baseline}} \times 100\%$$

For metrics where **higher is better** (e.g. throughput, utilization):
$$\text{improvement} = \frac{\text{dfleet} - \text{baseline}}{\text{baseline}} \times 100\%$$
