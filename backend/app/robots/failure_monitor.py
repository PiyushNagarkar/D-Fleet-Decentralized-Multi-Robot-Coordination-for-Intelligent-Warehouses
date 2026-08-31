"""Peer-Based Failure Detection and Decentralized Rescue Subsystem."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any

from app.robots.state import RobotState, RobotStatus
from app.robots.local_world_model import LocalWorldModel
from app.tasks.task import Task, TaskStatus
from app.tasks.task_manager import LocalTaskManager


@dataclass
class PeerHeartbeatInfo:
    robot_id: str
    last_seen_tick: int
    position: Tuple[int, int]
    status: str
    battery: float
    carrying_item: Optional[str] = None
    task_id: Optional[str] = None


@dataclass
class FailureEvent:
    failed_robot_id: str
    failure_tick: int
    last_known_position: Tuple[int, int]
    released_task_id: Optional[str] = None
    rescue_task_created: Optional[Task] = None
    invalidated_reservations_count: int = 0


class PeerFailureMonitor:
    """Monitors peer robot heartbeats and executes failure recovery without a central watchdog."""

    def __init__(
        self,
        my_robot_id: str,
        heartbeat_timeout_ticks: int = 5,
    ):
        self.my_robot_id = my_robot_id
        self.heartbeat_timeout_ticks = heartbeat_timeout_ticks
        self.peer_heartbeats: Dict[str, PeerHeartbeatInfo] = {}
        self.failed_peers: Set[str] = set()

    def record_peer_heartbeat(
        self,
        peer_id: str,
        current_tick: int,
        position: Tuple[int, int],
        status: str = "IDLE",
        battery: float = 100.0,
        carrying_item: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> None:
        """Record an incoming peer HEARTBEAT envelope."""
        if peer_id == self.my_robot_id:
            return

        self.peer_heartbeats[peer_id] = PeerHeartbeatInfo(
            robot_id=peer_id,
            last_seen_tick=current_tick,
            position=position,
            status=status,
            battery=battery,
            carrying_item=carrying_item,
            task_id=task_id,
        )

        # If peer was previously marked failed and is now alive
        if peer_id in self.failed_peers:
            self.failed_peers.remove(peer_id)

    def check_for_failed_peers(
        self,
        current_tick: int,
        world_model: LocalWorldModel,
        task_manager: Optional[LocalTaskManager] = None,
    ) -> List[FailureEvent]:
        """Detect timed-out peer heartbeats and execute decentralized failure recovery.

        1. Invalidate all space-time reservations owned by failed peer.
        2. Uncollected tasks: release for re-bidding.
        3. Carried pods: generate a RESCUE_REQUIRED task at failed peer's last location.
        """
        failure_events: List[FailureEvent] = []

        for peer_id, info in list(self.peer_heartbeats.items()):
            if peer_id in self.failed_peers:
                continue  # Already processed

            # Check timeout threshold
            if current_tick - info.last_seen_tick > self.heartbeat_timeout_ticks:
                self.failed_peers.add(peer_id)
                world_model.failed_robots.add(peer_id)
                from app.robots.local_world_model import KnownObstacle
                world_model.dynamic_obstacles[f"failed_{peer_id}"] = KnownObstacle(
                    obstacle_id=f"failed_{peer_id}",
                    position=info.position,
                    obstacle_type="STATIC",
                    first_observed_tick=current_tick,
                    last_observed_tick=current_tick,
                )

                # 1. Immediately invalidate all reservations owned by failed peer
                invalidated_count = 0
                to_delete = [
                    k for k, owner in list(world_model.reservations.items())
                    if owner == peer_id
                ]
                for k in to_delete:
                    del world_model.reservations[k]
                    invalidated_count += 1

                # 2. Task recovery handling
                released_task_id = None
                rescue_task = None

                if info.task_id and task_manager:
                    original_task = task_manager.known_tasks.get(info.task_id)

                    if info.carrying_item:
                        # Robot was carrying an item when it failed -> RESCUE_REQUIRED
                        rescue_task_id = f"rescue_{info.task_id}_{peer_id}"
                        delivery_loc = (
                            original_task.delivery_location
                            if original_task
                            else info.position
                        )
                        priority = (
                            original_task.priority + 1
                            if original_task
                            else 3
                        )

                        rescue_task = task_manager.on_task_announced(
                            task_id=rescue_task_id,
                            pickup_location=info.position,  # Pickup at failed robot's position
                            delivery_location=delivery_loc,
                            priority=priority,
                            spawn_tick=current_tick,
                            item_type=info.carrying_item,
                            metadata={
                                "is_rescue": True,
                                "failed_robot_id": peer_id,
                                "original_task_id": info.task_id,
                            },
                        )
                        rescue_task.status = TaskStatus.RESCUE_REQUIRED
                        if original_task:
                            original_task.status = TaskStatus.RESCUE_REQUIRED
                    else:
                        # Robot was en route to pickup -> Release task back to bidding pool
                        if original_task:
                            original_task.status = TaskStatus.RELEASED
                            original_task.assigned_robot_id = None
                            released_task_id = original_task.task_id
                            # Re-announce task for bidding
                            original_task.status = TaskStatus.BIDDING

                event = FailureEvent(
                    failed_robot_id=peer_id,
                    failure_tick=current_tick,
                    last_known_position=info.position,
                    released_task_id=released_task_id,
                    rescue_task_created=rescue_task,
                    invalidated_reservations_count=invalidated_count,
                )
                failure_events.append(event)

        return failure_events
