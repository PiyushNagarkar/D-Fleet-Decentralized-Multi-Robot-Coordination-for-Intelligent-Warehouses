"""Autonomous Decentralized Robot Agent.

Executes an independent sense-plan-act loop with zero centralized control.

CRITICAL ARCHITECTURAL MANDATE:
- All decisions are computed locally within this agent instance.
- No shared global state is accessed.
- All coordination is performed strictly via peer-to-peer messaging and local models.
"""

from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, Any

from app.simulation.physics import ActionType, Direction
from app.simulation.observations import RobotLocalObservation
from app.simulation.warehouse import WarehouseGrid, CellType
from .state import RobotState, RobotStatus
from .local_world_model import LocalWorldModel, KnownRobotInfo
from .message import Message, MessageType
from .communication import RobotCommunicator

if TYPE_CHECKING:
    from app.communication.network import P2PNetwork
from .conflict_detection import ConflictDetector, Conflict, ConflictType
from .negotiation import NegotiationEngine, NegotiationOutcome
from .deadlock_detection import WaitForGraph
from .battery_manager import BatteryManager, BatteryConfig
from .failure_monitor import PeerFailureMonitor
from .motion_controller import MotionController
from app.planning.dstar_lite import DStarLite
from app.planning.reservation_planner import SpaceTimeAStar, ReservationTable, ReservationRecord
from app.tasks.task import Task, TaskStatus
from app.tasks.bidder import TaskBidder
from app.tasks.task_manager import LocalTaskManager


