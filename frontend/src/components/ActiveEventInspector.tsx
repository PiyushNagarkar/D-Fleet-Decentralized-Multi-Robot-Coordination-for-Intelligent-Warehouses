/**
 * ActiveEventInspector: Real-Time Decentralized Conflict, Negotiation, Replanning & Rescue Monitor
 */

import React from "react";
import {
  AlertTriangle,
  Scale,
  Compass,
  Wifi,
  ShieldCheck,
} from "lucide-react";
import { TelemetrySnapshot, RobotStatus } from "../types";

interface ActiveEventInspectorProps {
  telemetry: TelemetrySnapshot;
}

export const ActiveEventInspector: React.FC<ActiveEventInspectorProps> = ({
  telemetry,
}) => {
  const { robots, recent_messages, obstacles } = telemetry;

  // 1. Detect any active negotiation or yielding robots
  const negotiatingRobots = robots.filter(
    (r) => r.status === RobotStatus.BIDDING || r.status === RobotStatus.CLAIMED
  );
  const yieldingRobots = robots.filter(
    (r) => r.status === RobotStatus.WAITING || r.status === RobotStatus.YIELDING
  );
  const failedRobots = robots.filter((r) => r.status === RobotStatus.FAILED);

  // 2. Extract recent negotiation or replanning messages
  const lastNegotiationMsg = recent_messages
    .slice()
    .reverse()
    .find(
      (m) =>
        m.type.includes("YIELD") ||
        m.type.includes("RESERVATION") ||
        m.type.includes("FAILURE") ||
        m.type.includes("OBSTACLE")
    );

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col gap-3 shadow-lg">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <span className="text-xs font-mono font-bold text-slate-300 flex items-center gap-1.5 uppercase tracking-wider">
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          Active Decentralized Event
        </span>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 border border-cyan-800 text-cyan-400 font-semibold">
          LIVE PROTOCOL
        </span>
      </div>

      {/* Case A: Hardware Breakdown & Rescue Alert */}
      {failedRobots.length > 0 ? (
        <div className="bg-rose-950/40 border border-rose-600/60 rounded-lg p-2.5 flex flex-col gap-1.5 animate-pulse">
          <div className="flex items-center gap-2 text-rose-300 text-xs font-bold font-mono">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>HARDWARE FAILURE: {failedRobots.map((r) => r.id).join(", ")}</span>
          </div>
          <p className="text-[11px] text-rose-200/90 leading-tight">
            Peer heartbeat timeout detected. Reservations purged. Tasks unassigned & rescue dispatched to peer fleet.
          </p>
        </div>
      ) : negotiatingRobots.length > 0 || yieldingRobots.length > 0 ? (
        /* Case B: Multi-Robot Negotiation & Priority Aging */
        <div className="bg-purple-950/40 border border-purple-600/50 rounded-lg p-2.5 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs font-bold font-mono text-purple-300">
              <Scale className="w-4 h-4 text-purple-400" />
              SPACETIME NEGOTIATION
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-purple-900/80 text-purple-200">
              P2P ARBITRATION
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
            {negotiatingRobots.map((r) => (
              <div
                key={r.id}
                className="bg-slate-950/80 p-1.5 rounded border border-purple-800/60 flex flex-col gap-0.5"
              >
                <span className="font-bold text-cyan-300">{r.id} (Bidder)</span>
                <span className="text-slate-400 text-[10px]">Priority: {(r.priority * 10).toFixed(0)}</span>
                <span className="text-emerald-400 text-[9px]">Evaluating Bid</span>
              </div>
            ))}
            {yieldingRobots.map((r) => (
              <div
                key={r.id}
                className="bg-slate-950/80 p-1.5 rounded border border-amber-800/60 flex flex-col gap-0.5"
              >
                <span className="font-bold text-amber-300">{r.id} (Yielding)</span>
                <span className="text-slate-400 text-[10px]">Aging: +{(r.priority * 1.5).toFixed(1)}/t</span>
                <span className="text-amber-400 text-[9px]">Aisle Wait</span>
              </div>
            ))}
          </div>
        </div>
      ) : obstacles.length > 0 ? (
        /* Case C: Dynamic Obstacle & D* Lite Replanning */
        <div className="bg-amber-950/30 border border-amber-600/50 rounded-lg p-2.5 flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-amber-300 text-xs font-bold font-mono">
            <Compass className="w-4 h-4 text-amber-400" />
            <span>D* LITE DYNAMIC REPLANNING</span>
          </div>
          <p className="text-[11px] text-amber-200/90 leading-tight">
            {obstacles.length} dynamic disturbance(s) active. Robots incrementally repairing affected trajectories in $O(k)$ time.
          </p>
        </div>
      ) : (
        /* Case D: Nominal Decentralized Fleet Transit */
        <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-2.5 flex flex-col gap-1">
          <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold font-mono">
            <Wifi className="w-4 h-4 text-emerald-400" />
            <span>P2P MESH SYNCHRONIZED</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-tight">
            All robots navigating autonomous trajectories with zero centralized arbitration.
          </p>
        </div>
      )}

      {/* Latest Protocol Exchange Snippet */}
      {lastNegotiationMsg && (
        <div className="text-[10px] font-mono bg-slate-950 border border-slate-800 rounded p-2 flex items-center justify-between text-slate-400">
          <span className="text-cyan-400 font-bold">{lastNegotiationMsg.from}</span>
          <span className="text-amber-300 font-semibold">{lastNegotiationMsg.type}</span>
          <span className="text-cyan-400 font-bold">{lastNegotiationMsg.to || "BROADCAST"}</span>
          <span className="text-slate-500">T+{lastNegotiationMsg.tick}</span>
        </div>
      )}
    </div>
  );
};
