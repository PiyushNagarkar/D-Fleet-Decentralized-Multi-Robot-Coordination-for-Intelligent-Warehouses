/**
 * useSimulationMetrics: Live KPI scorecard and metrics timeseries buffer
 */

import { useState, useEffect } from "react";
import { SimulationMetrics } from "../types";

export interface MetricTimeSeriesPoint {
  tick: number;
  throughput: number;
  waitingTime: number;
  conflicts: number;
  deadlocks: number;
  batteryAvg: number;
}

export function useSimulationMetrics(metrics: SimulationMetrics, currentTick: number) {
  const [history, setHistory] = useState<MetricTimeSeriesPoint[]>([]);

  useEffect(() => {
    if (currentTick === 0) {
      setHistory([]);
      return;
    }

    // Append history every 2 ticks
    if (currentTick % 2 === 0) {
      setHistory((prev) => {
        const point: MetricTimeSeriesPoint = {
          tick: currentTick,
          throughput: metrics.throughput_tasks_per_hour,
          waitingTime: metrics.average_waiting_time_ticks,
          conflicts: metrics.conflicts_detected,
          deadlocks: metrics.deadlocks_detected,
          batteryAvg: metrics.average_battery_consumed,
        };
        const next = [...prev, point];
        // Retain last 60 points
        return next.slice(-60);
      });
    }
  }, [currentTick, metrics]);

  return {
    metrics,
    history,
  };
}
