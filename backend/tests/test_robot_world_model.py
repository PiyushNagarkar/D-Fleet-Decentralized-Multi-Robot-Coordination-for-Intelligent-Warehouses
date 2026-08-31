"""Unit tests for RobotState, LocalWorldModel, and Decentralized Divergence."""

import pytest
from app.simulation.warehouse import WarehouseGrid
from app.simulation.engine import SimulationEngine
from app.simulation.physics import ActionType
from app.robots.state import RobotState, RobotStatus
from app.robots.local_world_model import LocalWorldModel
from app.robots.network import DelayedMessageChannel


def test_robot_state_lifecycle():
    state = RobotState(
        robot_id="robot_1",
        position=(1, 1),
        battery=95.0,
        status=RobotStatus.IDLE,
    )
    assert state.status == RobotStatus.IDLE
    assert state.position == (1, 1)
    assert state.next_position is None

    # Assign a multi-waypoint path
    path = [(1, 1), (2, 1), (3, 1), (3, 2)]
    state.set_path(path)
    assert state.path_version == 1
    assert state.next_position == (2, 1)
    assert len(state.current_path) == 4

    # Advance path
    pos1 = state.advance_path()
    assert pos1 == (1, 1)
    assert state.position == (1, 1)
    assert state.next_position == (2, 1)

    pos2 = state.advance_path()
    assert pos2 == (2, 1)
    assert state.position == (2, 1)
    assert state.next_position == (3, 1)

    state.transition_to(RobotStatus.MOVING_TO_PICKUP)
    assert state.status == RobotStatus.MOVING_TO_PICKUP


def test_decentralized_world_model_divergence():
    """Verify that two robots at the exact same simulation tick can legitimately
    hold divergent world models due to spatial occlusion and message latency."""
    ascii_map = """
    ##########
    #........#
    #........#
    #........#
    #........#
    #........#
    #........#
    #........#
    #........#
    ##########
    """
    grid = WarehouseGrid.from_ascii(ascii_map)
    engine = SimulationEngine(warehouse=grid, perception_radius=3)
    channel = DelayedMessageChannel(default_latency_ticks=3)

    # R1 is at (1, 1), R2 is far away at (8, 8)
    engine.spawn_robot("R1", x=1, y=1)
    engine.spawn_robot("R2", x=8, y=8)

    wm_r1 = LocalWorldModel(robot_id="R1", static_map=grid)
    wm_r2 = LocalWorldModel(robot_id="R2", static_map=grid)

    # Step simulation to tick 10
    for _ in range(10):
        engine.step()

    # Dynamic obstacle spawns at (2, 1) - directly adjacent to R1 (distance 1), far from R2 (distance 13)
    engine.add_obstacle(x=2, y=1, start_tick=10, obstacle_id="spill_at_aisle_1")

    # Step at tick 10: Observations generated
    obs, _ = engine.step()
    current_tick = engine.clock.current_tick  # 11

    # R1 updates from its local sensor cone
    wm_r1.update_from_observation(obs["R1"])
    # R2 updates from its local sensor cone
    wm_r2.update_from_observation(obs["R2"])

    # R1 saw the obstacle directly; R2 did not
    assert "spill_at_aisle_1" in wm_r1.dynamic_obstacles
    assert "spill_at_aisle_1" not in wm_r2.dynamic_obstacles
    assert wm_r1.is_cell_blocked(2, 1, current_tick) is True
    assert wm_r2.is_cell_blocked(2, 1, current_tick) is False

    # R1 sends a peer alert message to R2 with latency = 3 ticks
    channel.send(
        sender_id="R1",
        recipient_id="R2",
        message_type="OBSTACLE_ALERT",
        payload={"obstacle_id": "spill_at_aisle_1", "position": [2, 1]},
        current_tick=current_tick,
        latency_ticks=3,
    )

    # Ticks 12 and 13: Message is still in-flight
    for tick in [12, 13]:
        engine.step()
        obs_t = engine.get_all_observations()
        wm_r1.update_from_observation(obs_t["R1"])
        wm_r2.update_from_observation(obs_t["R2"])

        # Check for delivered messages for R2
        delivered = channel.deliver_for_robot("R2", tick)
        for msg in delivered:
            wm_r2.update_from_peer_message(msg, tick)

        # Snapshots MUST DIFFER during latency window
        assert "spill_at_aisle_1" in wm_r1.dynamic_obstacles
        assert "spill_at_aisle_1" not in wm_r2.dynamic_obstacles

    # Tick 14 (current_tick + 3): Message is delivered to R2
    engine.step()
    tick_14 = engine.clock.current_tick
    delivered_msgs = channel.deliver_for_robot("R2", tick_14)
    assert len(delivered_msgs) == 1
    assert delivered_msgs[0].message_type == "OBSTACLE_ALERT"

    for msg in delivered_msgs:
        wm_r2.update_from_peer_message(msg, tick_14)

    # Now both models know about the obstacle
    assert "spill_at_aisle_1" in wm_r1.dynamic_obstacles
    assert "spill_at_aisle_1" in wm_r2.dynamic_obstacles
    assert wm_r2.is_cell_blocked(2, 1, tick_14) is True


def test_packet_drop_simulation():
    """Verify that dropped messages do not update the recipient's local world model."""
    grid = WarehouseGrid(width=10, height=10)
    wm_r2 = LocalWorldModel(robot_id="R2", static_map=grid)
    channel = DelayedMessageChannel(drop_probability=1.0)  # 100% loss

    msg = channel.send(
        sender_id="R1",
        recipient_id="R2",
        message_type="OBSTACLE_ALERT",
        payload={"obstacle_id": "blocked_door", "position": [4, 4]},
        current_tick=5,
    )
    assert msg is None  # Packet was dropped

    delivered = channel.deliver_for_robot("R2", 10)
    assert len(delivered) == 0
    assert "blocked_door" not in wm_r2.dynamic_obstacles


def test_reservation_integration_and_pruning():
    grid = WarehouseGrid(width=10, height=10)
    wm = LocalWorldModel(robot_id="R1", static_map=grid)

    # Add space-time reservation for peer R2 at ((3, 3), tick=15)
    channel = DelayedMessageChannel()
    msg = channel.send(
        sender_id="R2",
        recipient_id="R1",
        message_type="RESERVATION_BROADCAST",
        payload={
            "robot_id": "R2",
            "reservations": [{"x": 3, "y": 3, "tick": 15}],
        },
        current_tick=10,
    )
    delivered = channel.deliver_for_robot("R1", 10)
    for m in delivered:
        wm.update_from_peer_message(m, current_tick=10)

    # Cell is blocked at tick 15, but open at tick 14
    assert wm.is_cell_blocked(3, 3, tick=15) is True
    assert wm.is_cell_blocked(3, 3, tick=14) is False

    # Prune stale reservations at tick 20
    wm.prune_stale_data(current_tick=20)
    assert wm.is_cell_blocked(3, 3, tick=15) is False
