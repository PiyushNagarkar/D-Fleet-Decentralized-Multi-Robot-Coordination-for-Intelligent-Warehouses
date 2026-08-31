/**
 * RobotInspector: High-Fidelity Autonomous Fleet Overview & Robot State Inspector
 * Displays all active robots in a compact selector strip and provides deep inspection for the selected AMR.
 */

import React from "react";
import {
  Bot,
  Radio,
  Zap,
  AlertTriangle,
} from "lucide-react";
import { RobotTelemetry, RobotStatus, CommunicationEvent, TaskInfo } from "../types";

interface RobotInspectorProps {
  robot: RobotTelemetry;
  selectedRobotId?: string | null;
  onSelectRobot?: (id: string) => void;
  totalReservationsCount?: number;
  recentMessages?: CommunicationEvent[];
  allRobots?: RobotTelemetry[];
  allTasks?: TaskInfo[];
  onClose?: () => void;
}

export const RobotInspector: React.FC<RobotInspectorProps> = ({
  robot,
  selectedRobotId,
  onSelectRobot,
  recentMessages = [],
  allRobots = [],
  allTasks = [],
}) => {
  const currentPath = robot.current_path || [];
  const targetWaypoint = currentPath.length > 0 ? currentPath[currentPath.length - 1] : null;
  const nextWaypoint = currentPath.length > 0 ? currentPath[0] : null;

  // Active Task details
  const activeTask = allTasks.find((t) => t.id === robot.task_id);

  // Peer communications involving this robot
  const peerMessages = recentMessages.filter(
    (m) => m.from === robot.id || m.to === robot.id || m.to === "ALL" || m.to === "BROADCAST"
  );

  const getStatusBadgeClass = (status: RobotStatus) => {
    switch (status) {
      case RobotStatus.MOVING_TO_PICKUP:
      case RobotStatus.MOVING_TO_DELIVERY:
        return "bg-emerald-950/80 border-emerald-600 text-emerald-400";
      case RobotStatus.BIDDING:
      case RobotStatus.CLAIMED:
      case RobotStatus.WAITING:
      case RobotStatus.YIELDING:
        return "bg-amber-950/80 border-amber-600 text-amber-400";
      case RobotStatus.CHARGING:
        return "bg-purple-950/80 border-purple-600 text-purple-400";
      case RobotStatus.FAILED:
        return "bg-rose-950/80 border-rose-600 text-rose-400";
      case RobotStatus.IDLE:
      default:
        return "bg-slate-950 border-slate-700 text-slate-300";
    }
  };

  const getStatusDotColor = (status: RobotStatus) => {
    switch (status) {
      case RobotStatus.MOVING_TO_PICKUP:
      case RobotStatus.MOVING_TO_DELIVERY:
        return "bg-emerald-400 shadow-emerald-500/50";
      case RobotStatus.BIDDING:
      case RobotStatus.CLAIMED:
      case RobotStatus.WAITING:
      case RobotStatus.YIELDING:
        return "bg-amber-400 shadow-amber-500/50";
      case RobotStatus.CHARGING:
        return "bg-purple-400 shadow-purple-500/50";
      case RobotStatus.FAILED:
        return "bg-rose-500 shadow-rose-500/50 animate-pulse";
      case RobotStatus.IDLE:
      default:
        return "bg-slate-400";
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0 bg-slate-900/90 border border-slate-800 rounded-xl overflow-y-auto overflow-x-hidden shadow-2xl p-2.5 font-mono text-xs space-y-2.5 select-text overscroll-contain">
      {/* 1. TOP SECTION: COMPACT FLEET SELECTOR & OVERVIEW */}
      <div className="p-2 bg-slate-950/80 border border-slate-800 rounded-lg space-y-1.5 shrink-0">
        <div className="flex items-center justify-between pb-1 border-b border-slate-800/80">
          <div className="flex items-center gap-1.5">
            <Bot className="w-3.5 h-3.5 text-sky-400" />
            <span className="text-[10px] font-extrabold text-white tracking-wider">
              FLEET OVERVIEW ({allRobots.length} ROBOTS)
            </span>
          </div>
          <span className="text-[9px] text-slate-400">Click robot to inspect</span>
        </div>

        {/* Dynamic Grid of All Active Robots */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
          {allRobots.map((bot) => {
            const isSelected = (selectedRobotId || robot.id) === bot.id;
            return (
              <button
                key={bot.id}
                onClick={() => onSelectRobot?.(bot.id)}
                className={`p-1.5 rounded-lg border text-left transition-all cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? "bg-sky-950/80 border-sky-400 shadow-md shadow-sky-950/60 ring-1 ring-sky-400"
                    : "bg-slate-900 hover:bg-slate-850 border-slate-800 text-slate-300"
                }`}
              >
                {/* Top: ID + Status Dot */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <span className={`w-2 h-2 rounded-full shadow-sm ${getStatusDotColor(bot.status)}`} />
                    <span className="font-black text-[11px] text-white">{bot.id}</span>
                  </div>
                  <span className="text-[9px] text-slate-300 font-bold">
                    {Math.round(bot.battery)}%
                  </span>
                </div>

                {/* Battery bar */}
                <div className="w-full h-1 bg-slate-950 rounded-full overflow-hidden my-1">
                  <div
                    className={`h-full transition-all duration-300 ${
                      bot.battery > 50
                        ? "bg-emerald-500"
                        : bot.battery > 20
                        ? "bg-amber-500"
                        : "bg-rose-500"
                    }`}
                    style={{ width: `${Math.max(5, Math.min(100, bot.battery))}%` }}
                  />
                </div>

                {/* Bottom: Status Pill */}
                <div className="flex items-center justify-between text-[8px] uppercase tracking-tight font-semibold">
                  <span className="truncate max-w-[65px] text-slate-300">
                    {bot.status.replace(/_/g, " ")}
                  </span>
                  {bot.carrying_item && (
                    <span className="text-emerald-400 font-bold ml-0.5">📦</span>
                  )}
                  {bot.status === RobotStatus.FAILED && (
                    <AlertTriangle className="w-2.5 h-2.5 text-rose-400 shrink-0" />
                  )}
                  {bot.status === RobotStatus.CHARGING && (
                    <Zap className="w-2.5 h-2.5 text-purple-400 shrink-0" />
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. DETAILED SELECTED ROBOT CARDS */}
      <div className="grid grid-cols-2 gap-2 shrink-0">
        {/* Left: Selected Robot Card */}
        <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded-lg space-y-1.5">
          <div className="flex items-center justify-between pb-1 border-b border-slate-800/80">
            <div className="flex items-center gap-1.5">
              <div className="w-4 h-4 rounded bg-sky-950 border border-sky-600 flex items-center justify-center text-sky-400">
                <Bot className="w-3 h-3" />
              </div>
              <span className="text-xs font-black text-white">{robot.id}</span>
            </div>
            <span
              className={`text-[8px] px-1.5 py-0.5 rounded-full border font-bold uppercase ${getStatusBadgeClass(
                robot.status
              )}`}
            >
              {robot.status.replace(/_/g, " ")}
            </span>
          </div>

          <div className="space-y-0.5 text-[10px]">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Position</span>
              <span className="text-slate-200 font-bold">({robot.position[0]}, {robot.position[1]})</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Status</span>
              <span className="text-emerald-400 font-bold truncate max-w-[90px]">{robot.status}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Battery</span>
              <span className="text-emerald-400 font-bold">{Math.round(robot.battery)}%</span>
            </div>

            <div className="flex items-center justify-between pt-0.5 border-t border-slate-900">
              <span className="text-slate-400">Task</span>
              <span className="text-emerald-300 font-bold truncate max-w-[100px]">
                {activeTask ? `${activeTask.id} (${activeTask.item_type})` : "None (IDLE)"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">From</span>
              <span className="text-slate-300">
                {activeTask
                  ? `(${activeTask.pickup_location[0]}, ${activeTask.pickup_location[1]})`
                  : `(${robot.position[0]}, ${robot.position[1]})`}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">To</span>
              <span className="text-slate-300">
                {activeTask
                  ? `(${activeTask.delivery_location[0]}, ${activeTask.delivery_location[1]})`
                  : targetWaypoint
                  ? `(${targetWaypoint[0]}, ${targetWaypoint[1]})`
                  : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Priority</span>
              <span className="text-slate-200">{robot.priority.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Right: D* Lite Planner Card */}
        <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded-lg space-y-1.5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-1 border-b border-slate-800/80">
              <span className="text-[9px] font-extrabold text-slate-300 tracking-wider">
                D* LITE PLANNER
              </span>
              <span className="text-[8px] text-emerald-400 font-bold">
                {currentPath.length > 0 ? "Routing" : "Idle"}
              </span>
            </div>

            <div className="space-y-0.5 text-[10px] pt-1">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Path Length</span>
                <span className="text-slate-200 font-bold">{currentPath.length} cells</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Next Waypoint</span>
                <span className="text-sky-300 font-bold">
                  {nextWaypoint ? `(${nextWaypoint[0]}, ${nextWaypoint[1]})` : "—"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Payload</span>
                <span className="text-slate-200">{robot.carrying_item || "None"}</span>
              </div>
            </div>
          </div>

          {/* Mini Grid Path Visualizer */}
          <div className="w-full h-10 bg-slate-900 border border-slate-800 rounded p-1 flex items-center justify-center">
            <div className="grid grid-cols-7 gap-1">
              {Array.from({ length: 7 }).map((_, idx) => (
                <div
                  key={idx}
                  className={`w-2 h-2 rounded-sm ${
                    idx < currentPath.length
                      ? idx === 0
                        ? "bg-emerald-500 shadow-sm"
                        : idx === currentPath.length - 1
                        ? "bg-sky-500"
                        : "bg-emerald-500/70"
                      : "bg-slate-800/50"
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 3. CURRENT PATH SEGMENTED STRIP */}
      <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded-lg space-y-1.5 shrink-0">
        <div className="flex items-center justify-between">
          <span className="text-[9px] font-extrabold text-slate-300 tracking-wider">
            CURRENT PATH FOR {robot.id} ({currentPath.length} CELLS)
          </span>
        </div>

        {/* Dynamic Segmented Chain */}
        <div className="flex items-center gap-1 w-full overflow-x-auto pb-0.5 min-h-[14px]">
          {currentPath.length > 0 ? (
            currentPath.map((wp, idx) => (
              <div
                key={idx}
                title={`(${wp[0]}, ${wp[1]})`}
                className={`w-3 h-2.5 rounded-xs shrink-0 ${
                  idx === 0
                    ? "bg-emerald-500"
                    : idx < 3
                    ? "bg-amber-500"
                    : "bg-sky-500"
                }`}
              />
            ))
          ) : (
            <span className="text-[9px] text-slate-500 italic">No active path planned for {robot.id}</span>
          )}
        </div>

        {/* Legend */}
        <div className="flex items-center justify-between text-[8px] text-slate-400 pt-0.5">
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
            <span>Current</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 inline-block" />
            <span>Reserved</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 inline-block" />
            <span>Conflict</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-500 inline-block" />
            <span>Planned</span>
          </div>
        </div>
      </div>

      {/* 4. RECENT COMMUNICATIONS FEED */}
      <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded-lg space-y-1.5 shrink-0 flex flex-col">
        <div className="flex items-center justify-between pb-1 border-b border-slate-800/80">
          <span className="text-[9px] font-extrabold text-slate-300 tracking-wider flex items-center gap-1">
            <Radio className="w-3 h-3 text-purple-400" />
            COMMUNICATIONS ({robot.id})
          </span>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1 text-[9px]">
          {peerMessages.length > 0 ? (
            peerMessages.slice(0, 5).map((msg, idx) => (
              <div key={idx} className="flex items-center justify-between text-slate-300 py-0.5 border-b border-slate-900">
                <span className="text-slate-500">T+{msg.tick}</span>
                <span className="font-bold text-sky-300">{msg.from} → {msg.to}</span>
                <span className="text-purple-300 font-bold truncate max-w-[110px]">{msg.type}</span>
                <span className="text-emerald-400 font-bold">{msg.status}</span>
              </div>
            ))
          ) : (
            <div className="text-slate-600 text-center py-3 text-[10px] italic">
              No recent P2P messages for {robot.id}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
