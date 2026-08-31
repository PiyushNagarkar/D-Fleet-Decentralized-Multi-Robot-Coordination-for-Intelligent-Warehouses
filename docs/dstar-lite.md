# D* Lite Incremental Path Planning

## 1. Algorithmic Overview

D* Lite (Koenig & Likhachev, 2002) is an incremental heuristic search algorithm that computes shortest paths on dynamic grids.

Unlike static $A^*$ which plans from scratch whenever an obstacle appears, D* Lite searches backwards from the goal to the current start position and maintains $g(s)$ and $rhs(s)$ values across search iterations. When edge costs change, D* Lite repairs only the affected vertices.

```
       Initial Search: Goal -> Start
       Obstacle detected at cell (x, y)
       Update edge costs c(u, v) = INF
       Key heuristic modifier k_m += h(s_last, s_current)
       Update vertices: rhs(u) = min_{s' in Succ(u)} (c(u, s') + g(s'))
       Priority Queue: keys = [min(g(s), rhs(s)) + h(s_start, s) + k_m, min(g(s), rhs(s))]
       Repair path in O(k) steps instead of O(|V| log |V|)
```

---

## 2. Key Maintenance & Consistency

Each vertex $s$ has two estimates of its distance to the goal:
- **$g(s)$**: The currently known path cost from $s$ to the goal.
- **$rhs(s)$**: The one-step lookahead value computed from successors:
  $$rhs(s) = \begin{cases} 0 & \text{if } s = s_{goal} \\ \min_{s' \in Succ(s)} (c(s, s') + g(s')) & \text{otherwise} \end{cases}$$

A vertex is:
- **Locally Consistent**: if $g(s) = rhs(s)$
- **Locally Overconsistent**: if $g(s) > rhs(s)$
- **Locally Underconsistent**: if $g(s) < rhs(s)$

When a dynamic obstacle blocks a cell, the edge costs $c(u, v)$ rise to $\infty$, making the affected nodes underconsistent. D* Lite pushes only affected nodes to the priority queue and recomputes until the current start vertex is consistent.

---

## 3. Dynamic Obstacle Synchronization

Every tick, `RobotAgent` synchronizes its private `LocalWorldModel` with its local `DStarLite` planner:

```python
# 1. Detect dynamic obstacles in sensory range
changed_cells = self.planner.sync_with_world_model(self.world_model, current_tick)

# 2. If any changed cell blocks the current active trajectory, trigger incremental replanning
if changed_cells and any(c in self.state.current_path for c in changed_cells):
    repaired_path = self.planner.replan(new_start=self.state.position)
    if len(repaired_path) > 1:
        self.state.set_path(repaired_path[1:])
```
