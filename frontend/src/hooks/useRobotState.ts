/**
 * useRobotState: Reactive access and inspection state for multi-robot fleet
 */

import { useState, useMemo } from "react";
import { RobotTelemetry, RobotStatus } from "../types";

export function useRobotState(robots: RobotTelemetry[]) {
  const [selectedRobotId, setSelectedRobotId] = useState<string | null>(null);

  const selectedRobot = useMemo(() => {
    if (!selectedRobotId) return null;
    return robots.find((r) => r.id === selectedRobotId) || null;
  }, [robots, selectedRobotId]);

  const activeRobotsCount = useMemo(() => {
    return robots.filter(
      (r) => r.status !== RobotStatus.IDLE && r.status !== RobotStatus.FAILED && r.status !== RobotStatus.CHARGING
    ).length;
  }, [robots]);

  const chargingRobotsCount = useMemo(() => {
    return robots.filter((r) => r.status === RobotStatus.CHARGING).length;
  }, [robots]);

  const failedRobotsCount = useMemo(() => {
    return robots.filter((r) => r.status === RobotStatus.FAILED).length;
  }, [robots]);

  const averageBattery = useMemo(() => {
    if (!robots.length) return 0;
    const total = robots.reduce((sum, r) => sum + (r.battery || 0), 0);
    return Math.round(total / robots.length);
  }, [robots]);

  return {
    robots,
    selectedRobotId,
    selectedRobot,
    setSelectedRobotId,
    activeRobotsCount,
    chargingRobotsCount,
    failedRobotsCount,
    averageBattery,
  };
}
