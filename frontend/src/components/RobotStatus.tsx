/**
 * RobotStatus: Fleet Overview and Individual Agent Telemetry Inspection
 */

import React from "react";
import {
  Bot,
  Battery,
  BatteryCharging,
  BatteryWarning,
  Package,
  Activity,
  MapPin,
  Route,
} from "lucide-react";
import { RobotTelemetry, RobotStatus as StatusEnum } from "../types";

interface RobotStatusProps {
  robots: RobotTelemetry[];
  selectedRobotId: string | null;
  onSelectRobot: (robotId: string) => void;
}

export const RobotStatus: React.FC<RobotStatusProps> = ({
  robots,
  selectedRobotId,
  onSelectRobot,
}) => {
  const getStatusBadge = (status: StatusEnum) => {
    switch (status) {
      case StatusEnum.IDLE:
        return "bg-slate-800 text-slate-300 border-slate-700";
      case StatusEnum.BIDDING:
        return "bg-purple-950/80 text-purple-300 border-purple-800";
      case StatusEnum.CLAIMED:
        return "bg-indigo-950/80 text-indigo-300 border-indigo-800";
      case StatusEnum.MOVING_TO_PICKUP:
      case StatusEnum.MOVING_TO_DELIVERY:
        return "bg-cyan-950/80 text-cyan-300 border-cyan-800 animate-pulse";
      case StatusEnum.PICKING_UP:
      case StatusEnum.DROPPING_OFF:
        return "bg-teal-950/80 text-teal-300 border-teal-800";
      case StatusEnum.CHARGING:
        return "bg-emerald-950/80 text-emerald-300 border-emerald-800";
      case StatusEnum.LOW_BATTERY:
        return "bg-amber-950/80 text-amber-300 border-amber-800";
      case StatusEnum.WAITING:
      case StatusEnum.YIELDING:
        return "bg-yellow-950/80 text-yellow-300 border-yellow-800";
      case StatusEnum.DEADLOCKED:
        return "bg-red-950/80 text-red-300 border-red-800 animate-bounce";
      case StatusEnum.FAILED:
        return "bg-rose-950/80 text-rose-300 border-rose-800";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const getBatteryIcon = (level: number, status: StatusEnum) => {
    if (status === StatusEnum.CHARGING) {
      return <BatteryCharging className="w-4 h-4 text-emerald-400 animate-pulse" />;
    }
    if (level < 25) {
      return <BatteryWarning className="w-4 h-4 text-rose-400" />;
    }
    return <Battery className="w-4 h-4 text-slate-400" />;
  };

  const getBatteryColor = (level: number) => {
    if (level > 60) return "bg-emerald-500";
    if (level > 25) return "bg-amber-500";
    return "bg-rose-500";
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
          <Bot className="w-4 h-4 text-cyan-400" />
          <span>Decentralized Robot Fleet</span>
          <span className="text-xs px-2 py-0.5 bg-slate-800 text-cyan-400 rounded-full font-mono">
            {robots.length}
          </span>
        </h2>
        <span className="text-[10px] text-slate-500 uppercase font-mono">
          Independent Agents
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pt-3 pr-1">
        {robots.map((robot) => {
          const isSelected = selectedRobotId === robot.id;
          return (
            <div
              key={robot.id}
              onClick={() => onSelectRobot(robot.id)}
              className={`p-3 rounded-lg border transition-all cursor-pointer ${
                isSelected
                  ? "bg-slate-800/90 border-cyan-500 ring-1 ring-cyan-500/50 shadow-md"
                  : "bg-slate-950/60 border-slate-800/80 hover:bg-slate-800/50 hover:border-slate-700"
              }`}
            >
              {/* Header: ID, Priority, Status */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold font-mono text-slate-100">
                    {robot.id}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 bg-slate-800 text-slate-400 rounded font-mono">
                    Prio: {robot.priority}
                  </span>
                </div>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${getStatusBadge(
                    robot.status
                  )}`}
                >
                  {robot.status}
                </span>
              </div>

              {/* Coordinates & Carried Item */}
              <div className="grid grid-cols-2 gap-2 text-xs mb-2 text-slate-300">
                <div className="flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-slate-500" />
                  <span className="font-mono text-slate-400">
                    ({robot.position[0]}, {robot.position[1]})
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Package className="w-3.5 h-3.5 text-amber-400" />
                  <span className="font-mono text-slate-300 truncate">
                    {robot.carrying_item || "Empty"}
                  </span>
                </div>
              </div>

              {/* Task & Path Waypoints */}
              <div className="flex items-center justify-between text-[11px] text-slate-400 mb-2 font-mono">
                <div className="flex items-center gap-1">
                  <Activity className="w-3 h-3 text-slate-500" />
                  <span>Task: {robot.task_id || "None"}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Route className="w-3 h-3 text-indigo-400" />
                  <span>Path: {robot.current_path?.length || 0} steps</span>
                </div>
              </div>

              {/* Battery Bar */}
              <div>
                <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 mb-1">
                  <div className="flex items-center gap-1">
                    {getBatteryIcon(robot.battery, robot.status)}
                    <span>Battery</span>
                  </div>
                  <span className="text-slate-300 font-bold">{Math.round(robot.battery)}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${getBatteryColor(
                      robot.battery
                    )}`}
                    style={{ width: `${Math.max(0, Math.min(100, robot.battery))}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