class RobotAgent:
    """Autonomous multi-robot agent coordinating without central authority."""

    def __init__(
        self,
        robot_id: str,
        initial_position: Tuple[int, int],
        static_map: WarehouseGrid,
        network: P2PNetwork,
        priority: int = 1,
        battery: float = 100.0,
    ):
        self.robot_id = robot_id
        self.static_map = static_map
        self.network = network

        # 1. State & Local World Representation
        self.state = RobotState(
            robot_id=robot_id,
            position=initial_position,
            priority=priority,
            battery=battery,
            status=RobotStatus.IDLE,
        )
        self.world_model = LocalWorldModel(robot_id=robot_id, static_map=static_map)

        # 2. P2P Communication & Task Management
        self.communicator = RobotCommunicator(robot_id=robot_id, network=network)
        self.bidder = TaskBidder()
        self.task_manager = LocalTaskManager(robot_id=robot_id, bidder=self.bidder)

        # 3. Motion & Planning
        self.motion_controller = MotionController()
        self.planner = DStarLite.from_world_model(self.world_model)
        self.reservation_table = ReservationTable()
        self.st_planner = SpaceTimeAStar(warehouse=static_map)

        # 4. Conflict, Deadlock, Battery, Failure Subsystems
        self.conflict_detector = ConflictDetector()
        self.negotiator = NegotiationEngine(robot_id=robot_id)
        self.wfg = WaitForGraph()
        self.battery_manager = BatteryManager()
        self.failure_monitor = PeerFailureMonitor(my_robot_id=robot_id)

        # Internal target tracking
        self.current_goal: Optional[Tuple[int, int]] = None
        self.is_running: bool = True

    def step(self, observation: RobotLocalObservation) -> ActionType:
        """Single discrete-tick sense-plan-act step.

        Strictly decentralized pipeline:
        1. Observe -> Update local world model.
        2. Ingest peer messages -> Update tasks & reservations.
        3. Check peer failures -> Invalidate reservations & trigger rescue tasks.
        4. Battery evaluation -> Autonomous charging detour if depleted.
        5. Task system -> Autonomous bidding, auction evaluation, and self-claim.
        6. Path validation -> Incremental D* Lite replan on dynamic obstacles.
        7. Conflict detection -> P2P negotiation & deadlock breaking.
        8. Action execution -> Motion controller physical intent.
        9. State broadcast -> Emit heartbeat and space-time reservations.
        """
        if getattr(observation, "is_failed", False):
            if self.state.status != RobotStatus.FAILED:
                self.state.transition_to(RobotStatus.FAILED)
            return ActionType.WAIT

        if self.state.status == RobotStatus.FAILED:
            return ActionType.WAIT

        current_tick = observation.tick
        self.state.last_heartbeat = current_tick
        self.state.position = observation.grid_position
        self.state.battery = observation.battery_level
        self.state.carrying_item = observation.carried_item_id

        # 1. Observe: Integrate sensor readings into private local world model
        self.world_model.update_from_observation(observation)
        self.world_model.prune_stale_data(current_tick)

        # 2. Ingest peer messages
        inbound_messages = self.communicator.receive_and_process_inbox(current_tick)
        for msg in inbound_messages:
            self._handle_inbound_message(msg, current_tick)

        # 3. Check peer failures
        self.failure_monitor.check_for_failed_peers(
            current_tick=current_tick,
            world_model=self.world_model,
            task_manager=self.task_manager,
        )

        # 4. Battery Management
        if self.battery_manager.should_seek_charging(self.state.battery):
            if self.state.status == RobotStatus.CHARGING:
                if self.battery_manager.is_fully_charged(self.state.battery):
                    self.state.transition_to(RobotStatus.IDLE)
                    self.current_goal = None
                else:
                    self._broadcast_heartbeat(current_tick)
                    return ActionType.CHARGE
            elif self.state.status not in (RobotStatus.MOVING_TO_PICKUP, RobotStatus.MOVING_TO_DELIVERY):
                # Seek charger
                chargers = self.static_map.charging_stations
                nearest_charger = self.battery_manager.find_nearest_charger(self.state.position, chargers)
                if nearest_charger:
                    self.state.transition_to(RobotStatus.LOW_BATTERY)
                    self._plan_to_goal(nearest_charger, current_tick)
                    if self.state.position == nearest_charger:
                        self.state.transition_to(RobotStatus.CHARGING)
                        self._broadcast_heartbeat(current_tick)
                        return ActionType.CHARGE

        # 5. Task Management (Bidding & Execution)
        task_action = self._handle_task_lifecycle(current_tick)
        if task_action is not None:
            self._broadcast_heartbeat(current_tick)
            return task_action

        # If arrived at charging station during low battery
        if self.state.status == RobotStatus.LOW_BATTERY and self.state.position in self.static_map.charging_stations:
            self.state.transition_to(RobotStatus.CHARGING)
            self._broadcast_heartbeat(current_tick)
            return ActionType.CHARGE

        # 6. Path validation & replanning
        if self.current_goal and (not self.state.current_path or self.state.current_path[0] != self.current_goal):
            # Check if dynamic obstacle blocks path
            changed_cells = self.planner.sync_with_world_model(self.world_model, current_tick)
            if changed_cells and any(c in self.state.current_path for c in changed_cells):
                repaired = self.planner.replan(new_start=self.state.position)
                if len(repaired) > 1:
                    self.state.set_path(repaired[1:])

        # 7. Conflict Detection & P2P Negotiation
        action = ActionType.WAIT
        if self.state.current_path:
            next_waypoint = self.state.current_path[0]
            
            # Check potential conflict at next step
            conflicts = self.conflict_detector.detect_all_conflicts(
                robot_id=self.robot_id,
                path=[self.state.position, next_waypoint],
                start_tick=current_tick,
                world_model=self.world_model,
                current_tick=current_tick,
            )

            should_wait = False
            for conf in conflicts:
                # Add wait dependency
                self.wfg.add_dependency(self.robot_id, conf.robot_id_2, cell=conf.location, tick=conf.time_tick)
                
                # Check for deadlocks
                cycles = self.wfg.detect_cycles()
                if cycles:
                    # Break cycle
                    res = self.wfg.resolve_deadlock_cycle(
                        cycle=cycles[0],
                        robot_effective_priorities={
                            self.robot_id: self.negotiator.get_my_effective_priority(self.state)
                        },
                    )
                    if res.yielding_robot_id == self.robot_id:
                        self.negotiator.record_yield()
                        # Replan alternative route
                        self.state.clear_path()
                        if self.current_goal:
                            self._plan_to_goal(self.current_goal, current_tick)
                        should_wait = True
                        break

                # Lookup peer effective priority from known reservations
                peer_reservations = [
                    res for res in self.world_model.reservations.get(conf.location, [])
                    if res.owner == conf.robot_id_2
                ]
                peer_prio = peer_reservations[0].priority if peer_reservations else 10.0

                # Negotiate with peer
                outcome = self.negotiator.evaluate_reservation_contest(
                    my_state=self.state,
                    peer_id=conf.robot_id_2,
                    peer_effective_priority=peer_prio,
                )
                if outcome in (NegotiationOutcome.WAIT, NegotiationOutcome.YIELD):
                    should_wait = True
                    break
                elif outcome == NegotiationOutcome.REROUTE:
                    self.state.clear_path()
                    if self.current_goal:
                        self._plan_to_goal(self.current_goal, current_tick)
                    should_wait = True
                    break

            # Immediate physical perception check: if next_waypoint is occupied right now by another robot or obstacle
            known_peer_positions = {tuple(info.position) for p_id, info in self.world_model.known_robots.items() if p_id != self.robot_id}
            for p_id, info in self.world_model.known_robots.items():
                if p_id != self.robot_id and info.planned_path:
                    if tuple(info.planned_path[0]) == tuple(next_waypoint):
                        my_prio = self.negotiator.get_my_effective_priority(self.state)
                        peer_prio = float(info.priority * 10.0) if hasattr(info, "priority") else 10.0
                        if my_prio < peer_prio or (my_prio == peer_prio and self.robot_id > p_id):
                            should_wait = True
                    elif p_id < self.robot_id:
                        known_peer_positions.add(tuple(info.planned_path[0]))
            for nr in getattr(observation, "nearby_robots", []):
                if nr.robot_id != self.robot_id:
                    known_peer_positions.add(tuple(nr.grid_position))
                    if abs(nr.grid_position[0] - next_waypoint[0]) + abs(nr.grid_position[1] - next_waypoint[1]) <= 1:
                        if self.robot_id > nr.robot_id:
                            should_wait = True

            known_obs_positions = set()
            for obs_item in self.world_model.dynamic_obstacles.values():
                known_obs_positions.add(tuple(obs_item.position))
                if obs_item.waypoints:
                    for wp in obs_item.waypoints:
                        known_obs_positions.add(tuple(wp))
            for no in getattr(observation, "nearby_obstacles", []):
                known_obs_positions.add(tuple(no.grid_position))

            if tuple(next_waypoint) in known_peer_positions or tuple(next_waypoint) in known_obs_positions:
                should_wait = True

            if not should_wait:
                # Clear wait dependency
                self.wfg.remove_dependency(self.robot_id)
                action = self.motion_controller.get_action_for_move(self.state.position, next_waypoint)
                # Advance path
                self.state.advance_path()
                self.negotiator.waiting_time = 0
            else:
                waiting_ticks = self.negotiator.increment_waiting_tick()
                # Bounded Waiting: if blocked for >= 3 ticks, autonomously replan with D* Lite
                if waiting_ticks >= 3 and self.current_goal:
                    self.planner.sync_with_world_model(self.world_model, current_tick)
                    new_path = self.planner.plan(start=self.state.position, goal=self.current_goal)
                    if len(new_path) > 1:
                        self.state.set_path(new_path[1:])
                action = ActionType.WAIT

        # 8. State & Reservation Broadcast
        self._broadcast_heartbeat(current_tick)
        return action

    def _handle_inbound_message(self, msg: Message, current_tick: int) -> None:
        """Process incoming peer message envelope."""
        m_type = msg.type
        p = msg.payload

        if m_type == MessageType.TASK_ANNOUNCEMENT:
            self.task_manager.on_task_announced(
                task_id=p["task_id"],
                pickup_location=(p["pickup_location"][0], p["pickup_location"][1]),
                delivery_location=(p["delivery_location"][0], p["delivery_location"][1]),
                priority=p.get("priority", 1),
                spawn_tick=current_tick,
                deadline_tick=p.get("deadline_tick"),
                item_type=p.get("item_type", "standard_pod"),
            )

        elif m_type == MessageType.TASK_BID:
            self.task_manager.record_peer_bid(
                task_id=p["task_id"],
                peer_id=msg.sender,
                bid=p["bid"],
            )

        elif m_type == MessageType.TASK_CLAIMED:
            # Handle decentralized claim / conflict
            retained = self.task_manager.handle_peer_claim(
                task_id=p["task_id"],
                claiming_robot_id=p["robot_id"],
                claiming_bid=p.get("bid", 0.0),
                claim_tick=p.get("claim_tick", current_tick),
            )
            if not retained and self.state.task_id == p["task_id"]:
                # Yielded task: reset to IDLE and clear goal
                self.state.task_id = None
                self.state.transition_to(RobotStatus.IDLE)
                self.state.clear_path()
                self.current_goal = None

        elif m_type == MessageType.TASK_RELEASED:
            task_id = p.get("task_id")
            if task_id and task_id in self.task_manager.known_tasks:
                self.task_manager.known_tasks[task_id].status = TaskStatus.UNASSIGNED

        elif m_type == MessageType.HEARTBEAT:
            pos_raw = p.get("position")
            if pos_raw:
                pos = (pos_raw[0], pos_raw[1])
                self.failure_monitor.record_peer_heartbeat(
                    peer_id=msg.sender,
                    current_tick=current_tick,
                    position=pos,
                    status=p.get("status", "IDLE"),
                    battery=p.get("battery", 100.0),
                    carrying_item=p.get("carrying_item"),
                    task_id=p.get("task_id"),
                )
                planned = []
                for r in p.get("reservations", []):
                    if isinstance(r, dict):
                        if "cell" in r:
                            planned.append((r["cell"][0], r["cell"][1]))
                        elif "x" in r:
                            planned.append((r["x"], r["y"]))
                    elif isinstance(r, (list, tuple)) and len(r) >= 2:
                        planned.append((r[0], r[1]))

                self.world_model.known_robots[msg.sender] = KnownRobotInfo(
                    robot_id=msg.sender,
                    position=pos,
                    heading=p.get("heading", "NORTH"),
                    is_carrying_pod=bool(p.get("carrying_item")),
                    status=p.get("status", "IDLE"),
                    battery_level=p.get("battery", 100.0),
                    last_observed_tick=current_tick,
                    planned_path=planned,
                )
                # Ingest reservations
                for r in p.get("reservations", []):
                    if isinstance(r, dict):
                        self.world_model.reservations[((r["x"], r["y"]), r["tick"])] = msg.sender
                    elif isinstance(r, (list, tuple)) and len(r) >= 3:
                        self.world_model.reservations[((r[0], r[1]), r[2])] = msg.sender

    def _handle_task_lifecycle(self, current_tick: int) -> Optional[ActionType]:
        """Handle bidding, claiming, and moving through task milestones."""
        if self.state.status == RobotStatus.IDLE:
            # Bid on available tasks
            for task_id, task in list(self.task_manager.known_tasks.items()):
                if task.status in (TaskStatus.UNASSIGNED, TaskStatus.BIDDING, TaskStatus.RESCUE_REQUIRED):
                    my_bid = self.task_manager.compute_and_record_my_bid(
                        task_id=task_id,
                        robot_state=self.state,
                        world_model=self.world_model,
                        current_tick=current_tick,
                    )
                    if my_bid is not None:
                        # Broadcast bid to peers
                        self.communicator.broadcast(
                            msg_type=MessageType.TASK_BID,
                            payload={"task_id": task_id, "bid": my_bid},
                            current_tick=current_tick,
                        )

                    # Evaluate auction winner
                    winner = self.task_manager.evaluate_auction(task_id)
                    if winner == self.robot_id:
                        winning_bid = task.bids.get(self.robot_id, 0.0)
                        claimed = self.task_manager.claim_task(
                            task_id=task_id,
                            robot_id=self.robot_id,
                            winning_bid=winning_bid,
                            current_tick=current_tick,
                        )
                        if claimed:
                            self.state.task_id = task_id
                            self.state.transition_to(RobotStatus.MOVING_TO_PICKUP)
                            self._plan_to_goal(task.pickup_location, current_tick)
                            # Broadcast claim
                            self.communicator.broadcast(
                                msg_type=MessageType.TASK_CLAIMED,
                                payload={
                                    "task_id": task_id,
                                    "robot_id": self.robot_id,
                                    "bid": winning_bid,
                                    "claim_tick": current_tick,
                                },
                                current_tick=current_tick,
                            )
                            break

        elif self.state.status == RobotStatus.MOVING_TO_PICKUP:
            active_task = self.task_manager.known_tasks.get(self.state.task_id or "")
            if active_task:
                if self.state.position == active_task.pickup_location:
                    # Arrived at pickup
                    self.task_manager.mark_picked_up(active_task.task_id)
                    self.state.carrying_item = active_task.item_type
                    self.state.transition_to(RobotStatus.MOVING_TO_DELIVERY)
                    self._plan_to_goal(active_task.delivery_location, current_tick)
                    return ActionType.PICKUP

        elif self.state.status == RobotStatus.MOVING_TO_DELIVERY:
            active_task = self.task_manager.known_tasks.get(self.state.task_id or "")
            if active_task:
                if self.state.position == active_task.delivery_location:
                    # Arrived at delivery
                    self.task_manager.mark_delivered(active_task.task_id, current_tick)
                    self.state.carrying_item = None
                    self.state.task_id = None
                    self.state.transition_to(RobotStatus.IDLE)
                    self.current_goal = None
                    self.state.clear_path()
                    # Broadcast completion
                    self.communicator.broadcast(
                        msg_type=MessageType.TASK_RELEASED,
                        payload={"task_id": active_task.task_id, "status": "DELIVERED"},
                        current_tick=current_tick,
                    )
                    return ActionType.DROPOFF

        return None

    def _plan_to_goal(self, goal: Tuple[int, int], current_tick: int) -> None:
        """Plan path to goal using D* Lite."""
        self.current_goal = goal
        self.planner.sync_with_world_model(self.world_model, current_tick)
        path = self.planner.plan(start=self.state.position, goal=goal)
        if len(path) > 1:
            self.state.set_path(path[1:])
        elif len(path) == 1:
            self.state.set_path([])

    def _broadcast_heartbeat(self, current_tick: int) -> None:
        """Broadcast state and active reservations to peer robots."""
        reservations = []
        my_prio = self.negotiator.get_my_effective_priority(self.state)
        for i, pos in enumerate(self.state.current_path[:10]):
            reservations.append({"x": pos[0], "y": pos[1], "tick": current_tick + 1 + i, "priority": my_prio})

        self.communicator.broadcast(
            msg_type=MessageType.HEARTBEAT,
            payload={
                "robot_id": self.robot_id,
                "position": [self.state.position[0], self.state.position[1]],
                "battery": round(self.state.battery, 2),
                "status": self.state.status.value,
                "carrying_item": self.state.carrying_item,
                "task_id": self.state.task_id,
                "priority": my_prio,
                "reservations": reservations,
            },
            current_tick=current_tick,
        )
