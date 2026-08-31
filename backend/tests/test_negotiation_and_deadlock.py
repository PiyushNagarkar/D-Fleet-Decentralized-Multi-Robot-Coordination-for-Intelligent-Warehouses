"""Unit tests for Decentralized Negotiation, Priority Aging, and Deadlock Recovery."""

import pytest
from app.robots.state import RobotState, RobotStatus
from app.robots.negotiation import (
    NegotiationOutcome,
    NegotiationEngine,
    PriorityCalculator,
    PriorityWeights,
)
from app.robots.deadlock_detection import (
    WaitForGraph,
    DeadlockResolutionResult,
)


def test_two_robots_resolve_to_one_grant_and_one_yield():
    """Test 1: Two robots competing for the same cell/tick resolve to exactly
    one winning claim and one yielding/waiting outcome."""
    neg_r1 = NegotiationEngine(robot_id="R1")
    neg_r2 = NegotiationEngine(robot_id="R2")

    # R1 has higher base priority (priority=2 vs priority=1)
    state_r1 = RobotState(robot_id="R1", position=(2, 2), priority=2, battery=100.0)
    state_r2 = RobotState(robot_id="R2", position=(3, 2), priority=1, battery=100.0)

    p1 = neg_r1.get_my_effective_priority(state_r1)
    p2 = neg_r2.get_my_effective_priority(state_r2)

    # R1 evaluates against R2's priority
    outcome_r1 = neg_r1.evaluate_reservation_contest(
        my_state=state_r1,
        peer_id="R2",
        peer_effective_priority=p2,
    )

    # R2 evaluates against R1's priority
    outcome_r2 = neg_r2.evaluate_reservation_contest(
        my_state=state_r2,
        peer_id="R1",
        peer_effective_priority=p1,
    )

    # Exactly one robot retains/rejects peer (wins) and one yields/waits (loses)
    assert outcome_r1 == NegotiationOutcome.REJECT  # R1 wins, retains reservation
    assert outcome_r2 in (NegotiationOutcome.YIELD, NegotiationOutcome.WAIT, NegotiationOutcome.REROUTE)  # R2 yields


def test_anti_starvation_priority_aging():
    """Test 2: A robot that loses repeatedly has rising effective priority and
    eventually wins against a higher base-priority robot (no starvation over N rounds)."""
    neg_weak = NegotiationEngine(robot_id="R_Low")
    neg_strong = NegotiationEngine(robot_id="R_High")

    # R_High starts with higher priority=5 vs R_Low priority=1
    state_weak = RobotState(robot_id="R_Low", position=(1, 1), priority=1, battery=100.0)
    state_strong = RobotState(robot_id="R_High", position=(5, 5), priority=5, battery=100.0)

    # Initially R_High easily wins
    p_weak_init = neg_weak.get_my_effective_priority(state_weak)
    p_strong_init = neg_strong.get_my_effective_priority(state_strong)
    assert p_strong_init > p_weak_init

    # Simulate R_Low waiting across consecutive simulation ticks
    weak_won = False
    max_rounds = 40

    for tick in range(1, max_rounds + 1):
        neg_weak.increment_waiting_tick()
        p_weak = neg_weak.get_my_effective_priority(state_weak)
        p_strong = neg_strong.get_my_effective_priority(state_strong)

        # R_Low's effective priority should rise
        assert p_weak > p_weak_init

        outcome = neg_weak.evaluate_reservation_contest(
            my_state=state_weak,
            peer_id="R_High",
            peer_effective_priority=p_strong,
        )

        if outcome == NegotiationOutcome.REJECT:
            weak_won = True
            break

    # R_Low must eventually win due to priority aging
    assert weak_won is True, "Priority aging failed: Low priority robot starved indefinitely!"
    assert tick < max_rounds


def test_three_robot_wait_for_cycle_deadlock_breaking():
    """Test 3: Construct a 3-robot wait-for cycle (R1 -> R2 -> R3 -> R1) and confirm
    cycle detection and resolution breaks the deadlock in one recovery pass."""
    wfg = WaitForGraph()

    # Create cycle: R1 is waiting on R2, R2 is waiting on R3, R3 is waiting on R1
    wfg.add_dependency(waiter_id="R1", blocking_id="R2", cell=(2, 2), tick=10)
    wfg.add_dependency(waiter_id="R2", blocking_id="R3", cell=(3, 3), tick=10)
    wfg.add_dependency(waiter_id="R3", blocking_id="R1", cell=(4, 4), tick=10)

    # Verify cycle is detected
    cycles = wfg.detect_cycles()
    assert len(cycles) == 1
    cycle = cycles[0]
    assert set(cycle) == {"R1", "R2", "R3"}

    # Assign distinct priorities: R1=30.0, R2=20.0, R3=10.0 (R3 has lowest priority)
    effective_priorities = {
        "R1": 30.0,
        "R2": 20.0,
        "R3": 10.0,
    }
    contested_cells = {
        "R1": (2, 2),
        "R2": (3, 3),
        "R3": (4, 4),
    }

    # Resolve deadlock
    results = wfg.detect_and_resolve_all(
        robot_effective_priorities=effective_priorities,
        contested_cells=contested_cells,
    )

    assert len(results) == 1
    res = results[0]
    assert res.cycle_detected is True
    # Lowest priority robot R3 is selected to yield and reroute
    assert res.yielding_robot_id == "R3"
    assert res.yielding_priority == 10.0
    assert res.action_taken == "YIELD_AND_REROUTE"

    # Verify the cycle in the graph is now broken
    remaining_cycles = wfg.detect_cycles()
    assert len(remaining_cycles) == 0
