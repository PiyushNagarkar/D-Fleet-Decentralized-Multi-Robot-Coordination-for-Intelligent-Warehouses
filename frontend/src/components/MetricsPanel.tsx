/**
 * MetricsPanel: Primary KPI Metric Cards computed from live simulation state
 * Formatted with prominent typography, clean visual hierarchy, and responsive grid layout.
 */

import React from "react";
import {
  PackageCheck,
  Zap,
  ShieldAlert,
  Radio,
  Clock,
  ShieldCheck,
} from "lucide-react";
import { SimulationMetrics } from "../types";

interface MetricsPanelProps {
  metrics: SimulationMetrics;
}

export const MetricsPanel: React.FC<MetricsPanelProps> = ({ metrics }) => {
  const completed = metrics.total_tasks_completed;
  const spawned = metrics.total_tasks_spawned;
  const throughput = metrics.throughput_tasks_per_hour;
  const avgDelivery = metrics.average_completion_time_ticks;
  const conflicts = metrics.conflicts_resolved;
  const deadlocks = metrics.deadlocks_resolved;
  const messages = metrics.messages_sent;
  const dropped = metrics.messages_dropped;
  const collisions = metrics.collisions_detected;

  const dropRate = messages > 0 ? ((dropped / messages) * 100).toFixed(1) : "0.0";

  const cards = [
    {
      label: "TASKS COMPLETED",
      value: `${completed} / ${spawned}`,
      icon: <PackageCheck className="w-4 h-4 text-sky-400" />,
      subtext: throughput > 0 ? `${(throughput / 3600).toFixed(2)} / hr rate` : "0.00 / hr",
      subtextColor: completed > 0 ? "text-cyan-400" : "text-slate-500",
    },
    {
      label: "CONFLICTS RESOLVED",
      value: `${conflicts}`,
      icon: <ShieldCheck className="w-4 h-4 text-emerald-400" />,
      subtext: conflicts > 0 ? "100% P2P negotiated" : "No active conflicts",
      subtextColor: conflicts > 0 ? "text-emerald-400" : "text-slate-500",
    },
    {
      label: "DEADLOCKS CLEARED",
      value: `${deadlocks}`,
      icon: <Zap className="w-4 h-4 text-amber-400" />,
      subtext: deadlocks > 0 ? `${deadlocks} cycles broken` : "Zero deadlocks",
      subtextColor: deadlocks > 0 ? "text-amber-400" : "text-slate-500",
    },
    {
      label: "P2P MESSAGES",
      value: `${messages}`,
      icon: <Radio className="w-4 h-4 text-purple-400" />,
      subtext: messages > 0 ? `${dropped} dropped (${dropRate}%)` : "Mesh idle",
      subtextColor: messages > 0 ? "text-purple-300" : "text-slate-500",
    },
    {
      label: "COLLISION VIOLATIONS",
      value: `${collisions}`,
      icon: <ShieldAlert className={`w-4 h-4 ${collisions === 0 ? "text-emerald-400" : "text-rose-400"}`} />,
      subtext: collisions === 0 ? "Zero violations" : `${collisions} violations`,
      subtextColor: collisions === 0 ? "text-emerald-400" : "text-rose-400 font-bold",
    },
    {
      label: "AVG DELIVERY TIME",
      value: completed > 0 ? `${avgDelivery.toFixed(1)} ticks` : "—",
      icon: <Clock className="w-4 h-4 text-indigo-400" />,
      subtext: completed > 0 ? `${(avgDelivery * 0.5).toFixed(1)}s sim-time` : "Awaiting deliveries",
      subtextColor: completed > 0 ? "text-indigo-300" : "text-slate-500",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
      {cards.map((card, idx) => (
        <div
          key={idx}
          className="bg-slate-900/90 border border-slate-800 hover:border-slate-700 transition-all rounded-xl p-3 flex flex-col justify-between shadow-lg font-mono"
        >
          <div className="flex items-center justify-between pb-1">
            <span className="text-[10px] font-extrabold text-slate-400 tracking-wider">
              {card.label}
            </span>
            {card.icon}
          </div>
          <div className="my-1 flex items-baseline">
            <span className="text-xl lg:text-2xl font-black text-white tracking-tight">
              {card.value}
            </span>
          </div>
          <div className={`text-[10px] ${card.subtextColor} truncate font-semibold pt-0.5 border-t border-slate-800/60`}>
            {card.subtext}
          </div>
        </div>
      ))}
    </div>
  );
};
