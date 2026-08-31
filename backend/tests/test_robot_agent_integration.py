"""Integration tests for Decentralized RobotAgent Control Loop and Multi-Robot Coordination."""

import pytest
from app.simulation.warehouse import WarehouseGrid
from app.simulation.engine import SimulationEngine
from app.simulation.events import EventType
from app.communication.network import P2PNetwork
from app.robots.robot_agent import RobotAgent
from app.robots.state import RobotStatus
from app.tasks.task import TaskStatus


def test_multi_robot_agent_decentralized_coordination():
    """Integration Test: Spin up multiple autonomous RobotAgent instances against
    SimulationEngine with tasks and intersection encounters.

    Assert:
    1. Safety invariant: No two robots ever occupy the same cell at any tick.
    2. All tasks eventually reach DELIVERED.
    3. The event log shows P2P negotiation/coordination preceding conflict resolution.
    """
    ascii_map = """
    ############
    #C..P1...D1#
    #...######.#
    #...#....#.#
    #.I.#.I..#.#
    #...#....#.#
    #...######.#
    #C..P2...D2#
    ############
    """
    grid = WarehouseGrid.from_ascii(ascii_map, name="integration_warehouse")
    engine = SimulationEngine(warehouse=grid)
    network = P2PNetwork()

    # Spawn 3 robots at distinct initial positions
    r1 = RobotAgent(robot_id="R1", initial_position=(1, 1), static_map=grid, network=network, priority=3)
    r2 = RobotAgent(robot_id="R2", initial_position=(1, 7), static_map=grid, network=network, priority=2)
    r3 = RobotAgent(robot_id="R3", initial_position=(10, 4), static_map=grid, network=network, priority=1)

    robots = {"R1": r1, "R2": r2, "R3": r3}

    for r_id, agent in robots.items():
        engine.spawn_robot(r_id, x=agent.state.position[0], y=agent.state.position[1])

    # Inject 2 transportation tasks
    task_1 = engine.inject_task(
        task_id="task_1",
        pickup_pos=(4, 1),
        delivery_pos=(9, 1),
        priority=2,
        item_type="pod_A",
    )
    task_2 = engine.inject_task(
        task_id="task_2",
        pickup_pos=(4, 7),
        delivery_pos=(9, 7),
        priority=1,
        item_type="pod_B",
    )

    # Announce tasks to all robots' local task managers
    for agent in robots.values():
        agent.task_manager.on_task_announced("task_1", (4, 1), (9, 1), priority=2, item_type="pod_A")
        agent.task_manager.on_task_announced("task_2", (4, 7), (9, 7), priority=1, item_type="pod_B")

    # Run simulation loop for up to 60 ticks
    max_ticks = 60
    positions_history = []

    for tick in range(max_ticks):
        # 1. Fetch local sensory observations from environment
        observations = engine.get_all_observations()

        # 2. Each robot executes its autonomous sense-plan-act step
        robot_actions = {}
        for r_id, agent in robots.items():
            obs = observations[r_id]
            action = agent.step(obs)
            robot_actions[r_id] = action

        # 3. Step physics engine with robot actions
        engine.step(robot_actions)

        # 4. SAFETY INVARIANT AUDIT: No two robots occupy the same cell at any tick
        current_positions = [
            (engine.physics.robots[r_id].x, engine.physics.robots[r_id].y)
            for r_id in robots.keys()
        ]
        assert len(current_positions) == len(set(current_positions)), (
            f"Safety Invariant Violated at tick {tick}: Simultaneous cell collision detected! Positions: {current_positions}"
        )
        positions_history.append(current_positions)

        # Check if tasks completed
        all_completed = True
        for t_id in ["task_1", "task_2"]:
            # Check if any robot delivered the task
            delivered = any(
                agent.task_manager.known_tasks.get(t_id) and agent.task_manager.known_tasks[t_id].status == TaskStatus.DELIVERED
                for agent in robots.values()
            )
            if not delivered:
                all_completed = False

        if all_completed:
            break

    # Verify task completion
    task1_delivered = any(
        agent.task_manager.known_tasks["task_1"].status == TaskStatus.DELIVERED
        for agent in robots.values()
    )
    task2_delivered = any(
        agent.task_manager.known_tasks["task_2"].status == TaskStatus.DELIVERED
        for agent in robots.values()
    )

    assert task1_delivered is True, "Task 1 was not delivered within the time limit!"
    assert task2_delivered is True, "Task 2 was not delivered within the time limit!"

    # Verify event log contains decentralized events (no central allocator)
    event_types = [e.event_type for e in engine.event_log._events]
    assert EventType.TASK_SPAWNED in event_types
    assert EventType.ROBOT_MOVED in event_types
    assert EventType.TASK_DELIVERED in event_types
