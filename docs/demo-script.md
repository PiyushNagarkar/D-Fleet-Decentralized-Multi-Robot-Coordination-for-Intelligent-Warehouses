# D-Fleet Demonstration Script

This script walks through demonstrating D-Fleet's autonomous decentralized coordination features for live audience presentations.

## 1. Quick Start (Web Dashboard)

1. Start the backend simulation server:
   ```powershell
   cd backend
   .venv\Scripts\uvicorn app.main:app --reload --port 8000
   ```
2. Start the frontend 3D dashboard:
   ```powershell
   cd frontend
   npm run dev
   ```
3. Open browser at `http://localhost:5173`.

---

## 2. Key Demonstration Scenarios

### Flagship Scenario: `complete_demo.json`
- **What it showcases**: 4 robots, 12 tasks, moving forklift traffic, temporary spills, communication delay, and scheduled carrying robot failure.
- **Visual proof of decentralization**:
  1. Observe the **Communication Graph**: 3D transient beams and tags (`R1 → ROBOT_STATE → R2`) show messages passing between peer robots.
  2. Observe **Auction Bidding**: Tasks transition from `BIDDING` to `CLAIMED` via local cost evaluation without a central allocator.
  3. Observe **Spacetime Reservations & Dynamic Detours**: Notice robots rerouting around moving forklifts using D* Lite.
  4. Observe **Failure & Rescue Dispatch**: When R2 suffers a simulated hardware fault at tick 18 while carrying a pod, peer robots detect the heartbeat timeout and generate a `RESCUE_REQUIRED` task.

---

## 3. Headless CLI Demonstration

Run the headless simulation runner to inspect the terminal event stream:
```powershell
python scripts/run_simulation.py --scenario complete_demo.json --ticks 50 --verbose
```

Run the comparative benchmark against the Stop-and-Go baseline:
```powershell
python scripts/benchmark.py --scenario normal.json --ticks 40
```
