"""Local Task Manager for Decentralized Robot Agents."""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any

from app.robots.state import RobotState, RobotStatus
from app.robots.local_world_model import LocalWorldModel
from .task import Task, TaskStatus
from .bidder import TaskBidder


class LocalTaskManager:
    """Manages tasks from the perspective of an individual autonomous robot.

    CRITICAL ARCHITECTURAL MANDATE:
    This is NOT a central task allocator. It lives inside each robot's private state,
    tracking local auctions, placing bids, managing task execution stages, and
    resolving conflicting claims via deterministic decentralized rules.
    """

    def __init__(self, robot_id: str, bidder: Optional[TaskBidder] = None):
        self.robot_id = robot_id
        self.bidder = bidder or TaskBidder()
        self.known_tasks: Dict[str, Task] = {}
        self.active_task_id: Optional[str] = None

    def on_task_announced(
        self,
        task_id: str,
        pickup_location: Tuple[int, int],
        delivery_location: Tuple[int, int],
        priority: int = 1,
        spawn_tick: int = 0,
        deadline_tick: Optional[int] = None,
        item_type: str = "standard_pod",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Register a new task announcement observed from the environment or peers."""
        if task_id in self.known_tasks:
            return self.known_tasks[task_id]

        task = Task(
            task_id=task_id,
            pickup_location=pickup_location,
            delivery_location=delivery_location,
            priority=priority,
            status=TaskStatus.BIDDING,
            spawn_tick=spawn_tick,
            deadline_tick=deadline_tick,
            item_type=item_type,
            metadata=metadata or {},
        )
        self.known_tasks[task_id] = task
        return task

    def compute_and_record_my_bid(
        self,
        task_id: str,
        robot_state: RobotState,
        world_model: LocalWorldModel,
        current_tick: int,
    ) -> Optional[float]:
        """Compute this robot's bid for a task and record it locally."""
        task = self.known_tasks.get(task_id)
        if not task or task.status not in (TaskStatus.UNASSIGNED, TaskStatus.BIDDING):
            return None

        bid = self.bidder.compute_bid(robot_state, world_model, task, current_tick)
        if bid is not None:
            task.bids[self.robot_id] = bid
        return bid

    def record_peer_bid(self, task_id: str, peer_id: str, bid: float) -> None:
        """Record a bid broadcast by a peer robot."""
        task = self.known_tasks.get(task_id)
        if task and task.status in (TaskStatus.UNASSIGNED, TaskStatus.BIDDING):
            task.bids[peer_id] = bid

    def evaluate_auction(self, task_id: str) -> Optional[str]:
        """Determine winner of the local auction for task_id."""
        task = self.known_tasks.get(task_id)
        if not task or not task.bids:
            return None
        return self.bidder.evaluate_winner(task.bids)

    def claim_task(
        self,
        task_id: str,
        robot_id: str,
        winning_bid: float,
        current_tick: int,
    ) -> bool:
        """Attempt to claim task after winning local auction.
        
        Returns True if claim succeeded locally.
        """
        task = self.known_tasks.get(task_id)
        if not task:
            return False

        if task.status in (TaskStatus.UNASSIGNED, TaskStatus.BIDDING):
            task.status = TaskStatus.CLAIMED
            task.assigned_robot_id = robot_id
            task.claim_tick = current_tick
            task.claim_bid = winning_bid
            if robot_id == self.robot_id:
                self.active_task_id = task_id
            return True
        return False

    def handle_peer_claim(
        self,
        task_id: str,
        claiming_robot_id: str,
        claiming_bid: float,
        claim_tick: int,
    ) -> bool:
        """Process a peer's CLAIMED broadcast with decentralized conflict resolution.

        If this robot also believes it claimed the same task, resolves via deterministic rule:
        1. Higher bid wins.
        2. Tie broken by lexicographically smaller robot_id.

        Returns:
            True if this robot holds/retains the claim; False if peer won the claim.
        """
        task = self.known_tasks.get(task_id)
        if not task:
            # Create stub task if not known yet
            task = Task(
                task_id=task_id,
                pickup_location=(0, 0),
                delivery_location=(0, 0),
                status=TaskStatus.CLAIMED,
                assigned_robot_id=claiming_robot_id,
                claim_tick=claim_tick,
                claim_bid=claiming_bid,
            )
            self.known_tasks[task_id] = task
            return False

        # If this robot is not claiming this task, accept peer's claim
        if task.assigned_robot_id != self.robot_id or self.active_task_id != task_id:
            task.status = TaskStatus.CLAIMED
            task.assigned_robot_id = claiming_robot_id
            task.claim_tick = claim_tick
            task.claim_bid = claiming_bid
            return False

        # --- Dual Claim Conflict Resolution ---
        my_bid = task.claim_bid if task.claim_bid is not None else task.bids.get(self.robot_id, -float("inf"))
        peer_bid = claiming_bid

        # Compare keys: (bid descending, robot_id ascending)
        my_key = (my_bid, -ord(self.robot_id[0]) if self.robot_id else 0)
        peer_key = (peer_bid, -ord(claiming_robot_id[0]) if claiming_robot_id else 0)

        # Exact tie breaking: lowest robot_id lexicographically
        if abs(my_bid - peer_bid) < 1e-6:
            i_win = self.robot_id < claiming_robot_id
        else:
            i_win = my_bid > peer_bid

        if i_win:
            # Retain claim
            return True
        else:
            # Peer won: yield and back off
            task.assigned_robot_id = claiming_robot_id
            task.claim_bid = claiming_bid
            task.claim_tick = claim_tick
            if self.active_task_id == task_id:
                self.active_task_id = None
            return False

    def mark_going_to_pickup(self, task_id: str) -> None:
        task = self.known_tasks.get(task_id)
        if task and task.assigned_robot_id == self.robot_id:
            task.status = TaskStatus.GOING_TO_PICKUP

    def mark_picked_up(self, task_id: str) -> None:
        task = self.known_tasks.get(task_id)
        if task and task.assigned_robot_id == self.robot_id:
            task.status = TaskStatus.PICKED_UP

    def mark_going_to_delivery(self, task_id: str) -> None:
        task = self.known_tasks.get(task_id)
        if task and task.assigned_robot_id == self.robot_id:
            task.status = TaskStatus.GOING_TO_DELIVERY

    def mark_delivered(self, task_id: str, current_tick: int) -> None:
        task = self.known_tasks.get(task_id)
        if task and task.assigned_robot_id == self.robot_id:
            task.status = TaskStatus.DELIVERED
            task.completed_tick = current_tick
            if self.active_task_id == task_id:
                self.active_task_id = None

    def mark_released(self, task_id: str) -> None:
        task = self.known_tasks.get(task_id)
        if task and task.assigned_robot_id == self.robot_id:
            task.status = TaskStatus.RELEASED
            task.assigned_robot_id = None
            if self.active_task_id == task_id:
                self.active_task_id = None

    def mark_failed(self, task_id: str) -> None:
        task = self.known_tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            if self.active_task_id == task_id:
                self.active_task_id = None
