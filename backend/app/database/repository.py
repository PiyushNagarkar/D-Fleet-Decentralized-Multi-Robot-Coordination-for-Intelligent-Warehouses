"""Repository and helper utilities for database persistence."""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from .models import (
    SimulationRun,
    Robot,
    Task,
    TaskEvent,
    RobotEvent,
    Reservation,
    CommunicationMessage,
    Obstacle,
    Metric,
)


class SimulationRepository:
    """Provides structured persistence methods for simulation telemetry and records."""

    def __init__(self, db: Session):
        self.db = db

    def create_simulation_run(self, scenario_name: str) -> SimulationRun:
        run = SimulationRun(scenario_name=scenario_name, status="RUNNING")
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def update_simulation_status(
        self,
        run_id: int,
        status: str,
        total_ticks: int,
        metrics_summary: Optional[Dict[str, Any]] = None,
    ) -> Optional[SimulationRun]:
        run = self.db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
        if run:
            run.status = status
            run.total_ticks = total_ticks
            if metrics_summary is not None:
                run.metrics_summary = metrics_summary
            self.db.commit()
            self.db.refresh(run)
        return run

    def log_task_event(
        self,
        run_id: Optional[int],
        task_id: str,
        event_type: str,
        tick: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> TaskEvent:
        event = TaskEvent(
            simulation_run_id=run_id,
            task_id=task_id,
            event_type=event_type,
            tick=tick,
            details=details,
        )
        self.db.add(event)
        self.db.commit()
        return event

    def log_robot_event(
        self,
        run_id: Optional[int],
        robot_id: str,
        event_type: str,
        tick: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> RobotEvent:
        event = RobotEvent(
            simulation_run_id=run_id,
            robot_id=robot_id,
            event_type=event_type,
            tick=tick,
            details=details,
        )
        self.db.add(event)
        self.db.commit()
        return event

    def record_metrics(
        self,
        run_id: Optional[int],
        tick: int,
        throughput: float,
        avg_delivery_time: float,
        deadlock_count: int,
        active_robots: int,
        energy_consumed: float,
    ) -> Metric:
        metric = Metric(
            simulation_run_id=run_id,
            tick=tick,
            throughput=throughput,
            avg_delivery_time=avg_delivery_time,
            deadlock_count=deadlock_count,
            active_robots=active_robots,
            energy_consumed=energy_consumed,
        )
        self.db.add(metric)
        self.db.commit()
        return metric
