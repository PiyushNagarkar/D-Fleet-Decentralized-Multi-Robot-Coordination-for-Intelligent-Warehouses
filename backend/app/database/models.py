"""SQLAlchemy ORM Models for D-Fleet Simulation Persistence."""

from __future__ import annotations
import datetime
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from .database import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scenario_name = Column(String(100), nullable=False)
    status = Column(String(50), default="CREATED")
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    total_ticks = Column(Integer, default=0)
    metrics_summary = Column(JSON, nullable=True)

    robots = relationship("Robot", back_populates="simulation_run", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="simulation_run", cascade="all, delete-orphan")
    task_events = relationship("TaskEvent", back_populates="simulation_run", cascade="all, delete-orphan")
    robot_events = relationship("RobotEvent", back_populates="simulation_run", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="simulation_run", cascade="all, delete-orphan")
    messages = relationship("CommunicationMessage", back_populates="simulation_run", cascade="all, delete-orphan")
    obstacles = relationship("Obstacle", back_populates="simulation_run", cascade="all, delete-orphan")
    metrics = relationship("Metric", back_populates="simulation_run", cascade="all, delete-orphan")


class Robot(Base):
    __tablename__ = "robots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    simulation_run_id = Column(Integer, ForeignKey("simulation_runs.id"), nullable=True)
    robot_id = Column(String(50), nullable=False, index=True)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    battery = Column(Float, default=100.0)
    status = Column(String(50), default="IDLE")
    carrying_pod = Column(String(50), nullable=True)
    task_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    simulation_run = relationship("SimulationRun", back_populates="robots")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    simulation_run_id = Column(Integer, ForeignKey("simulation_runs.id"), nullable=True)
    task_id = Column(String(50), nullable=False, index=True)
    pickup_x = Column(Integer, nullable=False)
    pickup_y = Column(Integer, nullable=False)
    delivery_x = Column(Integer, nullable=False)
    delivery_y = Column(Integer, nullable=False)
    priority = Column(Integer, default=1)
    status = Column(String(50), default="UNASSIGNED")
    assigned_robot_id = Column(String(50), nullable=True)
    spawn_tick = Column(Integer, default=0)
    delivered_tick = Column(Integer, nullable=True)

    simulation_run = relationship("SimulationRun", back_populates="tasks")


class TaskEvent(Base):
    __tablename__ = "task_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    simulation_run_id = Column(Integer, ForeignKey("simulation_runs.id"), nullable=True)
    task_id = Column(String(50), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    tick = Column(Integer, nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    simulation_run = relationship("SimulationRun", back_populates="task_events")


class RobotEvent(Base):
    __tablename__ = "robot_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    simulation_run_id = Column(Integer, ForeignKey("simulation_runs.id"), nullable=True)
    robot_id = Column(String(50), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    tick = Column(Integer, nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    simulation_run = relationship("SimulationRun", back_populates="robot_events")


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    simulation_run_id = Column(Integer, ForeignKey("simulation_runs.id"), nullable=True)
    robot_id = Column(String(50), nullable=False, index=True)
    cell_x = Column(Integer, nullable=False)
    cell_y = Column(Integer, nullable=False)
    time_tick = Column(Integer, nullable=False)
    created_tick = Column(Integer, default=0)
    ttl = Column(Integer, default=20)

    simulation_run = relationship("SimulationRun", back_populates="reservations")


class CommunicationMessage(Base):
    __tablename__ = "communication_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    simulation_run_id = Column(Integer, ForeignKey("simulation_runs.id"), nullable=True)
    message_id = Column(String(100), nullable=False, index=True)
    sender = Column(String(50), nullable=False)
    recipient = Column(String(50), nullable=False)
    message_type = Column(String(50), nullable=False)
    tick = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    simulation_run = relationship("SimulationRun", back_populates="messages")


class Obstacle(Base):
    __tablename__ = "obstacles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    simulation_run_id = Column(Integer, ForeignKey("simulation_runs.id"), nullable=True)
    obstacle_id = Column(String(50), nullable=False, index=True)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    start_tick = Column(Integer, default=0)
    duration = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    simulation_run = relationship("SimulationRun", back_populates="obstacles")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    simulation_run_id = Column(Integer, ForeignKey("simulation_runs.id"), nullable=True)
    tick = Column(Integer, nullable=False)
    throughput = Column(Float, default=0.0)
    avg_delivery_time = Column(Float, default=0.0)
    deadlock_count = Column(Integer, default=0)
    active_robots = Column(Integer, default=0)
    energy_consumed = Column(Float, default=0.0)

    simulation_run = relationship("SimulationRun", back_populates="metrics")
